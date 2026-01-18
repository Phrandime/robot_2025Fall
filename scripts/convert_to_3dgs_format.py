#!/usr/bin/env python3
"""
将COLMAP格式的相机参数转换为3DGS查看器所需的cameras.json和cfg_args格式
适配pycolmap 3.13.0 API
"""

import pycolmap
import json
import numpy as np
from pathlib import Path
import argparse


def quaternion_to_rotation_matrix(qw, qx, qy, qz):
    """将四元数转换为旋转矩阵"""
    R = np.array([
        [1 - 2*qy*qy - 2*qz*qz, 2*qx*qy - 2*qz*qw, 2*qx*qz + 2*qy*qw],
        [2*qx*qy + 2*qz*qw, 1 - 2*qx*qx - 2*qz*qz, 2*qy*qz - 2*qx*qw],
        [2*qx*qz - 2*qy*qw, 2*qy*qz + 2*qx*qw, 1 - 2*qx*qx - 2*qy*qy]
    ])
    return R


def convert_colmap_to_cameras_json(sparse_path, output_path):
    """
    从COLMAP sparse重建结果转换为cameras.json格式
    
    Args:
        sparse_path: COLMAP sparse目录路径 (包含cameras.bin, images.bin等)
        output_path: 输出cameras.json的路径
    """
    reconstruction = pycolmap.Reconstruction(sparse_path)
    
    cameras_list = []
    
    # 遍历所有图像
    for image_id, image in reconstruction.images.items():
        # 获取相机内参
        camera = reconstruction.cameras[image.camera_id]
        
        # pycolmap 3.13.0 API:
        # cam_from_world() 是方法，返回世界到相机的变换 (Rigid3d对象)
        # projection_center() 返回相机中心在世界坐标系中的位置
        cam_from_world = image.cam_from_world()
        R_w2c = cam_from_world.rotation.matrix()  # 世界到相机的旋转矩阵
        
        # 获取相机中心位置 (已经在世界坐标系中)
        camera_center = image.projection_center()
        
        # 3DGS需要相机到世界的旋转 (C2W = R^T)
        rotation_c2w = R_w2c.T
        
        # 获取相机参数
        # pycolmap 3.13.0 中，camera.model 是 CameraModelId 枚举类型
        model_name = str(camera.model).split('.')[-1]  # 获取模型名称
        
        if "PINHOLE" in model_name:
            # PINHOLE: params = [fx, fy, cx, cy]
            fx = camera.params[0]
            fy = camera.params[1]
        elif "SIMPLE_PINHOLE" in model_name:
            # SIMPLE_PINHOLE: params = [f, cx, cy]
            fx = fy = camera.params[0]
        elif "RADIAL" in model_name or "SIMPLE_RADIAL" in model_name:
            # RADIAL/SIMPLE_RADIAL: params = [f, cx, cy, k1, k2]
            fx = fy = camera.params[0]
        else:
            # 其他相机模型，尝试使用focal_length方法
            fx = camera.focal_length_x if hasattr(camera, 'focal_length_x') else camera.params[0]
            fy = camera.focal_length_y if hasattr(camera, 'focal_length_y') else (camera.params[1] if len(camera.params) > 1 else fx)
        
        camera_info = {
            "id": len(cameras_list),  # 使用连续的ID
            "img_name": image.name,
            "width": camera.width,
            "height": camera.height,
            "position": camera_center.tolist(),
            "rotation": rotation_c2w.tolist(),
            "fy": float(fy),
            "fx": float(fx)
        }
        
        cameras_list.append(camera_info)
    
    # 按图像名称排序
    cameras_list.sort(key=lambda x: x["img_name"])
    
    # 重新分配连续的ID
    for i, cam in enumerate(cameras_list):
        cam["id"] = i
    
    # 保存为JSON
    with open(output_path, 'w') as f:
        json.dump(cameras_list, f, indent=2)
    
    print(f"✅ 已生成 cameras.json，包含 {len(cameras_list)} 个相机视角")
    return cameras_list


