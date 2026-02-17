"""WebSocket handlers: frame capture, live stream, replay."""

import asyncio
import base64
import datetime
import glob
import io
import json
import os

import aiofiles
import cv2
import numpy as np
import tornado.websocket
from PIL import Image

from server import state
from server.config import BASE_SAVE_DIR
from server.session_mgr import SessionManager
from server.utils import read_json_file, update_virtual_position_from_metadata, _encode_image_bytes_rgb, build_mask, annotate_segment
from server.modules.composite.render import Renderer
from server.modules.composite.composite import composite


class FrameWebSocketHandler(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    async def open(self):
        self.set_nodelay(True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_folder = os.path.join(BASE_SAVE_DIR, f"session_{timestamp}")
        os.makedirs(self.session_folder, exist_ok=True)
        print("WebSocket opened. Session folder:", self.session_folder)

    async def on_message(self, message):
        try:
            data = json.loads(message)
        except Exception as e:
            await self.write_message(json.dumps({"error": "Invalid JSON: " + str(e)}))
            return

        msg_type = data.get("type")

        if msg_type == "initialize":
            state.global_rgb_resolution = data.get("rgbResolution")
            state.global_depth_resolution = data.get("depthResolution")
            state.global_intrinsics = data.get("intrinsics")
            virtual_object_path = data.get("virtual_object_path", state.current_model_path)

            if not (state.global_rgb_resolution and state.global_depth_resolution):
                await self.write_message(json.dumps({"error": "Missing resolutions"}))
                return

            session_config = {
                "rgb_resolution": state.global_rgb_resolution,
                "depth_resolution": state.global_depth_resolution,
                "intrinsics": state.global_intrinsics,
                "virtual_object_path": virtual_object_path,
                "scale": 0.006
            }
            config_filepath = os.path.join(self.session_folder, "session_config.json")
            async with aiofiles.open(config_filepath, "w") as f:
                await f.write(json.dumps(session_config, indent=4))

            state.init_event.set()
            await self.write_message(json.dumps({"message": "Initialization successful"}))
            print("Initialized:", state.global_rgb_resolution, state.global_depth_resolution)
            return

        elif msg_type == "frame":
            metadata = data.get("metadata")
            if not metadata:
                await self.write_message(json.dumps({"error": "Missing metadata"}))
                return

            update_virtual_position_from_metadata(metadata)

            mask_png = None
            for key in ("objectMask", "paritySnapshot"):
                mask_b64 = metadata.pop(key, None)
                if mask_b64:
                    try:
                        mask_png = base64.b64decode(mask_b64)
                    except Exception as e:
                        await self.write_message(json.dumps({"error": f"Error decoding mask PNG: {e}"}))
                    break

            rgb_base64 = data.get("rgbImage")
            depth_base64 = data.get("depthData")
            if not (rgb_base64 and depth_base64):
                await self.write_message(json.dumps({"error": "Missing image data"}))
                return

            try:
                rgb_bytes = base64.b64decode(rgb_base64)
                rgb_image = Image.open(io.BytesIO(rgb_bytes))
                rgb_data = np.asarray(rgb_image)
            except Exception as e:
                await self.write_message(json.dumps({"error": "Error processing RGB: " + str(e)}))
                return

            try:
                depth_bytes = base64.b64decode(depth_base64)
                depth_res = metadata.get("depthResolution") or state.global_depth_resolution
                if not depth_res:
                    await self.write_message(json.dumps({"error": "No depth resolution"}))
                    return
                depth_data = np.frombuffer(depth_bytes, dtype=np.float32).reshape(depth_res[::-1])
            except Exception as e:
                await self.write_message(json.dumps({"error": "Error processing depth: " + str(e)}))
                return

            task = {
                "metadata": {**metadata, "frame_idx": state.frame_counter},
                "rgb_data": rgb_data,
                "depth_data": depth_data,
                "model_path": state.current_model_path,
                "scale": 0.006,
                "frame_idx": state.frame_counter,
                "session_folder": self.session_folder
            }

            if mask_png is not None:
                task["mask_png"] = mask_png

            state.frame_counter += 1
            state.render_queue.put_latest(task)

            await self.write_message(json.dumps({"message": f"Frame {task['frame_idx']} queued"}))
            return

        else:
            await self.write_message(json.dumps({"error": "Unknown type"}))
            return

    def on_close(self):
        print("WebSocket closed. Session folder:", getattr(self, 'session_folder', 'N/A'))


class LiveStreamHandler(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    async def open(self):
        self.set_nodelay(True)
        state.live_clients.add(self)
        print("Live client connected.")

    async def on_message(self, message):
        pass

    def on_close(self):
        state.live_clients.discard(self)
        print("Live client disconnected.")


class ReplayStreamHandler(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    async def open(self):
        self.set_nodelay(True)
        session = self.get_query_argument("session", "")
        self.manager = SessionManager(session)
        if not self.manager.exists():
            await self.write_message(json.dumps({"error": "Session folder not found"}))
            self.close()
            return

        self.metadata_files = sorted(glob.glob(os.path.join(self.manager.session_folder, "frame_*_metadata.json")))
        if not self.metadata_files:
            await self.write_message(json.dumps({"error": "No replay frames found"}))
            self.close()
            return

        session_config_path = os.path.join(self.manager.session_folder, "session_config.json")
        session_config = read_json_file(session_config_path) if os.path.isfile(session_config_path) else {}
        session_config["virtual_object_path"] = state.current_model_path
        self.session_config = session_config
        self.replay_renderer = Renderer(
            model_path=state.current_model_path,
            scale=session_config.get("scale", 0.006),
            resolution=session_config.get("rgb_resolution"),
            intrinsics=session_config.get("intrinsics")
        )
        self.current_index = 0
        self.replaying = True
        print(f"Replay started for session: {self.manager.session} with {len(self.metadata_files)} frames")
        asyncio.create_task(self.send_replay_frames())

    async def send_replay_frames(self):
        frame_rate = 5
        delay = 1.0 / frame_rate
        while self.current_index < len(self.metadata_files) and self.replaying:
            metadata = read_json_file(self.metadata_files[self.current_index])
            update_virtual_position_from_metadata(metadata)
            base = os.path.splitext(os.path.basename(self.metadata_files[self.current_index]))[0]
            rgb_file = os.path.join(self.manager.session_folder, base.replace("metadata", "rgb") + ".png")
            depth_file = os.path.join(self.manager.session_folder, base.replace("metadata", "depth") + ".npy")
            raw_rgb = cv2.cvtColor(cv2.imread(rgb_file), cv2.COLOR_BGR2RGB)
            raw_depth = np.load(depth_file)
            if state.VIRTUAL_DEPTH is None:
                rendered_color, rendered_depth = self.replay_renderer.update_and_render(metadata, state.VIRTUAL_OBJECT_POSITION)
                mask_path = os.path.join(self.manager.session_folder, f"frame_{int(metadata['frame_idx']):05d}_server_mask.png")
                if not os.path.isfile(mask_path):
                    mask = build_mask(rendered_color)
                    cv2.imwrite(mask_path, mask)
            else:
                rendered_color, rendered_depth = None, None
            original_comp = composite(
                raw_rgb, raw_depth, rendered_color, rendered_depth,
                self.session_config["rgb_resolution"], virtual_depth=state.VIRTUAL_DEPTH
            )

            enc = _encode_image_bytes_rgb(original_comp)
            replay_frames = {"original": base64.b64encode(enc).decode("utf-8") if enc is not None else ""}

            if state.current_inference_models:
                for model_name, instance in state.current_inference_models:
                    inferred_depth = instance.infer(raw_rgb)
                    if hasattr(inferred_depth, "convert"):
                        inferred_depth = np.array(inferred_depth)
                    comp_inf = composite(
                        raw_rgb, inferred_depth, rendered_color, rendered_depth,
                    self.session_config["rgb_resolution"], virtual_depth=state.VIRTUAL_DEPTH
                )
                    comp_inf = annotate_segment(comp_inf, model_name)
                    enc_inf = _encode_image_bytes_rgb(comp_inf)
                    replay_frames[model_name] = base64.b64encode(enc_inf).decode("utf-8") if enc_inf is not None else ""
            await self.write_message(json.dumps({"replay_frames": replay_frames}))
            self.current_index += 1
            await asyncio.sleep(delay)
        try:
            await self.write_message(json.dumps({"message": "Replay finished"}))
        except Exception as e:
            print("Error sending replay finished message:", e)
        self.close()

    def on_close(self):
        self.replaying = False
        print("Replay client disconnected.")
