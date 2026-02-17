from transformers import pipeline
from PIL import Image
import numpy as np
from server.modules.inference.base import InferenceModel

class DepthAnythingModel(InferenceModel):
    def __init__(self):
        self.pipe = pipeline(task="depth-estimation", model="depth-anything/Depth-Anything-V2-Metric-Indoor-Base-hf")

    def infer(self, rgb_image: np.ndarray) -> np.ndarray:
        image = Image.fromarray(rgb_image)
        result = self.pipe(image)
        depth = result["predicted_depth"]
        depth = np.array(depth)
        
        return depth
