#!/usr/bin/env python3
"""
Road Hazard Detection Dataset Preparation Script
=================================================
Prepares and splits dataset for YOLOv8 road hazard detection model.
Classes:
  0: pothole
  1: crack
  2: animal

Features:
- Deterministic 70% train / 20% val / 10% test splits.
- Automatic generation of YOLO `data.yaml`.
- Synthetic sample dataset generator for testing/prototyping without downloading gigabytes.
- Dataset merger to combine multiple raw datasets or custom edge robot captures.
"""

import os
import sys
import yaml
import random
import shutil
import argparse
from pathlib import Path
from typing import List, Tuple, Dict
from PIL import Image, ImageDraw

CLASS_NAMES = ["pothole", "crack", "animal"]
CLASS_MAP = {name: i for i, name in enumerate(CLASS_NAMES)}

def generate_synthetic_sample(img_path: Path, label_path: Path, img_size: Tuple[int, int] = (640, 640)):
    """Generates a synthetic road surface image with random hazards and matching YOLO annotations."""
    w, h = img_size
    # Asphalt background with slight noise/shade variation
    bg_color = (
        random.randint(55, 75),
        random.randint(55, 75),
        random.randint(58, 78)
    )
    img = Image.new("RGB", (w, h), bg_color)
    draw = ImageDraw.Draw(img)

    # Road lane markings or texture
    if random.random() > 0.4:
        lane_x = random.randint(50, w - 50)
        draw.line([(lane_x, 0), (lane_x, h)], fill=(200, 200, 180), width=random.randint(4, 8))

    # Add 1 to 3 hazards
    annotations = []
    num_hazards = random.randint(1, 3)

    for _ in range(num_hazards):
        hazard_class_id = random.randint(0, 2)
        box_w = random.randint(60, 180)
        box_h = random.randint(40, 140)
        x1 = random.randint(20, w - box_w - 20)
        y1 = random.randint(20, h - box_h - 20)
        x2 = x1 + box_w
        y2 = y1 + box_h

        if hazard_class_id == 0:  # Pothole: dark eroded ellipse
            draw.ellipse([x1, y1, x2, y2], fill=(25, 25, 25), outline=(40, 40, 40), width=3)
            # Inner texture
            draw.ellipse([x1 + 10, y1 + 8, x2 - 10, y2 - 8], fill=(15, 15, 15))
        elif hazard_class_id == 1:  # Crack: dark jagged polygon / lines
            points = [(x1, (y1 + y2) // 2)]
            curr_x, curr_y = points[0]
            while curr_x < x2:
                curr_x += random.randint(15, 35)
                curr_y += random.randint(-15, 15)
                curr_y = max(y1, min(y2, curr_y))
                points.append((curr_x, curr_y))
            draw.line(points, fill=(20, 20, 20), width=random.randint(3, 5))
        else:  # Animal: silhouette blob
            draw.ellipse([x1, y1 + box_h // 3, x2, y2], fill=(139, 90, 43))
            draw.ellipse([x1 + box_w // 4, y1, x1 + 3 * box_w // 4, y1 + box_h // 2], fill=(110, 70, 30))

        # Normalized YOLO format: class_id center_x center_y norm_w norm_h
        cx = (x1 + x2) / (2.0 * w)
        cy = (y1 + y2) / (2.0 * h)
        nw = box_w / float(w)
        nh = box_h / float(h)
        annotations.append(f"{hazard_class_id} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")

    img.save(img_path, "JPEG", quality=90)
    with open(label_path, "w") as f:
        f.write("\n".join(annotations) + "\n")

def create_synthetic_dataset(output_dir: Path, total_count: int = 60, seed: int = 42):
    """Generates synthetic raw dataset for testing YOLO training pipeline."""
    random.seed(seed)
    raw_images = output_dir / "raw" / "images"
    raw_labels = output_dir / "raw" / "labels"
    raw_images.mkdir(parents=True, exist_ok=True)
    raw_labels.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Generating {total_count} synthetic road hazard samples in {output_dir / 'raw'}...")
    for i in range(total_count):
        filename = f"sample_{i:04d}"
        img_p = raw_images / f"{filename}.jpg"
        lbl_p = raw_labels / f"{filename}.txt"
        generate_synthetic_sample(img_p, lbl_p)
    print(f"[SUCCESS] Synthetic dataset generated ({total_count} images).")

def split_dataset(
    raw_dir: Path,
    output_dir: Path,
    train_ratio: float = 0.7,
    val_ratio: float = 0.2,
    test_ratio: float = 0.1,
    seed: int = 42
) -> Dict[str, int]:
    """Splits dataset into train, val, and test splits and creates YOLO directory structure."""
    random.seed(seed)
    assert abs((train_ratio + val_ratio + test_ratio) - 1.0) < 1e-5, "Split ratios must sum to 1.0"

    images_dir = raw_dir / "images"
    labels_dir = raw_dir / "labels"

    if not images_dir.exists():
        raise FileNotFoundError(f"Images directory not found: {images_dir}")

    # Gather paired samples
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp"}
    all_images = [f for f in images_dir.iterdir() if f.suffix.lower() in image_extensions]
    paired_samples = []

    for img_path in all_images:
        lbl_path = labels_dir / f"{img_path.stem}.txt"
        if lbl_path.exists():
            paired_samples.append((img_path, lbl_path))

    if not paired_samples:
        raise ValueError(f"No valid image-label pairs found in {raw_dir}")

    random.shuffle(paired_samples)
    n = len(paired_samples)
    train_end = int(n * train_ratio)
    val_end = train_end + int(n * val_ratio)

    splits = {
        "train": paired_samples[:train_end],
        "val": paired_samples[train_end:val_end],
        "test": paired_samples[val_end:]
    }

    counts = {}
    for split_name, samples in splits.items():
        split_img_dir = output_dir / split_name / "images"
        split_lbl_dir = output_dir / split_name / "labels"
        split_img_dir.mkdir(parents=True, exist_ok=True)
        split_lbl_dir.mkdir(parents=True, exist_ok=True)

        for src_img, src_lbl in samples:
            shutil.copy2(src_img, split_img_dir / src_img.name)
            shutil.copy2(src_lbl, split_lbl_dir / src_lbl.name)
        counts[split_name] = len(samples)

    # Generate YOLO data.yaml
    data_yaml_path = output_dir / "data.yaml"
    data_config = {
        "path": str(output_dir.resolve()),
        "train": "train/images",
        "val": "val/images",
        "test": "test/images",
        "names": {i: name for i, name in enumerate(CLASS_NAMES)},
        "nc": len(CLASS_NAMES)
    }

    with open(data_yaml_path, "w") as f:
        yaml.dump(data_config, f, sort_keys=False)

    print(f"[SUCCESS] Dataset split complete:")
    print(f"  Train: {counts['train']} images")
    print(f"  Val:   {counts['val']} images")
    print(f"  Test:  {counts['test']} images")
    print(f"  data.yaml written to: {data_yaml_path}")
    return counts

def merge_datasets(source_dirs: List[Path], target_dir: Path):
    """Merges multiple YOLO-formatted dataset folders into a single raw folder."""
    target_images = target_dir / "images"
    target_labels = target_dir / "labels"
    target_images.mkdir(parents=True, exist_ok=True)
    target_labels.mkdir(parents=True, exist_ok=True)

    total_merged = 0
    for src_idx, src_dir in enumerate(source_dirs):
        src_img_dir = src_dir / "images"
        src_lbl_dir = src_dir / "labels"
        if not src_img_dir.exists():
            continue
        for img_path in src_img_dir.iterdir():
            if img_path.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                lbl_path = src_lbl_dir / f"{img_path.stem}.txt"
                if lbl_path.exists():
                    new_name = f"merged_{src_idx}_{img_path.stem}"
                    shutil.copy2(img_path, target_images / f"{new_name}{img_path.suffix}")
                    shutil.copy2(lbl_path, target_labels / f"{new_name}.txt")
                    total_merged += 1
    print(f"[SUCCESS] Merged {total_merged} items into {target_dir}")

def parse_args():
    parser = argparse.ArgumentParser(description="Prepare and split YOLOv8 road hazard dataset.")
    parser.add_argument("--raw-dir", type=str, default="ml/dataset/raw", help="Directory with raw images and labels")
    parser.add_argument("--output-dir", type=str, default="ml/dataset", help="Output directory for train/val/test splits")
    parser.add_argument("--train-ratio", type=float, default=0.7, help="Proportion for training set (default: 0.7)")
    parser.add_argument("--val-ratio", type=float, default=0.2, help="Proportion for validation set (default: 0.2)")
    parser.add_argument("--test-ratio", type=float, default=0.1, help="Proportion for test set (default: 0.1)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--generate-synthetic", action="store_true", help="Generate synthetic dataset for testing")
    parser.add_argument("--synthetic-count", type=int, default=50, help="Number of synthetic samples to create")
    return parser.parse_args()

def main():
    args = parse_args()
    out_path = Path(args.output_dir)

    if args.generate_synthetic:
        create_synthetic_dataset(out_path, total_count=args.synthetic_count, seed=args.seed)
        raw_path = out_path / "raw"
    else:
        raw_path = Path(args.raw_dir)

    split_dataset(
        raw_dir=raw_path,
        output_dir=out_path,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        seed=args.seed
    )

if __name__ == "__main__":
    main()
