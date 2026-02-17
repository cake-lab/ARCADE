# code adapted from https://github.com/nianticlabs/implicit-depth/blob/main/inference/composite.py
from pathlib import Path
import cv2
import numpy as np
import torch
import torch.nn.functional as F


DEPTH_ALPHA_BAND_SIZE = 0.01  # metres

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def get_mask(predicted, virtual, soft: bool):
    """
    Returns a matte in [0,1] where 1 = show REAL RGB, 0 = show VIRTUAL RGB.
    Soft == True uses a linear ramp (alpha band) around the depth edge.
    """
    diff = virtual - predicted
    if soft:
        half = DEPTH_ALPHA_BAND_SIZE * 0.5
        matte = (diff + half) / (2 * half)
        return torch.clamp(matte, 0.0, 1.0)
    else:
        return (diff > 0).float()


def composite(
    rgb_image,
    depth_data,
    rendered_color,
    rendered_depth,
    resolution,
    virtual_depth=None,
    use_depth_banding=True,
):
    """
    Alpha-aware, depth-correct compositing.
    Returns uint8 HxWx3.
    """
    # Unpack resolution as (W, H)
    W, H = resolution
    # real rgb assumed uint8 HxWx3 or float 0..255; normalize to [0,1]
    real_rgb = torch.tensor(rgb_image, dtype=torch.float32, device=device)
    if real_rgb.max() > 1.0:
        real_rgb = real_rgb / 255.0
    # to NCHW for resize, then back to HWC @ (H, W)
    real_rgb = real_rgb.permute(2, 0, 1).unsqueeze(0)                       # [1,3,h0,w0]
    real_rgb = F.interpolate(real_rgb, size=(H, W), mode="bilinear", align_corners=False)
    real_rgb = real_rgb.squeeze(0).permute(1, 2, 0).contiguous()             # [H,W,3]

    # real depth to (H, W), use NEAREST to avoid mixing invalids
    real_depth = torch.tensor(depth_data, dtype=torch.float32, device=device)
    if real_depth.ndim == 2:
        real_depth = real_depth.unsqueeze(0).unsqueeze(0)                    # [1,1,h0,w0]
    elif real_depth.ndim == 3:
        # if [H,W,1] or [1,H,W], make it [1,1,H,W]
        if real_depth.shape[-1] == 1:
            real_depth = real_depth.permute(2, 0, 1).unsqueeze(0)
        else:
            real_depth = real_depth.unsqueeze(0)
    else:
        raise ValueError(f"Unexpected depth_data shape: {depth_data.shape}")

    real_depth = F.interpolate(real_depth, size=(H, W), mode="nearest").squeeze(0).squeeze(0)  # [H,W]

    if virtual_depth is None:
        # rendered_color expected RGBA HxWx4 in uint8 or float
        virt_rgba = torch.tensor(rendered_color, dtype=torch.float32, device=device)
        if virt_rgba.max() > 1.0:
            virt_rgba = virt_rgba / 255.0
        # to NCHW for resize
        virt_rgba = virt_rgba.permute(2, 0, 1).unsqueeze(0)                   # [1,4,hv,wv]
        virt_rgba = F.interpolate(virt_rgba, size=(H, W), mode="bilinear", align_corners=False)
        virt_rgba = virt_rgba.squeeze(0).permute(1, 2, 0).contiguous()        # [H,W,4]
        virtual_rgb = virt_rgba[..., :3]                                      # [H,W,3]
        virtual_alpha = virt_rgba[..., 3]                                     # [H,W]

        # rendered_depth to (H, W)
        virt_depth = torch.tensor(rendered_depth, dtype=torch.float32, device=device)
        if virt_depth.ndim == 2:
            virt_depth = virt_depth.unsqueeze(0).unsqueeze(0)
        elif virt_depth.ndim == 3:
            if virt_depth.shape[-1] == 1:
                virt_depth = virt_depth.permute(2, 0, 1).unsqueeze(0)
            else:
                virt_depth = virt_depth.unsqueeze(0)
        virt_depth = F.interpolate(virt_depth, size=(H, W), mode="nearest").squeeze(0).squeeze(0)

        valid_virtual = ((virt_depth > 0.0).float() * (virtual_alpha > 0.01).float())
        matte = get_mask(predicted=real_depth, virtual=virt_depth, soft=use_depth_banding)
        matte = torch.clamp(matte * valid_virtual + (1.0 - valid_virtual), 0.0, 1.0)

    else:
        virtual_rgb = torch.zeros((H, W, 3), dtype=torch.float32, device=device)
        virtual_rgb[..., 0] = 0.30
        virtual_rgb[..., 1] = 0.90
        virtual_rgb[..., 2] = 0.78
        virt_depth = torch.ones_like(real_depth) * float(virtual_depth)
        valid_virtual = torch.ones_like(real_depth)
        matte = get_mask(predicted=real_depth, virtual=virt_depth, soft=use_depth_banding)
        matte = torch.clamp(matte * valid_virtual + (1.0 - valid_virtual), 0.0, 1.0)

    matte = matte.unsqueeze(-1)  # [H,W,1]
    out = matte * real_rgb + (1.0 - matte) * virtual_rgb
    out = torch.clamp(out * 255.0 + 0.5, 0.0, 255.0).byte().detach().cpu().numpy()  # uint8

    return out