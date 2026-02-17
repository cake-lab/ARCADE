# ARCADE Server Architecture

This document describes the server modules so you can understand and extend the framework. The server is built with **Tornado** and handles live capture, replay, inference, mesh management, and dataset evaluation.

---

## Overview

```
server.py          → Entry point
server/
├── main.py        → Init, dataset, workers, Tornado loop
├── app.py         → Route definitions
├── config.py      → Paths, constants, env settings
├── state.py       → Mutable global state
├── utils.py       → Image encoding, JSON, depth colormap
├── session_mgr.py → Session folder and frame paths
├── workers.py     → Render and save background workers
└── handlers/      → HTTP and WebSocket handlers
```

**Data flow (live capture):** Mobile client → WebSocket → `render_queue` → `render_worker` (composite + broadcast) → `save_queue` → `save_worker` (disk)

---

## Core Modules

### `config.py` — Constants and Paths

| Variable | Purpose |
|----------|---------|
| `BASE_SAVE_DIR` | Root directory for captured sessions (default: `../../data`) |
| `MESH_DIR` | Directory for uploaded 3D meshes (`.obj`) |
| `INFERENCE_MODEL_DIR` | Directory for inference model scripts (`modules/inference`) |
| `VIRTUAL_DEPTH` | Default depth for virtual plane compositing |
| `VIRTUAL_OBJECT` | Default virtual object type (`"virtual_plane"` or mesh path) |
| `LIVE_ENCODING` | Image encoding for live/replay (`webp`, `jpg`, `png`, `webp_lossless`) |
| `LIVE_QUALITY` | JPEG/WebP quality (1–100) |

**Edit for:** Changing data paths, default encoding, or quality.

---

### `state.py` — Mutable Global State

Shared state used by handlers and workers:

| Variable | Purpose |
|----------|---------|
| `render_queue` | `LatestQueue` — latest frame task for rendering (drops older frames when full) |
| `save_queue` | Queue of frames to save to disk |
| `fileio_pool` | Thread pool for file I/O |
| `frame_counter` | Incremented per captured frame |
| `global_rgb_resolution`, `global_depth_resolution`, `global_intrinsics` | Camera parameters from client init |
| `current_model_path`, `current_model_paths` | Active mesh(es) for virtual object rendering |
| `current_inference_models` | List of `(model_name, instance)` for depth inference |
| `live_clients` | Set of WebSocket clients subscribed to live stream |
| `init_event` | Set when client sends `initialize` (unblocks render worker) |
| `VIRTUAL_DEPTH`, `VIRTUAL_OBJECT`, `VIRTUAL_OBJECT_POSITION` | Virtual object settings |
| `global_dataset`, `global_dataloader`, `global_data_iter` | ScanNet dataset (optional) |

**Edit for:** Adding new global state, changing queue sizes, or thread pool workers.

---

### `session_mgr.py` — Session and Frame Paths

`SessionManager` provides:

- `exists()` — Check if session folder exists
- `get_config()` — Load `session_config.json`
- `get_frame_path(frame_idx, file_type)` — Path for `rgb`, `depth`, or `metadata`

Frame naming: `frame_00000_rgb.png`, `frame_00000_depth.npy`, `frame_00000_metadata.json`

**Edit for:** Custom session layout or naming.

---

### `utils.py` — Shared Utilities

| Function | Purpose |
|----------|---------|
| `_encode_image_bytes_rgb()` | Encode RGB numpy array → bytes (WebP/JPEG/PNG) |
| `LatestQueue` | Queue that keeps only the most recent item when full |
| `build_mask()` | Alpha channel → binary mask |
| `read_json_file()` | Load JSON file |
| `load_camera_intrinsics_from_session()` | Read intrinsics from session config |
| `generate_depth_colormap()` | Depth → jet colormap PNG bytes |
| `annotate_segment()` | Draw label on segment image |
| `update_virtual_position_from_metadata()` | Update `VIRTUAL_OBJECT_POSITION` from metadata |

**Edit for:** New image formats, colormaps, or metadata handling.

---

### `workers.py` — Background Workers

Two daemon threads:

1. **`render_worker`**
   - Waits for `init_event`
   - Consumes `render_queue`, renders virtual object with `Renderer`, composites with `composite()`
   - Broadcasts result to `live_clients` via WebSocket
   - Pushes frame data to `save_queue`

2. **`save_worker`**
   - Consumes `save_queue`, submits `save_data_blocking` to `fileio_pool`
   - Writes RGB PNG, depth NPY, metadata JSON, optional mask PNG

**Edit for:** Changing render logic, compositing, or save format.

---

## Handlers (`handlers/`)

### `base.py` — Base Handler

- CORS headers
- `write_json()`, `error_response()`, `require_args()`

All HTTP handlers inherit from `BaseHandler`.

---

### `websocket.py` — Frame Capture, Live, Replay

| Handler | Route | Purpose |
|---------|-------|---------|
| `FrameWebSocketHandler` | `/websocket` | Receives RGB + depth + metadata from mobile client; creates session folder; queues frames for render/save |
| `LiveStreamHandler` | `/live` | WebSocket clients receive live composited frames |
| `ReplayStreamHandler` | `/replay?session=...` | Streams replay of saved session with optional inference overlays |

**Message types (FrameWebSocket):**

- `initialize` — Set resolution, intrinsics; create `session_config.json`
- `frame` — RGB + depth (base64) + metadata; enqueue for render/save

