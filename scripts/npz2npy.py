import argparse
import numpy as np
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='Convert results.npz to per-image .npy depth files')
    parser.add_argument('--npz-path', type=str, required=True, help='Path to results.npz (exported by da3)')
    parser.add_argument('--images-dir', type=str, required=True, help='Directory containing input images')
    parser.add_argument('--depths-dir', type=str, required=True, help='Output directory for .npy depth files')

    args = parser.parse_args()

    npz_path = Path(args.npz_path)
    images_dir = Path(args.images_dir)
    depths_dir = Path(args.depths_dir)

    if not npz_path.exists():
        print(f'❌ NPZ 文件不存在: {npz_path}')
        return

    # 加载 npz 文件
    data = np.load(str(npz_path))

    print('NPZ 文件内容:')
    for key in data.files:
        print(f'  {key}: {data[key].shape}')

    # 获取图片文件名列表（按字母顺序，尽量与COLMAP顺序一致）
    image_files = sorted([f for f in os.listdir(str(images_dir)) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    print(f'\n图片数量: {len(image_files)}')
    if 'depth' not in data.files:
        print('❌ NPZ 中未包含 depth 字段')
        return

    print(f'深度图数量: {data["depth"].shape[0]}')

    # 创建输出目录
    depths_dir.mkdir(parents=True, exist_ok=True)

    # 保存每张图片的深度为单独的 .npy 文件
    depth_all = data['depth']
    for i, img_name in enumerate(image_files):
        # 如果depth数量不匹配，停止
        if i >= depth_all.shape[0]:
            print(f'⚠️ 深度数量少于图片数量，停止在索引 {i}')
            break
        base_name = os.path.splitext(img_name)[0]
        depth_path = depths_dir / f'{base_name}.npy'
        np.save(str(depth_path), depth_all[i])
        print(f'保存: {depth_path} (shape: {depth_all[i].shape})')

    print(f'\n✅ 完成！共生成 {min(len(image_files), depth_all.shape[0])} 个深度文件')


if __name__ == '__main__':
    main()