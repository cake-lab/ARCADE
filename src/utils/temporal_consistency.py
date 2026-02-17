import os
import torch
import argparse
from torchvision.models.optical_flow import raft_large, Raft_Large_Weights
from PIL import Image
import torchvision.transforms as T
import torch.nn.functional as F
from utils.utils import InputPadder
import numpy as np

class Metrics:
    def __init__(self, h, w, device):
        weights = Raft_Large_Weights.DEFAULT
        self.raft_oflow = raft_large(weights=weights).to(device)
        self.raft_oflow.eval()

        self.device = device
        self.h = h
        self.w = w

        self.ygrid, self.xgrid = torch.meshgrid(torch.arange(h - 1, -1, -1), torch.arange(0, w), indexing="ij")
        self.xgrid, self.ygrid = self.xgrid.to(device), self.ygrid.to(device)
        self.flow_limit = 250
        
    def TCC(self, d0, d1, gt0, gt1, mask=None):
        if mask == None:
            mask = torch.ones_like(d0).to(d0.get_device())

        ssimloss = SSIM(1.0, nonnegative_ssim=True)
        return  ssimloss( (torch.abs(d1 - d0) * mask.float()).expand(-1, 3, -1, -1),
                          (torch.abs(gt1 - gt0) * mask.float()).expand(-1, 3, -1, -1) )

        
    def TCM(self, d0, d1, gt0, gt1, mask=None):
        if mask == None:
            mask = torch.ones_like(d0).to(d0.get_device())

        b, _, h, w = d0.shape
        ssimloss = SSIM(1.0, nonnegative_ssim=True, size_average=False)

        dmax = torch.max(gt0.view(b, -1), -1)[0].view(b, 1, 1, 1).expand(-1, 3, -1, -1)
        dmin = torch.min(gt0.view(b, -1), -1)[0].view(b, 1, 1, 1).expand(-1, 3, -1, -1)
        
        d0_ = (d0.expand(-1, 3, -1, -1).to(self.device) - dmin) / (dmax - dmin) * 255.
        d1_ = (d1.expand(-1, 3, -1, -1).to(self.device) - dmin) / (dmax - dmin) * 255.
        flow = self.oflow( d0_, d1_ )

        gt0_ = (gt0.expand(-1, 3, -1, -1).to(self.device) - dmin) / (dmax - dmin) * 255.
        gt1_ = (gt1.expand(-1, 3, -1, -1).to(self.device) - dmin) / (dmax - dmin) * 255.
        flow_gt = self.oflow( gt0_, gt1_ )
        flow_mask = torch.sum(flow > self.flow_limit, 1, keepdim=True) == 0

        mask = torch.logical_and(flow_mask, mask)
        
        ssim = torch.mean(ssimloss( torch.cat( (flow, torch.ones_like(flow[:, 0, None, ...])), 1) * mask.expand(-1, 3, -1, -1),
                                    torch.cat( (flow_gt, torch.ones_like(flow[:, 0, None, ...])), 1) * mask.expand(-1, 3, -1, -1) )[:, :2])
        return ssim
    
    def oflow(self, image1, image2):
        padder = InputPadder(image1.shape)
        image1, image2 = padder.pad(image1 / 255.0, image2 / 255.0)

        with torch.no_grad():
            flow = self.raft_oflow(image1, image2)[0][-1].unsqueeze(0)
        return flow

    def OPW(self, d0, d1, img0, img1, resample=False, pose_d0_to_d1=None, K=None, mask=None):
        if mask is None:
            mask = torch.ones_like(d0).to(self.device)

        flow = self.oflow(img0, img1)
        flow_mask = torch.sum(flow > self.flow_limit, 1, keepdim=True) == 0

        if resample:
            pts = torch.stack((self.xgrid, self.ygrid, d0[0, 0, ...]), 0).view(3, -1)
            pc = torch.matmul(pose_d0_to_d1, torch.stack(((pts[0, ...] - K[0, 2]) * pts[2, ...] / K[0, 0],
                                                          (pts[1, ...] - K[1, 2]) * pts[2, ...] / K[1, 1],
                                                          -pts[2, ...],
                                                          torch.ones_like(pts[2, ...], dtype=torch.double).to(self.device)), 0))
            d0_t = torch.abs(pc[2, ...].view(self.h, self.w)).view(1, 1, self.h, self.w)
        else:
            d0_t = d0

        batch_size = flow.shape[0]
        xgrid = self.xgrid.unsqueeze(0).unsqueeze(1).expand(batch_size, 1, self.h, self.w)
        ygrid = self.ygrid.unsqueeze(0).unsqueeze(1).expand(batch_size, 1, self.h, self.w)

        x_norm = (xgrid[:, 0, :, :] + flow[:, 0, :, :]) / (self.w - 1) * 2 - 1.0
        y_norm = (ygrid[:, 0, :, :] - flow[:, 1, :, :]) / (self.h - 1) * 2 - 1.0
        y_norm *= -1

        grid = torch.stack((x_norm, y_norm), -1).float()
        d1_sampled = F.grid_sample(d1, grid, align_corners=True)
        img1_sampled = F.grid_sample(img1 / 255., grid, align_corners=True)

        mask = torch.exp(-50. * torch.sqrt(((img0 / 255. - img1_sampled) ** 2).sum(1))) * flow_mask * mask * (d1_sampled > 0) > 1e-2
        m = torch.sum(mask)

        err = torch.sum(torch.abs(d1_sampled - d0_t) * mask) / m
        return err

