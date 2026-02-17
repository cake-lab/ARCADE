"""Shared utilities: image encoding, masks, JSON, depth colormap, virtual position."""

import json
import queue
import cv2
import numpy as np
import matplotlib.pyplot as plt

from server import config


def _encode_image_bytes_rgb(img_rgb, fmt=None, quality=None):
    """Encode HxWx3 uint8 RGB -> bytes using fast codec for live/replay."""
    fmt = fmt or config.LIVE_ENCODING
    quality = quality if quality is not None else config.LIVE_QUALITY
    bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    if fmt in ("jpg", "jpeg"):
        params = [int(cv2.IMWRITE_JPEG_QUALITY), quality,
                  int(cv2.IMWRITE_JPEG_OPTIMIZE), 1]
        ok, buf = cv2.imencode(".jpg", bgr, params)
    elif fmt == "webp":
        params = [int(cv2.IMWRITE_WEBP_QUALITY), quality]
        ok, buf = cv2.imencode(".webp", bgr, params)
    elif fmt == "webp_lossless":
        ok, buf = cv2.imencode(".webp", bgr, [int(cv2.IMWRITE_WEBP_LOSSLESS), 1])
    elif fmt == "png":
        params = [int(cv2.IMWRITE_PNG_COMPRESSION), config.PNG_LEVEL]
        ok, buf = cv2.imencode(".png", bgr, params)
    else:
        params = [int(cv2.IMWRITE_WEBP_QUALITY), quality]
        ok, buf = cv2.imencode(".webp", bgr, params)
    return buf.tobytes() if ok else None


class LatestQueue(queue.Queue):
    """A queue that keeps only the most recent items (drops oldest when full)."""

    def __init__(self, maxsize=2):
        super().__init__(maxsize=maxsize)

    def put_latest(self, item):
        try:
            if self.full():
                self.get_nowait()
                self.task_done()
        except queue.Empty:
            pass
        super().put(item)


def build_mask(color):
    alpha = color[:, :, 3]
    mask_bin = (alpha > 0).astype(np.uint8) * 255
    return mask_bin


def read_json_file(file_path):
    with open(file_path, "r") as f:
        return json.load(f)


def load_camera_intrinsics_from_session(session_folder, width, height):
    import os
    session_config_path = os.path.join(session_folder, 'session_config.json')
    fx = fy = 447.390625
    cx = width / 2
    cy = height / 2
    if os.path.exists(session_config_path):
        try:
            session_config = read_json_file(session_config_path)
            if 'intrinsics' in session_config and len(session_config['intrinsics']) >= 4:
                fx, fy, cx, cy = session_config['intrinsics']
                print(f"Loaded camera intrinsics from session config: fx={fx}, fy={fy}, cx={cx}, cy={cy}")
            else:
                print(f"Session config found but no valid intrinsics, using defaults")
        except Exception as e:
            print(f"Error loading session config: {e}, using defaults")
    else:
        print(f"Session config not found at {session_config_path}, using defaults")
    return fx, fy, cx, cy


def generate_depth_colormap(depth, cmap_name='jet'):
    vmin, vmax = float(np.min(depth)), float(np.max(depth))
    norm = plt.Normalize(vmin=vmin, vmax=vmax)
    cmap = plt.get_cmap(cmap_name)
    colored = (cmap(norm(depth))[:, :, :3] * 255).astype(np.uint8)
    ret, encoded = cv2.imencode('.png', colored)
    return encoded.tobytes() if ret else None


def annotate_segment(segment, label):
    annotated = segment.copy()
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    thickness = 2
    text_size, _ = cv2.getTextSize(label, font, font_scale, thickness)
    cv2.putText(annotated, label, (10, text_size[1] + 10), font, font_scale, (0, 255, 0), thickness)
    return annotated


def update_virtual_position_from_metadata(metadata):
    from server import state
    if not state.VIRTUAL_OBJECT_POSITION_MANUAL_SET and "objPosition" in metadata:
        state.VIRTUAL_OBJECT_POSITION = metadata["objPosition"]
