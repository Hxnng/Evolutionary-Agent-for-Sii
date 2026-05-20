"""
Batch evaluator for benchmark.csv.

Expected CSV columns:
    problem,image,answer

Prediction JSONL follows the course PDF submission shape exactly:
{"index":, "instruction":, "image":, "answer":, "pred":}

The image column can be empty, an http(s) URL, a data:image/... base64 URL,
a raw base64 image string, or a local image path. Raw base64 images are wrapped
as data URLs with a MIME type inferred from their magic bytes.
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import re
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from eval_modes import add_mode_args, resolve_mode
from task_runner import MAX_STEPS, extract_answer, normalize_answer, run_task


PREDICTION_FIELDS = ("index", "instruction", "image", "answer", "pred")


def _prediction_record(record: dict[str, Any]) -> dict[str, Any]:
    return {field: record.get(field, "") for field in PREDICTION_FIELDS}


def _index_sort_key(record: dict[str, Any]) -> tuple[int, Any]:
    value = record.get("index", 0)
    try:
        return (0, int(value))
    except (TypeError, ValueError):
        return (1, str(value))


def _read_csv_records(path: Path) -> list[dict[str, Any]]:
    csv.field_size_limit(sys.maxsize)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = [dict(row) for row in reader]
    missing = {"problem", "image"} - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"CSV is missing required columns: {sorted(missing)}")
    return rows


def _looks_like_base64(text: str) -> bool:
    if not text or len(text) < 32:
        return False
    if re.search(r"[^A-Za-z0-9+/=\s-]", text):
        return False
    try:
        base64.b64decode(text.strip(), validate=True)
        return True
    except Exception:  # noqa: BLE001
        return False


def _mime_from_bytes(data: bytes) -> str:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    return "image/jpeg"


def _data_url_from_bytes(data: bytes) -> str:
    mime = _mime_from_bytes(data)
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def _image_to_url(image: str, image_root: Path | None) -> tuple[str, str]:
    """Return (image_url_for_model, safe_image_for_output)."""
    image = (image or "").strip()
    if not image:
        return "", ""
    if image.startswith(("http://", "https://", "data:image/")):
        safe = image if len(image) < 500 else f"<image_url:{len(image)} chars>"
        return image, safe

    compact = re.sub(r"\s+", "", image)
    if _looks_like_base64(compact):
        data = base64.b64decode(compact, validate=True)
        return f"data:{_mime_from_bytes(data)};base64,{compact}", f"<base64_image:{len(compact)} chars>"

    path = Path(image)
    if not path.is_absolute() and image_root is not None:
        path = image_root / image
    if path.exists():
        return _data_url_from_bytes(path.read_bytes()), str(image)

    return "", image


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
    max_steps: int | None,
    skills_dir: str,
    learned_skills_dir: str,
    enable_reflection: bool,
) -> dict[str, Any]:
    image_url, safe_image = _image_to_url(row.get("image", ""), image_root)
    instruction = _build_instruction(str(row.get("problem") or ""), bool(image_url))
    answer = str(row.get("answer") or "")
    task_id = f"{split_name}_{source_index}"
    task_started = time.time()
    result = run_task(
        {
            "id": task_id,
            "instruction": instruction,
            "answer": answer,
            "image_url": image_url,
            "evolved": evolved,
            "skills_dir": skills_dir,
            "learned_skills_dir": learned_skills_dir,
            "enable_reflection": enable_reflection,
            "write_short_term_memory": enable_reflection,
        },
        trajectory_dir=str(trajectory_dir),
        model_name=model_name or None,
        llm_base_url=llm_base_url or None,
        max_steps=max_steps if max_steps is not None else MAX_STEPS,
    )
    pred = extract_answer(result.get("answer", ""))
    success = bool(answer) and normalize_answer(pred) == normalize_answer(answer)
    return {
        "index": source_index,
        "task_id": task_id,
        "dataset": "benchmark",
        "problem": row.get("problem", ""),
        "instruction": instruction,
        "image": safe_image,
        "has_image": bool(image_url),
        "answer": answer,
        "pred": pred,
        "success": success if answer else None,
        "trajectory_path": result.get("trajectory_path", ""),
        "elapsed_sec": time.time() - task_started,
        "steps": result.get("steps"),
        "tool_call_count": result.get("summary", {}).get("tool_call_count"),
    }


def _write_prediction_jsonl(records: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as out:
        for record in sorted(records, key=_index_sort_key):
            out.write(json.dumps(_prediction_record(record), ensure_ascii=False) + "\n")


def _write_submission_trajectory(records: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as out:
        for record in sorted(records, key=_index_sort_key):
            traj_path = Path(str(record.get("trajectory_path") or ""))
            if not traj_path.exists():
                continue
            with traj_path.open("r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.strip():
                        out.write(
                            json.dumps(
                                _submission_trace_entry(json.loads(line), record),
                                ensure_ascii=False,
                            )
                            + "\n"
                        )


def _submission_trace_entry(entry: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    if entry.get("role") != "user" or entry.get("step_id") != 0 or not record.get("image"):
        return entry
    content = entry.get("content")
    if not isinstance(content, list):
        return entry
    text_parts = [item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text"]
    text = "\n".join(part for part in text_parts if part).strip()
    image_ref = str(record.get("image") or "")
    if text:
        text = re.sub(r"输入图像的在线链接：\S+", f"image_url: {image_ref}", text)
        text = re.sub(r"image_url:\s*\S+", f"image_url: {image_ref}", text)
        if "image_url:" not in text:
            text = f"{text}\nimage_url: {image_ref}"
    else:
        text = f"{record.get('problem', '')}\nimage_url: {image_ref}".strip()
    updated = dict(entry)
    updated["content"] = [
        {"type": "image_url", "image_url": {"url": image_ref}},
        {"type": "text", "text": text},
    ]
    return updated


def _write_submission_zip(*, prediction_jsonl: Path, trajectory_jsonl: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(prediction_jsonl, arcname=prediction_jsonl.name)
        zf.write(trajectory_jsonl, arcname=trajectory_jsonl.name)


def _build_instruction(problem: str, has_image: bool) -> str:
    problem = problem.strip()
    if not problem:
        raise ValueError("CSV row has an empty problem field")
    if has_image:
        return (
            "Please answer the benchmark problem. Use the attached image if it is relevant. "
            "You may call search and browser tools when needed. "
            "Return the final answer only inside <answer>...</answer>.\n\n"
            f"Problem: {problem}"
        )
    return (
        "Please answer the benchmark problem. You may call search and browser tools when needed. "
        "Return the final answer only inside <answer>...</answer>.\n\n"
        f"Problem: {problem}"
    )


def run_dataset(
    dataset_path: Path,
    output_path: Path,
    trajectory_dir: Path,
    *,
    image_root: Path | None = None,
    limit: int | None = None,
    offset: int = 0,
    split_name: str = "benchmark",
    evolved: bool = True,
    model_name: str | None = None,
    llm_base_url: str | None = None,
    metrics_output: Path | None = None,
    workers: int = 1,
    group_id: str | None = None,
    submission_dir: Path | None = None,
    max_steps: int | None = None,
    trajectory_output: Path | None = None,
    skills_dir: str = "skills",
    learned_skills_dir: str = "learned_skills",
    enable_reflection: bool = True,
    mode_label: str | None = None,
) -> dict[str, Any]:
    all_rows = _read_csv_records(dataset_path)
    for source_index, row in enumerate(all_rows):
        row["__source_index"] = source_index
    rows = all_rows
    if offset:
        rows = rows[offset:]
    if limit is not None:
        rows = rows[:limit]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    trajectory_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    answerable = 0
    correct = 0
    started = time.time()
    workers = max(1, int(workers))
    records: list[dict[str, Any]] = []

    def _score(record: dict[str, Any]) -> None:
        nonlocal total, answerable, correct
        total += 1
        if record.get("answer"):
            answerable += 1
            if record.get("success"):
                correct += 1

    with output_path.open("w", encoding="utf-8") as out:
        if workers == 1:
            for local_i, row in enumerate(rows):
                record = _run_one(
                    row,
                    source_index=offset + local_i,
                    split_name=split_name,
                    image_root=image_root,
                    trajectory_dir=trajectory_dir,
                    evolved=evolved,
                    model_name=model_name,
                    llm_base_url=llm_base_url,
                    max_steps=max_steps,
                    skills_dir=skills_dir,
                    learned_skills_dir=learned_skills_dir,
                    enable_reflection=enable_reflection,
                )
                out.write(json.dumps(_prediction_record(record), ensure_ascii=False) + "\n")
                out.flush()
                records.append(record)
                _score(record)
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
                        max_steps=max_steps,
                        skills_dir=skills_dir,
                        learned_skills_dir=learned_skills_dir,
                        enable_reflection=enable_reflection,
                    )
                    for local_i, row in enumerate(rows)
                ]
                for future in as_completed(futures):
                    record = future.result()
                    out.write(json.dumps(_prediction_record(record), ensure_ascii=False) + "\n")
                    out.flush()
                    records.append(record)
                    _score(record)

    records.sort(key=_index_sort_key)

    elapsed = time.time() - started
    metrics = {
        "dataset": str(dataset_path),
        "output": str(output_path),
        "trajectory_dir": str(trajectory_dir),
        "split_name": split_name,
        "mode": mode_label or ("evolved" if evolved else "baseline"),
        "skills_dir": skills_dir,
        "learned_skills_dir": learned_skills_dir,
        "reflection": enable_reflection,
        "workers": workers,
        "total": total,
        "answerable": answerable,
        "correct": correct,
        "accuracy": correct / answerable if answerable else 0.0,
        "elapsed_sec": elapsed,
    }
    if trajectory_output is not None:
        _write_submission_trajectory(records, trajectory_output)
        metrics["trajectory_output"] = str(trajectory_output)
    if group_id:
        target_dir = submission_dir or output_path.parent
        prediction_jsonl = target_dir / f"group_{group_id}.jsonl"
        trajectory_jsonl = target_dir / f"group_{group_id}_trajectories.jsonl"
        zip_path = target_dir / f"group_{group_id}.zip"
        _write_prediction_jsonl(records, prediction_jsonl)
        _write_submission_trajectory(records, trajectory_jsonl)
        _write_submission_zip(
            prediction_jsonl=prediction_jsonl,
            trajectory_jsonl=trajectory_jsonl,
            zip_path=zip_path,
        )
        metrics.update(
            {
                "submission_prediction_jsonl": str(prediction_jsonl),
                "submission_trajectory_jsonl": str(trajectory_jsonl),
                "submission_zip": str(zip_path),
            }
        )
    if metrics_output is not None:
        metrics_output.parent.mkdir(parents=True, exist_ok=True)
        metrics_output.write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return metrics


def generate_submission_files(
    benchmark_output: Path,
    trajectory_dir: Path,
    group_number: int,
    output_dir: Path,
):
    """
    生成打榜提交文件（PDF 要求的 JSONL 口径）

    生成：
    - group_{N}.jsonl: 最终结果文件（index, instruction, image, answer, pred）
    - group_{N}_trajectories.jsonl: 轨迹文件
    - group_{N}.zip: 包含上述两个 JSONL
    """
    # 加载benchmark输出
    records = []
    with open(benchmark_output, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    output_dir.mkdir(parents=True, exist_ok=True)
    group_name = f"group_{group_number}"

    # 生成最终结果文件
    prediction_path = output_dir / f"{group_name}.jsonl"
    _write_prediction_jsonl(records, prediction_path)
    print(f"Generated {prediction_path} with {len(records)} predictions")

    # 生成轨迹文件（一个 step 一行）
    trajectory_path = output_dir / f"{group_name}_trajectories.jsonl"
    full_records = []
    for record in records:
        traj_ref = record.get("trajectory_path", "")
        if traj_ref:
            traj_path = Path(traj_ref)
            if not traj_path.is_absolute():
                traj_path = trajectory_dir / traj_ref
            record["trajectory_path"] = str(traj_path)
        full_records.append(record)
    _write_submission_trajectory(full_records, trajectory_path)
    print(f"Generated {trajectory_path}")

    # 生成压缩文件
    zip_path = output_dir / f"{group_name}.zip"
    _write_submission_zip(
        prediction_jsonl=prediction_path,
        trajectory_jsonl=trajectory_path,
        zip_path=zip_path,
    )
    print(f"Generated {zip_path}")

    print(f"\nSubmission files generated in {output_dir}/")
    print(f"  - {group_name}.jsonl (predictions)")
    print(f"  - {group_name}_trajectories.jsonl (trajectories)")
    print(f"  - {group_name}.zip (jsonl bundle)")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run harness evaluation on benchmark.csv.")
    p.add_argument("--dataset", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--traj-dir", required=True, type=Path)
    p.add_argument("--image-root", type=Path, default=None)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--split-name", default="benchmark")
    p.add_argument("--baseline", action="store_true", help="Disable memory/reflection prompt injection.")
    add_mode_args(p, dataset_name="benchmark")
    p.add_argument("--model", default=None)
    p.add_argument("--llm-url", default=None)
    p.add_argument("--metrics-output", type=Path, default=None)
    p.add_argument("--max-steps", type=int, default=None, help="Max agent loop steps. Defaults to MAX_STEPS from .env.")
    p.add_argument("--trajectory-output", type=Path, default=None, help="Merge all task trajectories into one PDF-format JSONL file.")
    p.add_argument("--group-id", default=None, help="Generate group_{id}.jsonl, group_{id}_trajectories.jsonl, and a zip bundle.")
    p.add_argument("--submission-dir", type=Path, default=None, help="Directory for group submission files.")
    p.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Parallel task workers. Start with 4-8 for large benchmark.csv runs.",
    )
    p.add_argument(
        "--group-number",
        type=int,
        default=None,
        help="Alias for --group-id, kept for older commands.",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    eval_mode = resolve_mode(args, dataset_name="benchmark", trajectory_dir=args.traj_dir)
    group_id = args.group_id or (str(args.group_number) if args.group_number is not None else None)
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
        group_id=group_id,
        submission_dir=args.submission_dir,
        max_steps=args.max_steps,
        trajectory_output=args.trajectory_output,
        skills_dir=eval_mode.skills_dir,
        learned_skills_dir=eval_mode.learned_skills_dir,
        enable_reflection=eval_mode.reflection,
        mode_label=eval_mode.label if not args.baseline else "baseline",
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
