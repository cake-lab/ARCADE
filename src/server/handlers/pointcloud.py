"""Point cloud export handlers."""

import io
import os
import tempfile
import zipfile

import cv2
import numpy as np
import trimesh
from PIL import Image

from server import state
from server.handlers.base import BaseHandler
from server.session_mgr import SessionManager
from server.utils import read_json_file, update_virtual_position_from_metadata
from server.modules.composite.render import Renderer
from server.modules.pointcloud import create_pointcloud


class PointCloudPlyHandler(BaseHandler):
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
        color = np.array(Image.open(io.BytesIO(rgb_data)))
        depth = np.load(depth_file)
        metadata = read_json_file(metadata_file)
        update_virtual_position_from_metadata(metadata)

        try:
            session_config = read_json_file(os.path.join(manager.session_folder, "session_config.json"))
        except Exception:
            session_config = {}
        resolution = state.global_rgb_resolution if state.global_rgb_resolution is not None else session_config.get("rgb_resolution")
        intrinsics = state.global_intrinsics if state.global_intrinsics is not None else session_config.get("intrinsics")

        depth = cv2.resize(depth, resolution, interpolation=cv2.INTER_NEAREST)

        virtual_obj_path = state.current_model_path
        if not os.path.isfile(virtual_obj_path):
            self.error_response(f"Virtual object mesh not found: {virtual_obj_path}. Add teapot.obj to the 3D_models folder.")
            return
        virtual_obj_position = metadata.get("objPosition")
        virtual_renderer = Renderer(
            model_path=virtual_obj_path,
            scale=0.006,
            resolution=resolution,
            intrinsics=intrinsics
        )
        rendered_color, rendered_depth = virtual_renderer.update_and_render(metadata, virtual_obj_position)
        rendered_color = rendered_color[:, :, :3]

        rendered_color = cv2.resize(rendered_color, resolution, interpolation=cv2.INTER_NEAREST)
        rendered_depth = cv2.resize(rendered_depth, resolution, interpolation=cv2.INTER_NEAREST)

        virtual_pcd = create_pointcloud(
            rgb_image=rendered_color,
            depth_data=rendered_depth,
            intrinsics_list=intrinsics,
            resolution=resolution,
        )

        point_clouds = {}
        arkit_scene_pcd = create_pointcloud(
            rgb_image=color,
            depth_data=depth,
            intrinsics_list=intrinsics,
            resolution=resolution,
        )
        arkit_scene_pcd += virtual_pcd
        point_clouds["arkit"] = arkit_scene_pcd

        if state.current_inference_models:
            for model_name, instance in state.current_inference_models:
                try:
                    inferred_depth = instance.infer(color)
                    if hasattr(inferred_depth, "convert"):
                        inferred_depth = np.array(inferred_depth)
                    inferred_depth = cv2.resize(inferred_depth, resolution, interpolation=cv2.INTER_NEAREST)
                    model_scene_pcd = create_pointcloud(
                        rgb_image=color,
                        depth_data=inferred_depth,
                        intrinsics_list=intrinsics,
                        resolution=resolution,
                    )
                    model_scene_pcd += virtual_pcd
                    point_clouds[model_name] = model_scene_pcd
                except Exception as e:
                    print(f"Error creating point cloud for model {model_name}: {e}")
                    continue

        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
            with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for cloud_name, pcd in point_clouds.items():
                    points = np.asarray(pcd.points)
                    colors = np.asarray(pcd.colors)
                    if colors.max() <= 1:
                        colors = (colors * 255).astype(np.uint8)
                    point_cloud = trimesh.PointCloud(vertices=points, colors=colors)
                    ply_data = point_cloud.export(file_type='ply')
                    filename = f"point_cloud_{cloud_name}.ply"
                    zipf.writestr(filename, ply_data)
            with open(temp_zip.name, 'rb') as f:
                zip_data = f.read()
            os.unlink(temp_zip.name)

        self.set_header("Content-Type", "application/zip")
        self.set_header("Content-Disposition", f"attachment; filename=point_clouds_{session}_frame_{frame}.zip")
        self.write(zip_data)


class PointCloudInfoHandler(BaseHandler):
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

        available_clouds = ["arkit"]
        if state.current_inference_models:
            for model_name, _ in state.current_inference_models:
                available_clouds.append(model_name)

        response = {
            "session": session,
            "frame": frame,
            "available_point_clouds": available_clouds,
            "total_clouds": len(available_clouds),
            "download_url": f"/point_cloud?session={session}&frame={frame}"
        }

        self.write_json(response)
