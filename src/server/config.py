"""Server constants, paths, and env-based settings."""

import os

BASE_SAVE_DIR = "../data/sessions"
MESH_DIR = "../data/3D_models"
INFERENCE_MODEL_DIR = os.path.join("modules", "inference")
DEFAULT_CONFIG_FILE = "default_config.json"

# Virtual object settings (immutable defaults)
VIRTUAL_DEPTH = 0.5
VIRTUAL_OBJECT = "virtual_plane"

# Live/replay image encoding 
LIVE_ENCODING = os.getenv("LIVE_ENCODING", "webp").lower()
LIVE_QUALITY = int(os.getenv("LIVE_QUALITY", "80"))  # 1..100
PNG_LEVEL = int(os.getenv("PNG_LEVEL", "1"))  # 0..9

os.makedirs(BASE_SAVE_DIR, exist_ok=True)
os.makedirs(MESH_DIR, exist_ok=True)
