"""Background workers: render loop, save loop, live broadcast."""

import asyncio
import json
import os
import queue

from server import state
from server.config import BASE_SAVE_DIR
from server.utils import _encode_image_bytes_rgb
from server.modules.composite.render import Renderer
from server.modules.composite.composite import composite


async def broadcast_live_frame(image_bytes):
    if not state.live_clients:
        return

    async def _send(client):
        try:
            await asyncio.wait_for(client.write_message(image_bytes, binary=True), timeout=0.1)
            return True
        except Exception:
            return False

    clients_snapshot = list(state.live_clients)
    results = await asyncio.gather(*[_send(c) for c in clients_snapshot], return_exceptions=True)
    for c, ok in zip(clients_snapshot, results):
        if ok is not True:
            try:
                state.live_clients.discard(c)
                c.close()
            except Exception:
                pass


def save_data_blocking(data):
    frame_idx = data["frame_idx"]
    session_folder = data.get("session_folder", BASE_SAVE_DIR)

    if data.get("mask_png"):
        mask_filename = os.path.join(session_folder, f"frame_{frame_idx:05d}_mask.png")
        with open(mask_filename, "wb") as mf:
            mf.write(data["mask_png"])
        data["metadata"]["objectMaskFile"] = os.path.basename(mask_filename)

    meta_filename = os.path.join(session_folder, f"frame_{frame_idx:05d}_metadata.json")
    with open(meta_filename, "w") as f:
        json.dump(data["metadata"], f, indent=4)

    import cv2
    import numpy as np
    rgb_filename = os.path.join(session_folder, f"frame_{frame_idx:05d}_rgb.png")
    cv2.imwrite(rgb_filename, cv2.cvtColor(data["rgb_data"], cv2.COLOR_RGB2BGR))

    depth_filename = os.path.join(session_folder, f"frame_{frame_idx:05d}_depth.npy")
    np.save(depth_filename, data["depth_data"], allow_pickle=False)


def render_worker():
    state.init_event.wait()
    active_model_path = state.current_model_path
    renderer = Renderer(
        model_path=active_model_path,
        scale=0.006,
        resolution=state.global_rgb_resolution,
        intrinsics=state.global_intrinsics
    )
    while True:
        task = state.render_queue.get()
        try:
            while True:
                try:
                    newer = state.render_queue.get_nowait()
                    state.render_queue.task_done()
                    task = newer
                except queue.Empty:
                    break

            if state.current_model_path != active_model_path:
                active_model_path = state.current_model_path
                renderer = Renderer(
                    model_path=active_model_path,
                    scale=0.006,
                    resolution=state.global_rgb_resolution,
                    intrinsics=state.global_intrinsics
                )

            try:
                rendered_color, rendered_depth = renderer.update_and_render(
                    task['metadata'], state.VIRTUAL_OBJECT_POSITION
                )
            except Exception as e:
                if hasattr(e, "err") and e.err == 12289:
                    renderer = Renderer(
                        model_path=state.current_model_path,
                        scale=0.006,
                        resolution=state.global_rgb_resolution,
                        intrinsics=state.global_intrinsics
                    )
                    rendered_color, rendered_depth = renderer.update_and_render(
                        task['metadata'], state.VIRTUAL_OBJECT_POSITION
                    )
                else:
                    raise e

            comp = composite(
                task['rgb_data'],
                task['depth_data'],
                rendered_color,
                rendered_depth,
                state.global_rgb_resolution,
                virtual_depth=state.VIRTUAL_DEPTH
            )
            image_bytes = _encode_image_bytes_rgb(comp)
            if image_bytes is not None:
                state.main_ioloop.spawn_callback(broadcast_live_frame, image_bytes)
            else:
                print(f"Failed to encode frame {task['frame_idx']}")

            try:
                state.save_queue.put_nowait({
                    "frame_idx": task["frame_idx"],
                    "metadata": task["metadata"],
                    "rgb_data": task["rgb_data"],
                    "depth_data": task["depth_data"],
                    "session_folder": task["session_folder"],
                    "mask_png": task.get("mask_png")
                })
            except Exception:
                pass

            if state.render_queue.qsize() > 1:
                print("Render backlog:", state.render_queue.qsize())

        except Exception as e:
            print(f"Error processing frame {task.get('frame_idx','?')}: {e}")
        finally:
            state.render_queue.task_done()


def save_worker():
    while True:
        data = state.save_queue.get()
        if data is None:
            break
        try:
            state.fileio_pool.submit(save_data_blocking, data)
            if state.save_queue.qsize() > 16:
                print("Save backlog:", state.save_queue.qsize())
        except Exception as e:
            print("save_worker submit error:", e)
        finally:
            state.save_queue.task_done()
