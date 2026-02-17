"""Mutable global state used by handlers and workers."""

import os
import queue
import threading

from server.config import MESH_DIR, VIRTUAL_OBJECT as _DEFAULT_VIRTUAL_OBJECT, VIRTUAL_DEPTH as _DEFAULT_VIRTUAL_DEPTH

# Queues and thread pool
render_queue = None  
save_queue = None   
fileio_pool = None 

frame_counter = 0
global_rgb_resolution = None
global_depth_resolution = None
global_intrinsics = None

current_model_path = os.path.join(MESH_DIR, "teapot.obj")
current_model_paths = [current_model_path]
current_inference_models = []
live_clients = set()
init_event = threading.Event()
main_ioloop = None
multi_object_mode = False

# Virtual depth (mutated by settings handler)
VIRTUAL_DEPTH = _DEFAULT_VIRTUAL_DEPTH
# Virtual object (mutated by settings handler)
VIRTUAL_OBJECT = _DEFAULT_VIRTUAL_OBJECT
# Virtual position (mutated by handlers and replay)
VIRTUAL_OBJECT_POSITION = None
VIRTUAL_OBJECT_POSITION_MANUAL_SET = False

# Dataset (set in main when using ScanNet dataset)
global_dataset = None
global_dataloader = None
global_data_iter = None


def init_queues_and_pool():
    """Initialize queues and thread pool. Call once from main."""
    from server.utils import LatestQueue
    from concurrent.futures import ThreadPoolExecutor

    global render_queue, save_queue, fileio_pool
    render_queue = LatestQueue(maxsize=2)
    save_queue = queue.Queue(maxsize=64)
    fileio_pool = ThreadPoolExecutor(max_workers=2)
