"""Session list, frame list, frame details handlers."""

import base64
import glob
import io
import os

import cv2
import numpy as np
from PIL import Image

from server import state
from server.config import BASE_SAVE_DIR
from server.handlers.base import BaseHandler
from server.session_mgr import SessionManager
from server.utils import read_json_file, update_virtual_position_from_metadata, generate_depth_colormap, _encode_image_bytes_rgb
from server.modules.composite.render import Renderer
from server.modules.composite.composite import composite


class SessionListHandler(BaseHandler):
    def get(self):
        sessions = [d for d in os.listdir(BASE_SAVE_DIR) if os.path.isdir(os.path.join(BASE_SAVE_DIR, d))]
        self.write_json({"sessions": sessions})


class ListFramesHandler(BaseHandler):
    def get(self):
        session = self.get_argument("session", None)
        if not session:
            self.error_response("Missing session parameter")
            return
        manager = SessionManager(session)
        if not manager.exists():
            self.error_response("Session folder not found")
            return
        files = glob.glob(os.path.join(manager.session_folder, "frame_*_metadata.json"))
        frames = sorted([int(os.path.basename(f).split('_')[1]) for f in files])
        self.write_json({"frames": frames})


class FrameDetailsHandler(BaseHandler):
    def get(self):
        args = self.require_args("session", "frame")
        if args is None:
            return
        session, frame = args["session"], args["frame"]

        manager = SessionManager(session)
        if not manager.exists():
            self.error_response("Session folder not found")
            return

        rgb_file = manager.get_frame_path(frame, "rgb")
        depth_file = manager.get_frame_path(frame, "depth")
        metadata_file = manager.get_frame_path(frame, "metadata")
        if not (os.path.isfile(rgb_file) and os.path.isfile(depth_file) and os.path.isfile(metadata_file)):
            self.error_response("Frame files not found")
            return

        with open(rgb_file, "rb") as f:
            rgb_data = f.read()
        depth = np.load(depth_file)
        metadata = read_json_file(metadata_file)
        update_virtual_position_from_metadata(metadata)

        try:
            session_config = read_json_file(os.path.join(manager.session_folder, "session_config.json"))
        except Exception:
            session_config = {}
        resolution = state.global_rgb_resolution if state.global_rgb_resolution is not None else session_config.get("rgb_resolution")
        intrinsics = state.global_intrinsics if state.global_intrinsics is not None else session_config.get("intrinsics")
        if resolution is None:
            self.error_response("RGB resolution is not available")
            return

        original_depth_colormap = generate_depth_colormap(depth, cmap_name='jet')
        rgb_array = np.array(Image.open(io.BytesIO(rgb_data)))
        if state.VIRTUAL_OBJECT == "virtual_plane":
            comp = composite(rgb_array, depth, None, None, resolution, virtual_depth=state.VIRTUAL_DEPTH)
        else:
            renderer = Renderer(model_path=state.current_model_path, scale=0.006, resolution=resolution, intrinsics=intrinsics)
            rendered_color, rendered_depth = renderer.update_and_render(metadata, state.VIRTUAL_OBJECT_POSITION)
            comp = composite(rgb_array, depth, rendered_color, rendered_depth, resolution, virtual_depth=state.VIRTUAL_DEPTH)

        comp_enc = _encode_image_bytes_rgb(comp)
        composite_data = comp_enc if comp_enc is not None else b""

        inferred_depth_colormaps = {}
        inferred_composites = {}
        if state.current_inference_models:
            for model_name, instance in state.current_inference_models:
                inferred_depth = instance.infer(rgb_array)
                if hasattr(inferred_depth, "convert"):
                    inferred_depth = np.array(inferred_depth)
                inferred_depth_colormap = generate_depth_colormap(inferred_depth, cmap_name='jet')
                inferred_depth_colormaps[model_name] = base64.b64encode(inferred_depth_colormap).decode("utf-8")
                comp_inferred = composite(rgb_array, inferred_depth, None, None, resolution, virtual_depth=state.VIRTUAL_DEPTH)
                comp_inf_enc = _encode_image_bytes_rgb(comp_inferred)
                inferred_composites[model_name] = base64.b64encode(comp_inf_enc).decode("utf-8") if comp_inf_enc is not None else ""

        mask_path = os.path.join(manager.session_folder, f"frame_{int(frame):05d}_mask.png")
        object_mask_b64 = ""
        if os.path.isfile(mask_path):
            with open(mask_path, "rb") as mf:
                object_mask_b64 = base64.b64encode(mf.read()).decode("utf-8")

        self.write_json({
            "rgb": base64.b64encode(rgb_data).decode("utf-8"),
            "composite": base64.b64encode(composite_data).decode("utf-8"),
            "original_depth_colormap": base64.b64encode(original_depth_colormap).decode("utf-8"),
            "inferred_depth_colormaps": inferred_depth_colormaps,
            "inferred_composites": inferred_composites,
            "object_mask": object_mask_b64
        })
