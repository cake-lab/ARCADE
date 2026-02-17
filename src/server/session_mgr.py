"""Session folder and frame path helpers."""

import os

from server.config import BASE_SAVE_DIR
from server.utils import read_json_file


class SessionManager:
    def __init__(self, session):
        self.session = session
        self.session_folder = os.path.join(BASE_SAVE_DIR, session)

    def exists(self):
        return os.path.isdir(self.session_folder)

    def get_config(self):
        config_file = os.path.join(self.session_folder, "session_config.json")
        return read_json_file(config_file) if os.path.isfile(config_file) else {}

    def get_frame_path(self, frame_idx, file_type):
        frame_str = f"{int(frame_idx):05d}"
        if file_type == "rgb":
            return os.path.join(self.session_folder, f"frame_{frame_str}_rgb.png")
        elif file_type == "depth":
            return os.path.join(self.session_folder, f"frame_{frame_str}_depth.npy")
        elif file_type == "metadata":
            return os.path.join(self.session_folder, f"frame_{frame_str}_metadata.json")
        return None
