"""Mesh upload, list, select handlers."""

import json
import os

from server import state
from server.config import MESH_DIR
from server.handlers.base import BaseHandler
from server.session_mgr import SessionManager
from server.utils import read_json_file, update_virtual_position_from_metadata
import glob


class MeshSettingsHandler(BaseHandler):
    def get(self):
        force_from_metadata = self.get_argument("force_from_metadata", "false").lower() == "true"

        if not force_from_metadata and state.VIRTUAL_OBJECT_POSITION_MANUAL_SET and state.VIRTUAL_OBJECT_POSITION is not None:
            self.write_json({"object_position": state.VIRTUAL_OBJECT_POSITION})
            return

        session = self.get_argument("session", None)
        if session:
            manager = SessionManager(session)
            if manager.exists():
                metadata_files = sorted(glob.glob(os.path.join(manager.session_folder, "frame_*_metadata.json")))
                if metadata_files:
                    latest = metadata_files[-1]
                    metadata = read_json_file(latest)
                    if "objPosition" in metadata:
                        if force_from_metadata or not state.VIRTUAL_OBJECT_POSITION_MANUAL_SET:
                            update_virtual_position_from_metadata(metadata)
                            if force_from_metadata:
                                state.VIRTUAL_OBJECT_POSITION_MANUAL_SET = False
                        self.write_json({"object_position": metadata["objPosition"]})
                        return

        pos = state.VIRTUAL_OBJECT_POSITION if state.VIRTUAL_OBJECT_POSITION is not None else [0.0, 0.0, 0.0]
        self.write_json({"object_position": pos})


class MeshUploadHandler(BaseHandler):
    def post(self):
        if "mesh" not in self.request.files:
            self.error_response("Mesh file not provided")
            return
        fileinfo = self.request.files["mesh"][0]
        filename = fileinfo.filename
        if not filename.lower().endswith(".obj"):
            self.error_response("Only .obj files allowed")
            return
        file_path = os.path.join(MESH_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(fileinfo.body)
        state.current_model_path = file_path
        self.write_json({"message": "Mesh uploaded successfully", "mesh_path": file_path})


class ListMeshesHandler(BaseHandler):
    def get(self):
        files = [f for f in os.listdir(MESH_DIR) if f.lower().endswith(".obj")]
        self.write_json({"meshes": files})


class SelectMeshHandler(BaseHandler):
    def post(self):
        try:
            data = json.loads(self.request.body)
        except Exception as e:
            self.error_response("Invalid JSON: " + str(e))
            return
        mesh = data.get("mesh")
        if not mesh:
            self.error_response("Missing mesh parameter")
            return
        candidate = os.path.join(MESH_DIR, mesh)
        if not os.path.isfile(candidate):
            self.error_response("Mesh file does not exist: " + candidate)
            return
        state.current_model_path = candidate
        if candidate not in state.current_model_paths:
            state.current_model_paths.append(candidate)
        print("Mesh selected:", candidate)
        self.write_json({"message": "Mesh selected successfully", "mesh_path": candidate})


class SelectMultipleMeshesHandler(BaseHandler):
    def post(self):
        try:
            data = json.loads(self.request.body)
        except Exception as e:
            self.error_response("Invalid JSON: " + str(e))
            return
        meshes = data.get("meshes", [])
        if not meshes:
            self.error_response("Missing meshes parameter")
            return

        valid_meshes = []
        for mesh in meshes:
            candidate = os.path.join(MESH_DIR, mesh)
            if os.path.isfile(candidate):
                valid_meshes.append(candidate)
            else:
                self.error_response(f"Mesh file does not exist: {candidate}")
                return

        state.current_model_paths = valid_meshes
        print("Multiple meshes selected:", valid_meshes)
        self.write_json({"message": "Multiple meshes selected successfully", "mesh_paths": valid_meshes})


class GetCurrentMeshesHandler(BaseHandler):
    def get(self):
        self.write_json({"current_meshes": state.current_model_paths})
