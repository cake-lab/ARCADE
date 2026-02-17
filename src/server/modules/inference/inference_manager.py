import os
import importlib
from server.modules.inference.base import InferenceModel

models = {}

def load_models():
    global models
    base_dir = os.path.dirname(os.path.abspath(__file__))
    for file in os.listdir(base_dir):
        if file.endswith(".py") and file not in ["__init__.py", "base.py", "inference_manager.py"]:
            module_name = file[:-3]
            module = importlib.import_module(f".{module_name}", package=__package__)
            for attr in dir(module):
                obj = getattr(module, attr)
                try:
                    if issubclass(obj, InferenceModel) and obj is not InferenceModel:
                        models[module_name] = obj
                except TypeError:
                    continue


def reload_models():
    global models
    models.clear()
    load_models()

def list_models():
    return list(models.keys())

current_inference_model = None

def select_model(model_name):
    global current_inference_model
    if model_name not in models:
        raise ValueError(f"Model {model_name} not available")
    current_inference_model = models[model_name]()
    return current_inference_model

def get_current_model():
    return current_inference_model

load_models()