def create_cfg_args(source_path, model_path, output_path):
    """
    创建cfg_args文件（使用3DGS查看器兼容的参数）
    
    Args:
        source_path: 数据集源路径
        model_path: 模型输出路径
        output_path: cfg_args输出路径
    """
    cfg_content = f"""Namespace(sh_degree=0, source_path='{source_path}', model_path='{model_path}', images='images', resolution=-1, white_background=False, data_device='cuda', no_load_depth=False, eval=False, lambda_local_pearson=0.15, lambda_pearson=0.05, box_p=128, p_corr=0.5, prune_exp=7.5, prune_perc=0.98, densify_lag=1000000, power_thresh=-4.0, densify_period=5000, step_ratio=0.95, lambda_diffusion=0.0, SDS_freq=0.1, lambda_reg=0.1, warp_reg_start_itr=4999)"""
    
    with open(output_path, 'w') as f:
        f.write(cfg_content)
    
    print(f"✅ 已生成 cfg_args")


def main():
    parser = argparse.ArgumentParser(description="转换COLMAP格式为3DGS查看器所需格式")
    parser.add_argument("--dataset_path", type=str, required=True,
                      help="数据集路径 (包含sparse/, images/等目录)")
    parser.add_argument("--sparse_dir", type=str, default="sparse/0",
                      help="COLMAP sparse重建目录 (相对于dataset_path)")
    parser.add_argument("--output_dir", type=str, default=None,
                      help="输出目录 (默认为 dataset_path/output/gs_ply)")
    
    args = parser.parse_args()
    
    dataset_path = Path(args.dataset_path)
    sparse_path = dataset_path / args.sparse_dir
    
    # 确定输出目录
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = dataset_path / "output" / "gs_ply"
    
    # 创建输出目录和point_cloud子目录
    output_dir.mkdir(parents=True, exist_ok=True)
    point_cloud_dir = output_dir / "point_cloud"
    point_cloud_dir.mkdir(exist_ok=True)
    
    if not sparse_path.exists():
        print(f"❌ 错误: sparse目录不存在: {sparse_path}")
        return
    
    # 检查是否有必要的COLMAP文件
    required_files = ["cameras.bin", "images.bin"]
    missing_files = [f for f in required_files if not (sparse_path / f).exists()]
    if missing_files:
        print(f"❌ 错误: 缺少COLMAP文件: {missing_files}")
        return
    
    print(f"📂 数据集路径: {dataset_path}")
    print(f"📂 Sparse路径: {sparse_path}")
    print(f"📂 输出目录: {output_dir}")
    print("-" * 60)
    
    # 转换cameras.json
    cameras_json_path = output_dir / "cameras.json"
    convert_colmap_to_cameras_json(str(sparse_path), str(cameras_json_path))
    
    # 创建cfg_args
    cfg_args_path = output_dir / "cfg_args"
    model_path = str(output_dir.absolute())
    create_cfg_args(
        source_path=str(dataset_path.absolute()),
        model_path=model_path,
        output_path=str(cfg_args_path)
    )
    
    import shutil
    # 在 output/gs_ply 根目录查找 ply 文件
    search_root = dataset_path / "output" / "gs_ply"
    if search_root.exists():
        ply_candidates = sorted([p for p in search_root.glob('*.ply')])
        if ply_candidates:
            src = ply_candidates[0]
            dst = point_cloud_dir / 'point_cloud.ply'
            try:
                shutil.move(src, dst)
                print(f"✅ 已移动点云文件 {src.name} 到 {dst}")
            except Exception as e:
                print(f"⚠️ 移动点云失败: {e}")
        else:
            print(f"⚠️ 未在 {search_root} 发现 .ply 点云文件")
    
    # 检查是否已有点云文件
    existing_ply = list(point_cloud_dir.glob("*.ply"))
    if existing_ply:
        print(f"✅ 发现点云文件: {', '.join([p.name for p in existing_ply])}")
    
    print("-" * 60)
    print("✅ 转换完成！")
    print(f"📄 cameras.json: {cameras_json_path}")
    print(f"📄 cfg_args: {cfg_args_path}")
    print(f"\n📂 3DGS查看器文件结构已准备就绪:")
    print(f"   {output_dir}/")
    print(f"   ├── cameras.json")
    print(f"   ├── cfg_args")
    print(f"   └── point_cloud/")
    print(f"       └── point_cloud.ply")
    print("\n现在你可以使用3DGS查看器查看高斯点云了！")
    print(f"\n命令示例:")
    print(f"   ./SIBR_gaussianViewer_app -m {output_dir.absolute()}")


if __name__ == "__main__":
    main()
