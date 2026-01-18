#!/usr/bin/env python3
"""
Wrapper script to run `da3 images` and reorganize outputs for a dataset.

Usage example:
  python scripts/run_da3_and_organize.py \
    --dataset-root workspace/datasets/lectern \
    --model-dir workspace/checkpoints/DA3NESTED-GIANT-LARGE-1.1 \
    --process-res 1024

The script will:
 - run `da3 images <images_dir> --model-dir <model_dir> --export-format glb-colmap-npz-gs_ply --export-dir <output_dir> --process-res <res>`
 - move COLMAP binary files into `<dataset_root>/sparse/0/`
 - run `scripts/npz2npy.py` to generate per-image `.npy` depth files under `<dataset_root>/depths/`
 - run `scripts/convert_to_3dgs_format.py --dataset_path <dataset_root>` to create 3DGS viewer files and copy the first found .ply into `output/gs_ply/point_cloud/point_cloud.ply`
"""

import argparse
import subprocess
import sys
from pathlib import Path
import shutil
import os


def run_command(cmd, check=True, env=None):
    print("\n> " + " ".join(cmd))
    res = subprocess.run(cmd, stdout=sys.stdout, stderr=sys.stderr, env=env)
    if check and res.returncode != 0:
        raise SystemExit(f"Command failed: {' '.join(cmd)} (exit {res.returncode})")
    return res.returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset-root', required=True, help='Path to dataset root (contains images/ )')
    parser.add_argument('--model-dir', required=True, help='Path to model directory for --model-dir')
    parser.add_argument('--process-res', type=int, default=1024, help='process-res passed to da3')
    parser.add_argument('--env', type=str, default='py311_da3', help='Conda env name to run da3 (uses `conda run -n ENV da3 ...`)')
    parser.add_argument('--skip-da3', action='store_true', help='Skip running da3 (useful for testing organization only)')
    args = parser.parse_args()

    dataset_root = Path(args.dataset_root)
    images_dir = dataset_root / 'images'
    output_dir = dataset_root / 'output'

    if not images_dir.exists():
        raise SystemExit(f'Images dir not found: {images_dir}')

    # 1) Run da3
    if not args.skip_da3:
        # Try running `da3` directly; if not available, try `conda run -n <env> da3 ...`
        da3_cmd = [
            'da3', 'images', str(images_dir),
            '--model-dir', str(args.model_dir),
            '--export-format', 'glb-colmap-npz-gs_ply',
            '--export-dir', str(output_dir),
            '--process-res', str(args.process_res)
        ]

        try:
            run_command(da3_cmd)
        except SystemExit:
            print('`da3` 调用失败，尝试使用 `conda run -n {}`'.format(args.env))
            run_command(['conda', 'run', '-n', args.env] + da3_cmd)

    # 2) Move COLMAP bin files into dataset_root/sparse/0/
    sparse_dir = dataset_root / 'sparse' / '0'
    sparse_dir.mkdir(parents=True, exist_ok=True)

    colmap_bins = ['cameras.bin', 'images.bin', 'points3D.bin', 'frames.bin', 'rigs.bin']
    moved = []
    for b in colmap_bins:
        src = output_dir / b
        if src.exists():
            dst = sparse_dir / b
            shutil.move(str(src), str(dst))
            moved.append(b)

    if moved:
        print(f'✅ 已移动 COLMAP 文件到 {sparse_dir}: {moved}')
    else:
        print('⚠️ 未发现 COLMAP 二进制文件可移动')

    # 3) Convert npz -> npy depths
    # Expect NPZ at output/exports/npz/results.npz (matches da3 export layout)
    npz_path = output_dir / 'exports' / 'npz' / 'results.npz'
    depths_dir = dataset_root / 'depths'
    depths_dir.mkdir(parents=True, exist_ok=True)

    if npz_path.exists():
        run_command([sys.executable, 'scripts/npz2npy.py', '--npz-path', str(npz_path), '--images-dir', str(images_dir), '--depths-dir', str(depths_dir)])
    else:
        print(f'⚠️ 未找到 {npz_path}，跳过 npz->npy 转换')

    # 4) Convert COLMAP -> 3DGS format and copy/rename first ply to point_cloud/point_cloud.ply
    run_command([sys.executable, 'scripts/convert_to_3dgs_format.py', '--dataset_path', str(dataset_root)])

    # Ensure final gs_ply/point_cloud/point_cloud.ply exists; if not, try to move first ply
    gs_root = output_dir / 'gs_ply'
    point_cloud_dir = gs_root / 'point_cloud'
    point_cloud_dir.mkdir(parents=True, exist_ok=True)

    final_ply = point_cloud_dir / 'point_cloud.ply'
    if final_ply.exists():
        print(f'✅ 最终点云存在: {final_ply}')
    else:
        # try to find any ply in gs_root
        candidates = sorted(list(gs_root.glob('*.ply')))
        if candidates:
            src = candidates[0]
            shutil.move(str(src), str(final_ply))
            print(f'✅ 已移动 {src.name} -> {final_ply}')
        else:
            print('⚠️ 未找到 .ply 文件用于移动到 point_cloud/point_cloud.ply')

    print('\n🚀 一键处理完成！')


if __name__ == '__main__':
    main()
