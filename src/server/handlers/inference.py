"""Inference model list, select, upload handlers."""

import json
import os

from server import state
from server.config import INFERENCE_MODEL_DIR
from server.handlers.base import BaseHandler
from server.modules.inference.inference_manager import list_models, select_model, reload_models


class ListInferenceModelsHandler(BaseHandler):
    def get(self):
        self.write_json({"models": list_models()})


class SelectInferenceModelsHandler(BaseHandler):
    def post(self):
        try:
            data = json.loads(self.request.body)
        except Exception as e:
            self.error_response("Invalid JSON: " + str(e))
            return
        models_list = data.get("models")
        if models_list is None:
            self.error_response("Missing models parameter")
            return
        state.current_inference_models = []
        for model_name in models_list:
            try:
                instance = select_model(model_name)
                state.current_inference_models.append((model_name, instance))
            except Exception as e:
                self.write_json({"error": f"Error loading model {model_name}: {str(e)}"})
                return
        self.write_json({"message": "Inference models selected", "models": models_list})


class GetSelectedModelsHandler(BaseHandler):
    def get(self):
        selected_models = [model_name for model_name, _ in state.current_inference_models]
        self.write_json({"models": selected_models})


class UploadInferenceModelHandler(BaseHandler):
    def post(self):
        if "model" not in self.request.files:
            self.error_response("Model file not provided")
            return
        fileinfo = self.request.files["model"][0]
        filename = fileinfo.filename
        if not filename.lower().endswith(".py"):
            self.error_response("Only .py files allowed")
            return
        file_path = os.path.join(INFERENCE_MODEL_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(fileinfo.body)
        reload_models()
        self.write_json({"message": "Inference model uploaded successfully", "model_file": filename})
