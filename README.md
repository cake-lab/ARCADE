<div align="center">

# ARCADE

### AR as an Evaluation Playground: Bridging Metric and Visual Perception of Computer Vision Models

[![arXiv](https://img.shields.io/badge/arXiv-2508.04102-b31b1b.svg)](https://arxiv.org/abs/2508.04102)

[**Ashkan Ganj**](https://ashkanganj.me/)<sup>1</sup> · [**Yiqin Zhao**](https://yiqinzhao.phd/)<sup>2</sup> · [**Tian Guo**](https://tianguo.info/)<sup>1</sup>

<sup>1</sup>Worcester Polytechnic Institute &emsp; <sup>2</sup>Rochester Institute of Technology

</div>

![teaser](assets/Teaser.png)
## Overview

ARCADE is an evaluation framework that bridges the gap between quantitative benchmarks and visual evaluation of computer vision models. By providing a reusable pipeline and interactive AR tasks, it enables researchers to complement metrics with direct visual inspection.



![Video](assets/teaser.gif)


## Table of Contents

- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Mobile Clients](#mobile-clients)
- [Captured Data](#captured-data)
- [Case Studies](#case-studies)
- [Citation](#citation)

---

## Project Structure

| Path | Description |
|------|-------------|
| `src/server/` | Backend server (Tornado, handlers, workers) |
| `src/IOS_APP/` | iOS client for live capture |
| `src/webUI/` | Web interface |
| `examples/lighting/` | Lighting case study example |
| `examples/docker/` | Docker example for adding containerized models |
| `data/` | Captured sessions |

For a detailed breakdown of server modules—handlers, workers, state, config, and how to extend them. 
>**Detailed breakdown of server modules:** See [README.md](src/server/README.md).


## Installation

### 1. Clone the repository

```bash
git clone https://github.com/cake-lab/ARCADE
cd ARCADE
```

### 2. Create and activate the `Arcade` conda environment

```bash
conda env create -f environment.yml
conda activate Arcade
```

This creates an environment with Python 3.10 and installs PyTorch (CUDA 12.6) plus all server dependencies from `requirements.txt`.



## Quick Start

### Step 1: Start the server

```bash
cd src
python server.py 
```

The server listens on **port 5034** by default.

### Step 2: Serve the web UI

The web UI is static HTML/CSS/JS—no Node.js or build step required. In a **separate terminal**:

```bash
cd src/webUI
python -m http.server 8000
```

Open `http://localhost:8000` (or `http://<your-ip>:8000` on another device). The UI connects to the backend at `http://<server-ip>:5034` for WebSocket, API, and live/replay streams. Note that you need to be on the same network as the server.


## Captured Data
Captured sessions are saved in `data/sessions/`. When you capture a session from the mobile client, the server saves the following under `data/sessions/session_YYYYMMDD_HHMMSS/`:

| File | Description |
|------|-------------|
| `session_config.json` | Camera resolution, intrinsics, virtual object path, scale |
| `frame_00000_rgb.png` | RGB image |
| `frame_00000_depth.npy` | Depth map (float32 numpy) |
| `frame_00000_metadata.json` | AR pose, object position, etc. |
| `frame_00000_mask.png` | Object mask (optional; from client when using object placement) |
| `frame_00000_server_mask.png` | Server-rendered mask (created during replay when using object placement) |

> **Dataset viewer:** The dataset viewer (ScanNet) only works with **Plane** mode (virtual plane at a fixed depth). It does not support Object Placement mode. Use the web UI for object placement evaluation on captured sessions.

---

## Mobile Clients

| Platform | Instructions |
|----------|--------------|
| **iOS** | Build and run the included app. See [src/IOS_APP/README.md](src/IOS_APP/README.md) for build instructions. |
| **Android & cross-platform** | Use [ARFlow](https://github.com/cake-lab/ARFlow) for prebuilt clients and data streaming to the ARCADE server. |

---

## Case Studies

### Depth Case Study

The depth evaluation pipeline is **integrated** into ARCADE. Use the web UI to:

1. Select inference models (ZoeDepth, DepthAnything) via the model selector
2. Capture or replay sessions to compare predicted depth against ground truth
3. View depth colormaps, composites, and metrics in the frame details and dataset viewer

Models live in `src/server/modules/inference/` and are auto-discovered. See [src/server/README.md](src/server/README.md#adding-a-new-inference-model) for adding new depth models.

### Lighting Case Study

For lighting evaluation, use the example under `case_study/lighting`. Follow the README in that directory to run the lighting case study and extend it for your scenarios.

### Adding More Models (Docker)

To add models that run in isolated environments or require different dependencies, use the Docker example in `case_study/lighting/Dockerfile`. The example shows how to:

- Package a model as a containerized service
- Connect it to the ARCADE server
- Register and use it alongside built-in inference models

See [README.md](./src/case_study/README.md) for setup and usage.

---

## Citation

If you use ARCADE in your research, please cite:

```bibtex
@misc{ganj2026arevaluationplaygroundbridging,
      title={AR as an Evaluation Playground: Bridging Metrics and Visual Perception of Computer Vision Models}, 
      author={Ashkan Ganj and Yiqin Zhao and Tian Guo},
      year={2026},
      eprint={2508.04102},
      archivePrefix={arXiv},
      primaryClass={cs.CV},
      url={https://arxiv.org/abs/2508.04102}, 
}
```

---

## License

This project is licensed under the terms of the LICENSE file in this repository.
