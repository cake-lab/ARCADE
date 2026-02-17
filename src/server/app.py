"""Tornado application and route list."""

import tornado.web

from server.handlers import (
    FrameWebSocketHandler,
    LiveStreamHandler,
    ReplayStreamHandler,
    MeshUploadHandler,
    ListMeshesHandler,
    SelectMeshHandler,
    SelectMultipleMeshesHandler,
    GetCurrentMeshesHandler,
    ListInferenceModelsHandler,
    SelectInferenceModelsHandler,
    GetSelectedModelsHandler,
    UploadInferenceModelHandler,
    SessionListHandler,
    ListFramesHandler,
    FrameDetailsHandler,
    PointCloudPlyHandler,
    PointCloudInfoHandler,
    DatasetInfoHandler,
    DatasetFrameHandler,
    UpdateVirtualSettingsHandler,
    RenderPositionsHandler,
    MeshSettingsHandler,
)


def make_app():
    return tornado.web.Application([
        (r"/websocket", FrameWebSocketHandler),
        (r"/live", LiveStreamHandler),
        (r"/replay", ReplayStreamHandler),
        (r"/upload_mesh", MeshUploadHandler),
        (r"/list_meshes", ListMeshesHandler),
        (r"/select_mesh", SelectMeshHandler),
        (r"/select_multiple_meshes", SelectMultipleMeshesHandler),
        (r"/get_current_meshes", GetCurrentMeshesHandler),
        (r"/list_inference_models", ListInferenceModelsHandler),
        (r"/select_inference_models", SelectInferenceModelsHandler),
        (r"/get_selected_models", GetSelectedModelsHandler),
        (r"/upload_inference_model", UploadInferenceModelHandler),
        (r"/list_sessions", SessionListHandler),
        (r"/list_frames", ListFramesHandler),
        (r"/frame_details", FrameDetailsHandler),
        (r"/point_cloud", PointCloudPlyHandler),
        (r"/point_cloud_info", PointCloudInfoHandler),
        (r"/dataset_info", DatasetInfoHandler),
        (r"/dataset_frame", DatasetFrameHandler),
        (r"/update_virtual_settings", UpdateVirtualSettingsHandler),
        (r"/render_positions", RenderPositionsHandler),
        (r"/mesh_settings", MeshSettingsHandler),
    ])
