# 2025秋《智能机器人概论》期末大作业 - 稀疏重建

将前馈式重建方法与传统 3DGS 优化方法相结合：选用 [Depth Anything 3](https://github.com/ByteDance-Seed/depth-anything-3) 生成深度图、相机位姿、初始点云等信息，将稀疏图片集合转换成 COLMAP 数据集；然后再使用 [SparseGS](https://github.com/ForMyCat/SparseGS) 等方法，迭代优化高斯点云。

## 📁 项目结构

```
robot_2025Fall/
├── README.md                              # project description
├── depth-anything-3/                      # submodule
|   └── ...
├── SparseGS/                              # submodule
|   └── ...
├── patches/                               # patches for submodules
|   └── depth_anything_3.patch             # fix bugs in DA3
├── scripts                                # scripts
|   ├── convert_to_3dgs_format.py          # convert 3DGS output by DA3 for the Gaussian viewer
|   ├── npz2npy.py                         # convert results.npz to per-image .npy depth files
|   └── run_da3_and_organize.py            # rapper script to run `da3 images` and reorganize outputs
└── workspace
    ├── checkpoints/                       # place model weights here
    └── datasets/                          # place images here 
```

## 🛠️ 环境配置

### 1. 基础要求

- Python 3.10
- CUDA 12.8
- 24GB+ GPU 显存（推荐）

### 2. 安装依赖

#### 2.1 克隆项目
```bash
git clone https://github.com/Phrandime/robot_2025Fall.git --recursive
cd robot_2025Fall
```

#### 2.2 应用代码补丁
```bash
git apply ./patches/depth_anything_3.patch
```

#### 2.3 按照 depth-anything-3 要求安装依赖
```bash
cd depth-anything-3
pip install xformers torch\>=2 torchvision
pip install -e . # Basic
pip install --no-build-isolation git+https://github.com/nerfstudio-project/gsplat.git@0b4dddf04cb687367602c01196913cde6a743d70 # for gaussian head
pip install -e ".[app]" # Gradio, python>=3.10
# pip install -e ".[all]" # ALL  # 不执行这一行
```

#### 2.4 安装剩余依赖
```bash
cd ..
pip install -r requirements.txt
```

### 3. 模型下载

参考 [Depth Anything 3](https://github.com/ByteDance-Seed/depth-anything-3) 说明文件下载模型

## 🚀 快速开始

将需要重建的场景组织成如下结构
```
/path/to/scene/
└── images
    ├── image_name1.png
    ├── image_name2.png
    └── ...
```

执行指令
```bash
python3 scripts/run_da3_and_organize.py --dataset-root /path/to/scene --model-dir /path/to/DA3-model --process-res 1024
```
