"""Server entry point: init state, dataset, workers, and run Tornado."""

import threading
import torch
import tornado.ioloop

from server import config, state
from server.app import make_app
from server.workers import render_worker, save_worker
from server.modules.datasets.ScanNet.scannet_dataset import ScannetDataset


def main():
    state.init_queues_and_pool()
    state.main_ioloop = tornado.ioloop.IOLoop.current()

    dataset_path = "/project/ScanNet/data"
    state.global_dataset = ScannetDataset(
        dataset_path=dataset_path,
        split="test",
        include_full_res_depth=True,
        include_full_depth_K=True,
        include_high_res_color=True,
        pass_frame_id=True,
        image_height=480,
        image_width=640,
        tuple_info_file_location="server/modules/datasets/data_splits/ScanNet/",
        mv_tuple_file_suffix="_eight_view_deepvmvs.txt",
        num_images_in_tuple=8,
    )
    state.global_dataloader = torch.utils.data.DataLoader(
        state.global_dataset,
        batch_size=1,
        shuffle=False,
        num_workers=0,
        drop_last=False,
    )
    state.global_data_iter = iter(state.global_dataloader)

    threading.Thread(target=render_worker, daemon=True).start()
    threading.Thread(target=save_worker, daemon=True).start()

    app = make_app()
    port = 5034
    app.listen(port)
    print(f"Server started on port {port} | LIVE_ENCODING={config.LIVE_ENCODING} QUALITY={config.LIVE_QUALITY}")
    state.main_ioloop.start()

    state.render_queue.put(None)
    state.save_queue.put(None)
    print("Server stopped")


if __name__ == "__main__":
    main()
