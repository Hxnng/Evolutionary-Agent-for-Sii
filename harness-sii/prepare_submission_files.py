"""Prepare course submission artifacts from existing harness runs.

The script copies prediction JSONL files into the required result filenames,
merges per-task trajectories into one JSONL per dataset/mode, and writes the
leaderboard CSV/JSON reported in the project README.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_SCORE_ROWS = [
    {"method": "baseline", "SimpleVQA": 0.2121, "2wiki": 0.91, "leaderboard": 0.01},
    {"method": "Skill", "SimpleVQA": 0.4286, "2wiki": 0.96, "leaderboard": 0.26},
    {"method": "SFT", "SimpleVQA": 0.394, "2wiki": 0.72, "leaderboard": 0.36},
]


RUNS = [
    {
        "dataset_label": "SimpleVQA",
        "prefix": "",
        "prediction": Path("runs/no_reflection/simplevqa/predictions.jsonl"),
        "trajectory_dir": Path("runs/no_reflection/simplevqa/trajectories"),
        "dataset": Path("data_test/SimpleVQA.jsonl"),
    },
    {
        "dataset_label": "2Wiki",
        "prefix": "",
        "prediction": Path("runs/no_reflection/2wiki/predictions.jsonl"),
        "trajectory_dir": Path("runs/no_reflection/2wiki/trajectories"),
        "dataset": Path("data_test/2wiki.jsonl"),
    },
    {
        "dataset_label": "SimpleVQA",
        "prefix": "evo_",
        "prediction": Path("runs/with_skill_reflection/simplevqa/predictions.jsonl"),
        "trajectory_dir": Path("runs/with_skill_reflection/simplevqa/trajectories"),
        "dataset": Path("data_test/SimpleVQA.jsonl"),
    },
    {
        "dataset_label": "2Wiki",
        "prefix": "evo_",
        "prediction": Path("runs/with_skill_reflection/2wiki/predictions.jsonl"),
        "trajectory_dir": Path("runs/with_skill_reflection/2wiki/trajectories"),
        "dataset": Path("data_test/2wiki.jsonl"),
    },
]


def _index_key(record: dict[str, Any]) -> tuple[int, Any]:
    value = record.get("index", 0)
    try:
        return (0, int(value))
    except (TypeError, ValueError):
        return (1, str(value))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _instruction_from_trajectory(trajectory_dir: Path, dataset_label: str, index: int) -> str:
    stem = "2wiki" if dataset_label == "2Wiki" else dataset_label.lower()
    path = trajectory_dir / f"{stem}_{index}.jsonl"
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        if entry.get("role") == "user":
            content = entry.get("content")
            if isinstance(content, str):
                return content
            return json.dumps(content, ensure_ascii=False)
    return ""


def _complete_missing_rows(
    rows: list[dict[str, Any]],
    dataset_path: Path,
    trajectory_dir: Path,
    dataset_label: str,
) -> list[dict[str, Any]]:
    if dataset_label != "2Wiki" or not dataset_path.exists():
        return rows
    by_index = {int(row["index"]): row for row in rows if str(row.get("index", "")).isdigit()}
    dataset_rows = _read_jsonl(dataset_path)
    for index, source_row in enumerate(dataset_rows):
        if index in by_index:
            continue
        instruction = _instruction_from_trajectory(trajectory_dir, dataset_label, index)
        if not instruction:
            instruction = str(source_row.get("question") or source_row.get("instruction") or "")
        by_index[index] = {
            "index": index,
            "instruction": instruction,
            "image": str(source_row.get("image") or ""),
            "answer": str(source_row.get("answer") or ""),
            "pred": "",
        }
    return list(by_index.values())


def _write_sorted_predictions(
    source: Path,
    target: Path,
    *,
    dataset_path: Path,
    trajectory_dir: Path,
    dataset_label: str,
) -> int:
    rows = _complete_missing_rows(_read_jsonl(source), dataset_path, trajectory_dir, dataset_label)
    rows = sorted(rows, key=_index_key)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as out:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(rows)


def _natural_key(path: Path) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", path.name)]


def _merge_trajectories(source_dir: Path, target: Path) -> int:
    count = 0
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as out:
        for path in sorted(source_dir.glob("*.jsonl"), key=_natural_key):
            with path.open("r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.strip():
                        out.write(line if line.endswith("\n") else line + "\n")
                        count += 1
    return count


def _write_leaderboard(output_dir: Path) -> None:
    csv_path = output_dir / "leaderboard_results.csv"
    json_path = output_dir / "leaderboard_results.json"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["method", "SimpleVQA", "2wiki", "leaderboard"])
        writer.writeheader()
        writer.writerows(DEFAULT_SCORE_ROWS)
    json_path.write_text(json.dumps(DEFAULT_SCORE_ROWS, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate SII submission JSONL/CSV/JSON files.")
    parser.add_argument("--group-id", default="11", help="Group number used in required filenames.")
    parser.add_argument("--output-dir", type=Path, default=Path("submissions/group_11"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parent
    output_dir = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, Any]] = []
    for run in RUNS:
        base_name = f"{run['prefix']}{run['dataset_label']}_group_{args.group_id}"
        prediction = root / run["prediction"]
        trajectory_dir = root / run["trajectory_dir"]
        result_target = output_dir / f"{base_name}_result.jsonl"
        trajectory_target = output_dir / f"{base_name}_trajectory.jsonl"
        result_rows = _write_sorted_predictions(
            prediction,
            result_target,
            dataset_path=root / run["dataset"],
            trajectory_dir=trajectory_dir,
            dataset_label=run["dataset_label"],
        )
        trajectory_rows = _merge_trajectories(trajectory_dir, trajectory_target)
        manifest.append(
            {
                "dataset": run["dataset_label"],
                "evolved": bool(run["prefix"]),
                "result_file": str(result_target),
                "trajectory_file": str(trajectory_target),
                "result_rows": result_rows,
                "trajectory_rows": trajectory_rows,
            }
        )

    _write_leaderboard(output_dir)
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output_dir": str(output_dir), "files": manifest}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