def load_pickle(file_path):
    import pickle
    with open(file_path, 'rb') as f:
        return pickle.load(f)

def load_bin(file_path):
    d =  torch.tensor(np.fromfile(file_path, dtype=np.float32).reshape(192, 256))
    return d.unsqueeze(0).unsqueeze(0)

def load_image(file_path):
    transform = T.Compose([T.ToTensor()])
    img = transform(Image.open(file_path).convert('RGB')).unsqueeze(0)
    return img

def main():
    parser = argparse.ArgumentParser(description="Compute OPW Metric for a Dataset")
    parser.add_argument('--image_dir', type=str, required=True, help="Directory containing RGB images")
    parser.add_argument('--depth_dir', type=str, required=True, help="Directory containing depth map pickles or bin files")

    args = parser.parse_args()

    image_files = sorted([os.path.join(args.image_dir, f) for f in os.listdir(args.image_dir) if f.endswith(('.jpg', '.png'))])
    depth_files = sorted([os.path.join(args.depth_dir, f) for f in os.listdir(args.depth_dir) if f.endswith(('.pickle', '.bin', 'zoedepth_depth.npy'))])
    print(depth_files)
    # Handle mismatch in starting frame indices
    if image_files and depth_files and "frame_0.jpg" in image_files[0] and not "0.pickle" in depth_files[0] and depth_files[0].endswith('.pickle'):
        image_files.pop(0)

    print(f"Found {len(image_files)} images and {len(depth_files)} depth maps.")
    if len(image_files) != len(depth_files):
        raise ValueError("Number of images and depth maps must match.")

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    total_opw = 0.0
    metrics = None

    for i in range(len(image_files) - 1):
        if depth_files[i].endswith('.pickle'):
            d0_data = load_pickle(depth_files[i])["depth_pred_s0_b1hw"]
            d1_data = load_pickle(depth_files[i + 1])["depth_pred_s0_b1hw"]
        elif depth_files[i].endswith('.bin'):
            d0_data = load_bin(depth_files[i])
            d1_data = load_bin(depth_files[i + 1])
        elif depth_files[i].endswith('.npy'):
            d0_data = torch.tensor(np.load(depth_files[i])).to(device).unsqueeze(0).unsqueeze(0)
            d1_data = torch.tensor(np.load(depth_files[i + 1])).to(device).unsqueeze(0).unsqueeze(0)
            

        d0 = d0_data.to(device)
        d1 = d1_data.to(device)
        # d0 = d0.squeeze(0)
        # d1 = d1.squeeze(0)
        img0 = load_image(image_files[i]).to(device)
        img1 = load_image(image_files[i + 1]).to(device)

        # d0 = F.interpolate(d0, (480, 640), mode='bilinear', align_corners=False)
        # d1 = F.interpolate(d1, (480, 640), mode='bilinear', align_corners=False)
        
        # Resize depth maps and images to 128x256
        d0 = F.interpolate(d0, (128, 256), mode='bilinear', align_corners=False)
        d1 = F.interpolate(d1, (128, 256), mode='bilinear', align_corners=False)
        img0 = F.interpolate(img0, (128, 256), mode='bilinear', align_corners=False)
        img1 = F.interpolate(img1, (128, 256), mode='bilinear', align_corners=False)
        
        if metrics is None:
            metrics = Metrics(h=d0.shape[2], w=d0.shape[3], device=device)
            
        opw_metric = metrics.OPW(d0, d1, img0, img1, resample=False)
        total_opw += opw_metric.item()
        
        # Print progress
        print(f"Processed {i + 1}/{len(image_files) - 1} images. Current OPW Metric: {opw_metric.item()}")

    avg_opw = total_opw / (len(image_files) - 1)
    print(f"Average OPW Metric: {avg_opw}")

if __name__ == '__main__':
    main()
