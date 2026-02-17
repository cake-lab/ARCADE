import os
from typing import Tuple, Dict, Any

import cv2
import numpy as np
import open3d as o3d


def _ensure_uint8_rgb(rgb_image: np.ndarray) -> np.ndarray:
    if rgb_image.dtype != np.uint8:
        if rgb_image.max() <= 1.0:
            rgb_image = (rgb_image * 255).astype(np.uint8)
        else:
            rgb_image = rgb_image.astype(np.uint8)
    return rgb_image


def _ensure_float32_depth(depth_image: np.ndarray) -> np.ndarray:
    if depth_image.dtype != np.float32:
        depth_image = depth_image.astype(np.float32)
    return depth_image


def resize_depth_to_rgb(depth: np.ndarray, rgb_resolution: Tuple[int, int]) -> np.ndarray:
    """Resize depth to match provided (width, height)."""
    width, height = rgb_resolution
    if depth.shape[1] == width and depth.shape[0] == height:
        return depth
    return cv2.resize(depth, (width, height), interpolation=cv2.INTER_NEAREST)




def load_session_data(session_path: str) -> Tuple[np.ndarray, np.ndarray, dict, dict, str]:
    """
    Load session data (RGB, depth, intrinsics, metadata).
    Returns (rgb_image, depth_data, intrinsics_dict, metadata, metadata_path)
    """
    rgb_path = os.path.join(session_path, "frame_00000_rgb.png")
    depth_path = os.path.join(session_path, "frame_00000_depth.npy")
    metadata_path = os.path.join(session_path, "frame_00000_metadata.json")
    config_path = os.path.join(session_path, "session_config.json")

    rgb_image = cv2.imread(rgb_path)
    if rgb_image is None:
        raise FileNotFoundError(f"Could not load RGB image from {rgb_path}")
    rgb_image = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2RGB)
    depth_data = np.load(depth_path)

    import json
    with open(config_path, "r") as f:
        config = json.load(f)
    intrinsics = {
        "rgb_resolution": tuple(config.get("rgb_resolution", (rgb_image.shape[1], rgb_image.shape[0]))),
        "intrinsics": config.get("intrinsics", [447.39, 447.39, rgb_image.shape[1] / 2, rgb_image.shape[0] / 2]),
    }

    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    return rgb_image, depth_data, intrinsics, metadata, metadata_path


def create_pointcloud(
    rgb_image: np.ndarray,
    depth_data: np.ndarray,
    intrinsics_list: list,
    resolution: Tuple[int, int],
    depth_trunc: float = 3.0,
) -> o3d.geometry.PointCloud:
    """
    Mirror server.py point cloud creation exactly:
      - resize depth to (width, height)
      - ensure rgb uint8, depth float32
      - create Open3D RGBDImage
      - create PinholeCameraIntrinsic from (fx, fy, cx, cy) and (width, height)
      - create point cloud without extrinsic or coordinate flips
    """
    width, height = resolution
    depth_resized = cv2.resize(depth_data, resolution, interpolation=cv2.INTER_NEAREST)

    rgb_u8 = _ensure_uint8_rgb(rgb_image)
    depth_f32 = _ensure_float32_depth(depth_resized)

    rgbd_image = o3d.geometry.RGBDImage.create_from_color_and_depth(
        o3d.geometry.Image(rgb_u8),
        o3d.geometry.Image(depth_f32),
        depth_trunc=depth_trunc,
        convert_rgb_to_intensity=False,
    )

    fx, fy, cx, cy = intrinsics_list
    intrinsic_o3d = o3d.camera.PinholeCameraIntrinsic(
        width, height, fx, fy, cx, cy
    )
    
    scene_pcd = o3d.geometry.PointCloud.create_from_rgbd_image(rgbd_image, intrinsic_o3d)
    
    # Transform coordinate system.
    scene_pcd.transform([[1, 0, 0, 0],
                        [0, -1, 0, 0],
                        [0, 0, -1, 0],
                        [0, 0, 0, 1]])
    
    return scene_pcd


