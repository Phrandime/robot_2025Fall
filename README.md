# 2025秋《智能机器人概论》期末大作业 - 稀疏重建

将前馈式重建方法与传统 3DGS 优化方法相结合：选用 [Depth Anything 3](https://github.com/ByteDance-Seed/depth-anything-3) 生成深度图、相机位姿、初始点云等信息，将稀疏图片集合转换成 COLMAP 数据集；然后再使用 [SparseGS](https://github.com/ForMyCat/SparseGS) 等方法，迭代优化高斯点云。

## 📁 项目结构

```
robot_2025Fall/
├── README.md                             # project description
├── depth-anything-3/                     # submodule
|   └── ...
├── SparseGS/                             # submodule
|   └── ...
├── patches/                              # patches for submodules
|   └── depth_anything_3.patch            # fix bugs in DA3
├── scripts                               # scripts
|   ├── convert_to_3dgs_format.py         # convert 3DGS output by DA3 for the Gaussian viewer
|   ├── npz2npy.py                        # convert results.npz to per-image .npy depth files
|   └── run_da3_and_organize.py           # rapper script to run `da3 images` and reorganize outputs
└── workspace
    ├── checkpoints/                      # place model weights here
    └── datasets/                         # place images here 
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
cd depth-anything-3 && git apply ./patches/depth_anything_3.patch
cd ../SparseGS && git apply --whitespace=fix --reject ../patches/sparsegs.patch
```

#### 2.3 按照 depth-anything-3 要求安装依赖
```bash
cd ../depth-anything-3
pip install xformers torch\>=2 torchvision
pip install -e . # Basic
pip install --no-build-isolation git+https://github.com/nerfstudio-project/gsplat.git@0b4dddf04cb687367602c01196913cde6a743d70 # for gaussian head
pip install -e ".[app]" # Gradio, python>=3.10
# pip install -e ".[all]" # ALL  # 不执行这一行
```

#### 2.4 安装 SparseGS 剩余依赖
```bash
cd ..
pip install -r requirements.txt
git clone https://github.com/g-truc/glm.git SparseGS/submodules/diff-gaussian-rasterization-softmax/third_party/glm
pip install \
    SparseGS/submodules/diff-gaussian-rasterization-softmax \
    SparseGS/submodules/simple-knn \
    --no-build-isolation
```

### 3. 模型下载

参考 [Depth Anything 3](https://github.com/ByteDance-Seed/depth-anything-3) 说明文件下载模型

SparseGS 需要用到 Stable Diffusion 模型，可以下载 [stable-diffusion-2-1-base](https://www.modelscope.cn/models/stabilityai/stable-diffusion-2-1-base)，也可以在运行代码时自动下载

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
python scripts/run_da3_and_organize.py \
    --dataset-root /path/to/scene \
    --model-dir /path/to/DA3-model \
    --process-res 1024
```

生成 DA3 预测得到的 COLMAP 数据集、高斯点云等文件

然后使用 SparseGS 进行重建

```bash
cd SparseGS
python train.py \
    --source_path /path/to/colmap/dataset \
    --model_path /output/path \
    --beta 5.0 --lambda_pearson 0.05 --lambda_local_pearson 0.15 --box_p 128 --p_corr 0.5 \
    --lambda_diffusion 0.001 --SDS_freq 0.1 --step_ratio 0.99 --lambda_reg 0.1 \
    --iterations 10000 \
    -r 4 \
    --hf_key /path/to/stable-diffusion-model  # 若不指定，则自动下载模型
```

也可以指定初始高斯点云

```bash
python train.py \
    --source_path /path/to/colmap/dataset \
    --model_path /output/path \
    --init_ply_path /path/to/point_cloud.ply \
    --lambda_diffusion 0.001 --SDS_freq 0.1 --step_ratio 0.99 --lambda_reg 0.1 \
    --iterations 3000 \
    -r 4 \
    --hf_key /path/to/stable-diffusion-model
```
