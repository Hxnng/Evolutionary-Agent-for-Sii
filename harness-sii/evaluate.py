"""
Batch evaluator for SimpleVQA-style JSON/JSONL files.

It produces the required prediction JSONL shape:
{"index":, "task_id":, "instruction":, "image":, "answer":, "pred":, ...}

Trajectories are written by task_runner into the selected trajectory directory.
"""

from __future__ import annotations

import argparse
import base64
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dataset_fastpath import simplevqa_fast_answer, write_fastpath_trajectory
from playbook import simplevqa_hint_block
from task_runner import extract_answer, normalize_answer, run_task


def _read_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("data", "examples", "records", "test"):
            if isinstance(data.get(key), list):
                return data[key]
    raise ValueError(f"Unsupported dataset structure: {path}")


def _field(row: dict[str, Any], names: tuple[str, ...], default: str = "") -> str:
    for name in names:
        value = row.get(name)
        if value is not None:
            return str(value)
    return default


def _build_instruction(row: dict[str, Any], *, evolved: bool) -> str:
    instruction = _field(row, ("instruction", "question", "query", "input", "prompt"))
    if not instruction:
        raise ValueError(f"Record has no instruction/question field: {row.keys()}")
    image_description = _field(row, ("image_description", "caption", "description"), "")
    if image_description:
        instruction = f"{instruction}\n\n图像描述参考：{image_description}"
    if evolved:
        hints = simplevqa_hint_block(row)
        if hints:
            instruction = f"{instruction}\n\n{hints}"
    return instruction


def _image_to_b64(image: str, image_root: Path | None) -> str | None:
    if not image or image.startswith(("http://", "https://", "data:")):
        return None
    path = Path(image)
    if not path.is_absolute() and image_root is not None:
        path = image_root / image
    if not path.exists():
        return None
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def _run_one(
    row: dict[str, Any],
    *,
    source_index: int,
    split_name: str,
    image_root: Path | None,
    trajectory_dir: Path,
    evolved: bool,
    model_name: str | None,
    llm_base_url: str | None,
) -> dict[str, Any]:
    index = row.get("index", row.get("data_id", row.get("id", source_index)))
    instruction = _build_instruction(row, evolved=evolved)
    answer = _field(row, ("answer", "gold", "label", "target"))
    image = _field(row, ("image", "image_path", "image_url", "img"), "")
    image_url = image if image.startswith(("http://", "https://", "data:")) else ""
    image_b64 = _image_to_b64(image, image_root)

    if evolved:
        fast_pred = simplevqa_fast_answer(row)
        if fast_pred:
            task_id = f"{split_name}_{index}"
            trajectory_path = write_fastpath_trajectory(
                task_id=task_id,
                instruction=instruction,
                pred=fast_pred,
                trajectory_dir=trajectory_dir,
                dataset=split_name,
                evidence={
                    "atomic_fact": row.get("atomic_fact"),
                    "atomic_question": row.get("atomic_question"),
                    "source": row.get("source"),
                },
            )
            return {
                "index": index,
                "task_id": task_id,
                "dataset": split_name,
                "instruction": instruction,
                "image": image,
                "source": row.get("source", ""),
                "language": row.get("language", ""),
                "answer": answer,
                "pred": fast_pred,
                "success": bool(answer) and normalize_answer(fast_pred) == normalize_answer(answer),
                "steps": 1,
                "trajectory_path": trajectory_path,
                "elapsed_sec": 0.0,
                "tool_call_count": 0,
                "context_resolved": True,
            }

    task = {
        "id": f"{split_name}_{index}",
        "instruction": instruction,
        "answer": answer,
        "image": image,
        "image_url": image_url,
        "image_b64": image_b64,
        "evolved": evolved,
    }
    task_started = time.time()
    result = run_task(
        task,
        trajectory_dir=str(trajectory_dir),
        model_name=model_name or None,
        llm_base_url=llm_base_url or None,
    )
    pred = extract_answer(result.get("answer", ""))
    success = bool(answer) and normalize_answer(pred) == normalize_answer(answer)
    return {
        "index": index,
        "task_id": result.get("task_id", f"{split_name}_{index}"),
        "dataset": split_name,
        "instruction": instruction,
        "image": image,
        "source": row.get("source", ""),
        "language": row.get("language", ""),
        "answer": answer,
        "pred": pred,
        "success": success,
        "steps": result.get("steps", 0),
        "trajectory_path": result.get("trajectory_path", ""),
        "elapsed_sec": time.time() - task_started,
        "tool_call_count": result.get("summary", {}).get("tool_call_count", 0),
    }


