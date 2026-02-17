"""ScanNet dataset info and frame handlers."""

import base64
import cv2
import numpy as np

from server import state
from server.handlers.base import BaseHandler
from server.utils import generate_depth_colormap, _encode_image_bytes_rgb
from server.modules.composite.composite import composite


def convert_to_builtin_type(obj):
    if isinstance(obj, np.generic):
        return obj.item()
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (list, tuple)):
        return type(obj)(convert_to_builtin_type(x) for x in obj)
    elif isinstance(obj, dict):
        return {k: convert_to_builtin_type(v) for k, v in obj.items()}
    else:
        return obj


class DatasetInfoHandler(BaseHandler):
    def get(self):
        if state.global_dataset is None:
            self.error_response("Dataset not loaded", status=503)
            return
        self.write_json({"num_frames": len(state.global_dataset)})


class DatasetFrameHandler(BaseHandler):
    def get(self):
        try:
            frame_id = int(self.get_argument("frame"))
        except Exception as e:
            self.write_json({"error": "Invalid frame id: " + str(e)})
            return
        if state.global_dataset is None:
            self.error_response("Dataset not loaded", status=503)
            return
        try:
            sample = state.global_dataset[frame_id]
        except Exception as e:
            self.write_json({"error": "Error loading frame: " + str(e)})
            return
        try:
            sample = sample[0]
            color_key = "high_res_color_b3hw"
            depth_key = "full_res_depth_b1hw"
            rgb_array = sample[color_key].numpy()
            rgb_array = np.transpose(rgb_array, (1, 2, 0))
            depth = sample[depth_key].numpy().squeeze()
            depth = np.nan_to_num(depth)
            intrinsics = sample["K_full_depth_b44"].numpy().tolist()
            resolution = (int(rgb_array.shape[1]), int(rgb_array.shape[0]))
        except Exception as e:
            self.write_json({"error": "Error processing sample: " + str(e)})
            return

        rgb_array = np.clip(rgb_array * 255, 0, 255).astype(np.uint8)

        virtual_depth_param = self.get_argument("virtual_depth", None)
        if virtual_depth_param is not None:
            try:
                virtual_depth_ui = float(virtual_depth_param)
            except Exception:
                virtual_depth_ui = state.VIRTUAL_DEPTH
        else:
            virtual_depth_ui = state.VIRTUAL_DEPTH

        comp = composite(255 - rgb_array, depth, None, None, resolution, virtual_depth=virtual_depth_ui)
        comp = np.clip(comp * 255, 0, 255).astype(np.uint8)

        comp_enc = _encode_image_bytes_rgb(comp)
        if comp_enc is None:
            self.write_json({"error": "Failed to encode composite image"})
            return
        comp_base64 = base64.b64encode(comp_enc).decode("utf-8")

        def compute_depth_errors(gt, pred):
            valid = (gt > 0) & (~np.isnan(gt))
            if np.sum(valid) == 0:
                return {"RMSE": None, "MSE": None, "AbsRel": None, "A1": None, "A2": None, "A3": None}
            gt_valid = gt[valid]
            pred_valid = pred[valid]
            mse = np.mean((gt_valid - pred_valid) ** 2)
            rmse = np.sqrt(mse)
            abs_rel = np.mean(np.abs(gt_valid - pred_valid) / gt_valid)
            max_ratio = np.maximum(gt_valid / pred_valid, pred_valid / gt_valid)
            a1 = np.mean(max_ratio < 1.25)
            a2 = np.mean(max_ratio < 1.25 ** 2)
            a3 = np.mean(max_ratio < 1.25 ** 3)
            return {"RMSE": float(rmse), "MSE": float(mse), "AbsRel": float(abs_rel),
                    "A1": float(a1), "A2": float(a2), "A3": float(a3)}

        gt_depth_colormap = generate_depth_colormap(depth, cmap_name='jet')
        gt_depth_colormap_b64 = base64.b64encode(gt_depth_colormap).decode("utf-8")

        inferred_depth_colormaps = {}
        inferred_composites = {}
        depth_errors = {}
        if state.current_inference_models:
            for model_name, instance in state.current_inference_models:
                inferred_depth = instance.infer(rgb_array)
                if hasattr(inferred_depth, "convert"):
                    inferred_depth = np.array(inferred_depth)
                inferred_depth_colormap = generate_depth_colormap(inferred_depth, cmap_name='jet')
                inferred_depth_colormaps[model_name] = base64.b64encode(inferred_depth_colormap).decode("utf-8")
                comp_inferred = composite(rgb_array, inferred_depth, None, None, resolution, virtual_depth=state.VIRTUAL_DEPTH)
                comp_inf_enc = _encode_image_bytes_rgb(comp_inferred)
                if comp_inf_enc:
                    inferred_composites[model_name] = base64.b64encode(comp_inf_enc).decode("utf-8")
                else:
                    inferred_composites[model_name] = ""
                depth_errors[model_name] = compute_depth_errors(depth, inferred_depth)

        ret_rgb, buf_rgb = cv2.imencode('.png', cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR))
        original_rgb_b64 = base64.b64encode(buf_rgb.tobytes()).decode("utf-8") if ret_rgb else ""

        output = {
            "frame_id": frame_id,
            "original_rgb": original_rgb_b64,
            "composite": comp_base64,
            "gt_depth_colormap": gt_depth_colormap_b64,
            "intrinsics": intrinsics,
            "resolution": resolution,
            "max_depth": float(depth.max()),
            "min_depth": float(depth.min()),
            "inferred_depth_colormaps": inferred_depth_colormaps,
            "inferred_composites": inferred_composites,
            "depth_errors": depth_errors
        }
        self.write_json(convert_to_builtin_type(output))
