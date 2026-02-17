import numpy as np

class InferenceModel:
    def infer(self, rgb_image: np.ndarray) -> np.ndarray:
        raise NotImplementedError("Subclasses must implement the infer method")