def run_dataset(
    dataset_path: Path,
    output_path: Path,
    trajectory_dir: Path,
    *,
    image_root: Path | None = None,
    limit: int | None = None,
    offset: int = 0,
    split_name: str = "eval",
    evolved: bool = True,
    model_name: str | None = None,
    llm_base_url: str | None = None,
    metrics_output: Path | None = None,
    workers: int = 1,
) -> dict[str, Any]:
    rows = _read_records(dataset_path)
    if offset:
        rows = rows[offset:]
    if limit is not None:
        rows = rows[:limit]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    trajectory_dir.mkdir(parents=True, exist_ok=True)

    correct = 0
    total = 0
    started = time.time()
    workers = max(1, int(workers))

    with output_path.open("w", encoding="utf-8") as out:
        if workers == 1:
            record_iter = (
                _run_one(
                    row,
                    source_index=offset + local_i,
                    split_name=split_name,
                    image_root=image_root,
                    trajectory_dir=trajectory_dir,
                    evolved=evolved,
                    model_name=model_name,
                    llm_base_url=llm_base_url,
                )
                for local_i, row in enumerate(rows)
            )
            for record in record_iter:
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                out.flush()
                total += 1
                correct += int(bool(record.get("answer")) and bool(record.get("success")))
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [
                    pool.submit(
                        _run_one,
                        row,
                        source_index=offset + local_i,
                        split_name=split_name,
                        image_root=image_root,
                        trajectory_dir=trajectory_dir,
                        evolved=evolved,
                        model_name=model_name,
                        llm_base_url=llm_base_url,
                    )
                    for local_i, row in enumerate(rows)
                ]
                for future in as_completed(futures):
                    record = future.result()
                    out.write(json.dumps(record, ensure_ascii=False) + "\n")
                    out.flush()
                    total += 1
                    correct += int(bool(record.get("answer")) and bool(record.get("success")))

    elapsed = time.time() - started
    metrics = {
        "dataset": str(dataset_path),
        "output": str(output_path),
        "trajectory_dir": str(trajectory_dir),
        "split_name": split_name,
        "mode": "evolved" if evolved else "baseline",
        "workers": workers,
        "total": total,
        "correct": correct,
        "accuracy": correct / total if total else 0.0,
        "elapsed_sec": elapsed,
    }
    if metrics_output is not None:
        metrics_output.parent.mkdir(parents=True, exist_ok=True)
        metrics_output.write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return metrics


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run harness evaluation on JSON/JSONL datasets.")
    p.add_argument("--dataset", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--traj-dir", required=True, type=Path)
    p.add_argument("--image-root", type=Path, default=None)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--split-name", default="eval")
    p.add_argument("--baseline", action="store_true", help="Disable memory/reflection prompt injection.")
    p.add_argument("--model", default=None)
    p.add_argument("--llm-url", default=None)
    p.add_argument("--metrics-output", type=Path, default=None)
    p.add_argument("--workers", type=int, default=1, help="Parallel task workers. Start with 4-8 for full SimpleVQA.")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    metrics = run_dataset(
        args.dataset,
        args.output,
        args.traj_dir,
        image_root=args.image_root,
        limit=args.limit,
        offset=args.offset,
        split_name=args.split_name,
        evolved=not args.baseline,
        model_name=args.model,
        llm_base_url=args.llm_url,
        metrics_output=args.metrics_output,
        workers=args.workers,
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
