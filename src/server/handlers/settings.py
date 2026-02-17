"""Virtual settings and render-positions handlers."""

import base64
import json
import os

import cv2
import numpy as np

from server import state
from server.handlers.base import BaseHandler
from server.session_mgr import SessionManager
from server.utils import read_json_file, _encode_image_bytes_rgb
from server.modules.composite.render import Renderer
from server.modules.composite.composite import composite


class UpdateVirtualSettingsHandler(BaseHandler):
    def post(self):
        try:
            data = json.loads(self.request.body)
            new_depth = data.get("virtual_depth", None)
            state.VIRTUAL_DEPTH = None if new_depth in (None, "") else float(new_depth)
            new_obj = data.get("virtual_object", None)
            if new_obj is not None:
                if new_obj == "virtual_plane":
                    state.VIRTUAL_OBJECT = new_obj
                else:
                    if os.path.isfile(new_obj):
                        state.current_model_path = new_obj
                    else:
                        self.error_response(f"Provided virtual object path is not a valid file: {new_obj}")
                        return
                    state.VIRTUAL_OBJECT = new_obj
            virtual_position = data.get("virtual_position", None)

            if virtual_position is not None and state.VIRTUAL_OBJECT == "virtual_plane":
                state.VIRTUAL_OBJECT = state.current_model_path
            if virtual_position is not None:
                try:
                    x = float(virtual_position.get("x", 0.0))
                    y = float(virtual_position.get("y", 0.0))
                    z = float(virtual_position.get("z", 0.0))
                    state.VIRTUAL_OBJECT_POSITION = [x, y, z]
                    state.VIRTUAL_OBJECT_POSITION_MANUAL_SET = True
                except Exception as e:
                    self.error_response("Invalid virtual position values: " + str(e))
                    return
            self.write_json({
                "message": "Virtual settings updated",
                "virtual_depth": state.VIRTUAL_DEPTH,
                "virtual_object": state.VIRTUAL_OBJECT if state.VIRTUAL_OBJECT is not None else state.current_model_path,
                "virtual_position": state.VIRTUAL_OBJECT_POSITION
            })
        except Exception as e:
            self.error_response(str(e))


class RenderPositionsHandler(BaseHandler):
    def post(self):
        try:
            try:
                data = json.loads(self.request.body)
            except Exception:
                data = {}

            session = data.get("session") or self.get_argument("session", None)
            frame = data.get("frame") or self.get_argument("frame", None)
            if session is None or frame is None:
                self.error_response("Missing required parameters: session, frame")
                return
            try:
                frame = int(frame)
            except Exception as e:
                self.error_response("Invalid frame: " + str(e))
                return

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

            raw_rgb = cv2.cvtColor(cv2.imread(rgb_file), cv2.COLOR_BGR2RGB)
            raw_depth = np.load(depth_file)
            metadata = read_json_file(metadata_file)

            try:
                session_config = read_json_file(os.path.join(manager.session_folder, "session_config.json"))
            except Exception:
                session_config = {}
            resolution = state.global_rgb_resolution if state.global_rgb_resolution is not None else session_config.get("rgb_resolution")
            intrinsics = state.global_intrinsics if state.global_intrinsics is not None else session_config.get("intrinsics")
            if resolution is None or intrinsics is None:
                self.error_response("Missing camera resolution or intrinsics for rendering")
                return

            raw_depth = cv2.resize(raw_depth, resolution, interpolation=cv2.INTER_NEAREST)

            positions = metadata.get("candidatePositions", [])
            if not isinstance(positions, list) or len(positions) == 0:
                self.error_response("No candidatePositions found in frame metadata")
                return

            renderer = Renderer(
                model_path=state.current_model_path,
                scale=0.006,
                resolution=resolution,
                intrinsics=intrinsics
            )

            images = []
            for idx, pos in enumerate(positions):
                try:
                    position = np.array(pos, dtype=float).tolist()
                except Exception:
                    continue
                rendered_color, rendered_depth = renderer.update_and_render(metadata, position)
                comp = composite(raw_rgb, raw_depth, rendered_color, rendered_depth, resolution, virtual_depth=state.VIRTUAL_DEPTH)
                enc = _encode_image_bytes_rgb(comp)
                if enc is None:
                    continue
                images.append({
                    "index": idx,
                    "position": position,
                    "image_base64": base64.b64encode(enc).decode("utf-8")
                })

            self.write_json({
                "count": len(images),
                "images": images
            })
        except Exception as e:
            self.error_response(f"Error rendering positions: {str(e)}", status=500)
