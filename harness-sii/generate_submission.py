"""
生成打榜提交文件
================

将evaluate_benchmark.py的输出转换为打榜要求的格式：
- group_11.json: 轨迹文件
- group_11.csv: 答案文件（包含answer列）
- group_11.zip: 压缩文件

Usage:
    python generate_submission.py \
        --benchmark-output benchmark_output.jsonl \
        --trajectory-dir trajectories/ \
        --group-number 11
"""

import argparse
import csv
import json
import zipfile
from pathlib import Path
from typing import Any


def load_benchmark_output(path: Path) -> list[dict[str, Any]]:
    """加载benchmark输出文件"""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def load_trajectory(trajectory_path: Path) -> list[dict[str, Any]]:
    """加载单个轨迹文件"""
    steps = []
    if trajectory_path.exists():
        with open(trajectory_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    steps.append(json.loads(line))
    return steps


def generate_group_json(
    records: list[dict[str, Any]],
    trajectory_dir: Path,
    output_path: Path,
):
    """
    生成group_11.json轨迹文件

    格式：每个问题的完整轨迹
    """
    all_trajectories = {}

    for record in records:
        task_id = record.get("task_id", "")
        trajectory_path = record.get("trajectory_path", "")

        if trajectory_path:
            traj_path = Path(trajectory_path)
            if not traj_path.is_absolute():
                traj_path = trajectory_dir / trajectory_path
            steps = load_trajectory(traj_path)
        else:
            steps = []

        all_trajectories[task_id] = {
            "index": record.get("index"),
            "instruction": record.get("instruction", ""),
            "answer": record.get("answer", ""),
            "pred": record.get("pred", ""),
            "steps": steps,
        }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_trajectories, f, ensure_ascii=False, indent=2)

    print(f"Generated {output_path} with {len(all_trajectories)} trajectories")


def generate_group_csv(
    records: list[dict[str, Any]],
    output_path: Path,
):
    """
    生成group_11.csv答案文件

    格式：包含index, problem, image, answer列
    """
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["index", "problem", "image", "answer"])

        for record in records:
            writer.writerow([
                record.get("index", ""),
                record.get("problem", ""),
                record.get("image", ""),
                record.get("pred", ""),  # pred就是Agent的答案
            ])

    print(f"Generated {output_path} with {len(records)} answers")


def generate_zip(
    json_path: Path,
    csv_path: Path,
    zip_path: Path,
):
    """生成group_11.zip压缩文件"""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(json_path, json_path.name)
        zf.write(csv_path, csv_path.name)

    print(f"Generated {zip_path}")


def main():
    parser = argparse.ArgumentParser(description="生成打榜提交文件")
    parser.add_argument(
        "--benchmark-output",
        type=Path,
        required=True,
        help="evaluate_benchmark.py的输出文件（JSONL格式）",
    )
    parser.add_argument(
        "--trajectory-dir",
        type=Path,
        default=Path("trajectories"),
        help="轨迹文件目录",
    )
    parser.add_argument(
        "--group-number",
        type=int,
        default=11,
        help="组号（默认11）",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("submission"),
        help="输出目录",
    )
    args = parser.parse_args()

    # 创建输出目录
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # 加载benchmark输出
    records = load_benchmark_output(args.benchmark_output)
    print(f"Loaded {len(records)} records from {args.benchmark_output}")

    # 生成文件路径
    group_name = f"group_{args.group_number}"
    json_path = args.output_dir / f"{group_name}.json"
    csv_path = args.output_dir / f"{group_name}.csv"
    zip_path = args.output_dir / f"{group_name}.zip"

    # 生成文件
    generate_group_json(records, args.trajectory_dir, json_path)
    generate_group_csv(records, csv_path)
    generate_zip(json_path, csv_path, zip_path)

    print(f"\nSubmission files generated in {args.output_dir}/")
    print(f"  - {group_name}.json (trajectories)")
    print(f"  - {group_name}.csv (answers)")
    print(f"  - {group_name}.zip (submission)")


if __name__ == "__main__":
    main()
