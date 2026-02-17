import numpy as np
import trimesh
import pyrender
import os
import cv2
from .vdr_sequence import VDRSequence
os.environ["PYOPENGL_PLATFORM"] = "egl"

np.infty = np.inf

class Renderer:
    def __init__(self, model_path, scale, resolution, intrinsics):
        self.mesh = trimesh.load(model_path)
        self.mesh.apply_scale(scale)
        self.material = pyrender.MetallicRoughnessMaterial(
            baseColorFactor=[1.0, 0.7, 0.2, 1.0],  
            metallicFactor=0.5,   
            roughnessFactor=0.5  
        )
        self.trimesh_mesh = pyrender.Mesh.from_trimesh(self.mesh, material=self.material)

        width, height = resolution[0], resolution[1]
        scale_factor = 1
        new_resolution = (int(height * scale_factor), int(width * scale_factor))
        self.renderer = pyrender.OffscreenRenderer(
            viewport_width=new_resolution[1],
            viewport_height=new_resolution[0]
        )
        
        self.scene = pyrender.Scene()
        self.mesh_node = self.scene.add(self.trimesh_mesh, name="mesh")

        key_light = pyrender.DirectionalLight(color=np.array([1.0, 0.98, 0.95]), intensity=2.5)
        self.scene.add(key_light, pose=np.eye(4))
        fill_light = pyrender.DirectionalLight(color=np.array([0.8, 0.85, 1.0]), intensity=1.5)
        fill_pose = np.eye(4)
        fill_pose[:3, 3] = [1.5, 2.0, 1.5]
        self.scene.add(fill_light, pose=fill_pose)
        ambient_light = pyrender.PointLight(color=np.array([1.0, 1.0, 1.0]), intensity=0.5)
        ambient_pose = np.eye(4)
        ambient_pose[:3, 3] = [-2.0, 3.0, -2.0]
        self.scene.add(ambient_light, pose=ambient_pose)
        
        # Scale intrinsics
        fx, fy, cx, cy = intrinsics
        fx, fy, cx, cy = fx * scale_factor, fy * scale_factor, cx * scale_factor, cy * scale_factor
        self.camera = pyrender.IntrinsicsCamera(fx=fx, fy=fy, cx=cx, cy=cy)
        self.camera_node = self.scene.add(self.camera, pose=np.eye(4), name="camera")

    def update_and_render(self, metadata, virtual_object_position_override=None):
        vdr_sequence = VDRSequence(metadata)
        frame = dict(metadata)
        
        if virtual_object_position_override is not None:
            translation = np.array(virtual_object_position_override)
        else:
            translation = vdr_sequence.load_obj_location(frame)
        mesh_translation = np.eye(4)
        mesh_translation[:3, 3] = translation
        self.mesh_node.matrix = mesh_translation

        pose = vdr_sequence.load_extrinsics_for_frame(frame).as_transform().as_matrix()
        self.camera_node.matrix = pose

        flags = (
            pyrender.RenderFlags.RGBA
            | pyrender.RenderFlags.SHADOWS_DIRECTIONAL
            | pyrender.RenderFlags.ALL_SOLID
        )
        color, depth = self.renderer.render(self.scene, flags=flags)
        color = np.array(color, copy=True)
        
        transparent_background = np.all(color[:, :, :3] == 255, axis=-1)
        color[transparent_background, 3] = 0
        
        return color, depth