**Edit for:** New message types, different session layout, or replay behavior.

---

### `mesh.py` — 3D Mesh Management

| Handler | Route | Method | Purpose |
|---------|-------|--------|---------|
| `MeshUploadHandler` | `/upload_mesh` | POST | Upload `.obj` file |
| `ListMeshesHandler` | `/list_meshes` | GET | List meshes in `MESH_DIR` |
| `SelectMeshHandler` | `/select_mesh` | POST | Set single active mesh |
| `SelectMultipleMeshesHandler` | `/select_multiple_meshes` | POST | Set multiple meshes |
| `GetCurrentMeshesHandler` | `/get_current_meshes` | GET | Return current mesh path(s) |
| `MeshSettingsHandler` | `/mesh_settings` | GET | Get virtual object position (from metadata or manual) |

**Edit for:** Supporting other mesh formats or multi-mesh rendering.

---

### `inference.py` — Depth Inference Models

| Handler | Route | Method | Purpose |
|---------|-------|--------|---------|
| `ListInferenceModelsHandler` | `/list_inference_models` | GET | List available models |
| `SelectInferenceModelsHandler` | `/select_inference_models` | POST | Load selected model(s) |
| `GetSelectedModelsHandler` | `/get_selected_models` | GET | Return currently selected models |
| `UploadInferenceModelHandler` | `/upload_inference_model` | POST | Upload `.py` model file; reload models |

Models live in `modules/inference/`. Each model is a class extending `InferenceModel` with `infer(rgb_image) -> depth`. See `modules/inference/base.py` and `zoedepth.py` / `depthanything.py` for examples.

**Edit for:** New inference endpoints or model loading logic.

---

### `session_handlers.py` — Sessions and Frames

| Handler | Route | Method | Purpose |
|---------|-------|--------|---------|
| `SessionListHandler` | `/list_sessions` | GET | List session folders |
| `ListFramesHandler` | `/list_frames?session=...` | GET | List frame indices in session |
| `FrameDetailsHandler` | `/frame_details?session=...&frame=...` | GET | RGB, composite, depth colormap, inference overlays, mask |

**Edit for:** Custom frame metadata or response format.

---

### `pointcloud.py` — Point Cloud Export

| Handler | Route | Method | Purpose |
|---------|-------|--------|---------|
| `PointCloudPlyHandler` | `/point_cloud?session=...&frame=...` | GET | ZIP of PLY files (ARKit + inference models) |
| `PointCloudInfoHandler` | `/point_cloud_info?session=...&frame=...` | GET | Metadata about available point clouds |

**Edit for:** Different export formats or point cloud generation.

---

### `dataset.py` — ScanNet Dataset

| Handler | Route | Method | Purpose |
|---------|-------|--------|---------|
| `DatasetInfoHandler` | `/dataset_info` | GET | Number of frames in dataset |
| `DatasetFrameHandler` | `/dataset_frame?frame=...` | GET | RGB, composite, GT depth colormap, inference results, depth errors |

Used for offline evaluation on ScanNet. Dataset is loaded in `main.py`.

**Edit for:** Supporting other datasets or metrics.

---

### `settings.py` — Virtual Object Settings

| Handler | Route | Method | Purpose |
|---------|-------|--------|---------|
| `UpdateVirtualSettingsHandler` | `/update_virtual_settings` | POST | Set `virtual_depth`, `virtual_object`, `virtual_position` |
| `RenderPositionsHandler` | `/render_positions` | POST | Render virtual object at each `candidatePositions` from metadata |

**Edit for:** New virtual object parameters or rendering options.

---

## Supporting Modules (`modules/`)

### `modules/composite/`

- **`composite.py`** — Depth-aware compositing of real RGB + virtual object (or virtual plane)
- **`render.py`** — PyRender-based virtual object renderer; uses `VDRSequence` for pose
- **`vdr_sequence.py`** — Parses ARKit/VDR metadata for camera pose and object position

### `modules/inference/`

- **`base.py`** — `InferenceModel` abstract base with `infer(rgb) -> depth`
- **`inference_manager.py`** — Auto-discovers and loads model classes from `.py` files
- **`zoedepth.py`, `depthanything.py`** — Example depth estimation models

### `modules/datasets/`

- **`ScanNet/`** — ScanNet dataset loader for offline evaluation

### `modules/pointcloud.py`

- **`create_pointcloud()`** — RGB + depth + intrinsics → Open3D/trimesh point cloud

---

## Adding a New Inference Model

1. Create `modules/inference/my_model.py`:

```python
from modules.inference.base import InferenceModel
import numpy as np

class MyDepthModel(InferenceModel):
    def __init__(self):
        # Load your model here
        pass

    def infer(self, rgb_image: np.ndarray) -> np.ndarray:
        return depth_array
```

2. The model is auto-discovered on server start. Use `/list_inference_models` and `/select_inference_models` to enable it.

---

## Adding a New API Route

1. Implement handler in `handlers/` (or new file)
2. Import in `handlers/__init__.py`
3. Add route in `app.py`: `(r"/your_path", YourHandler)`

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `LIVE_ENCODING` | `webp` | `webp`, `jpg`, `png`, `webp_lossless` |
| `LIVE_QUALITY` | `80` | 1–100 for JPEG/WebP |
| `PNG_LEVEL` | `1` | 0–9 PNG compression |
