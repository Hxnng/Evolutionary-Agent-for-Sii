"""
Batch evaluator for benchmark.csv.

Expected CSV columns:
    problem,image,answer

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

from task_runner import extract_answer, normalize_answer, run_task


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
        },
        trajectory_dir=str(trajectory_dir),
        model_name=model_name or None,
        llm_base_url=llm_base_url or None,
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


def _write_submission_answers(
    *,
    source_rows: list[dict[str, Any]],
    records: list[dict[str, Any]],
    output_path: Path,
) -> None:
    by_index = {int(record["index"]): record for record in records}
    fieldnames = [key for key in source_rows[0].keys() if not key.startswith("__")] if source_rows else ["problem", "image"]
    if "answer" not in fieldnames:
        fieldnames.append("answer")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in source_rows:
            source_index = int(row.get("__source_index", len(by_index)))
            out_row = {key: row.get(key, "") for key in fieldnames}
            out_row["answer"] = by_index.get(source_index, {}).get("pred", "")
            writer.writerow(out_row)


def _write_submission_trajectory(records: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as out:
        for record in sorted(records, key=lambda item: int(item["index"])):
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


def _write_submission_zip(*, answer_csv: Path, trajectory_json: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(trajectory_json, arcname=trajectory_json.name)
        zf.write(answer_csv, arcname=answer_csv.name)


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
                )
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
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
                    )
                    for local_i, row in enumerate(rows)
                ]
                for future in as_completed(futures):
                    record = future.result()
                    out.write(json.dumps(record, ensure_ascii=False) + "\n")
                    out.flush()
                    records.append(record)
                    _score(record)

    records.sort(key=lambda item: int(item["index"]))

    elapsed = time.time() - started
    metrics = {
        "dataset": str(dataset_path),
        "output": str(output_path),
        "trajectory_dir": str(trajectory_dir),
        "split_name": split_name,
        "mode": "evolved" if evolved else "baseline",
        "workers": workers,
        "total": total,
        "answerable": answerable,
        "correct": correct,
        "accuracy": correct / answerable if answerable else 0.0,
        "elapsed_sec": elapsed,
    }
    if group_id:
        target_dir = submission_dir or output_path.parent
        answer_csv = target_dir / f"group_{group_id}.csv"
        trajectory_json = target_dir / f"group_{group_id}.json"
        zip_path = target_dir / f"group_{group_id}.zip"
        _write_submission_answers(
            source_rows=rows,
            records=records,
            output_path=answer_csv,
        )
        _write_submission_trajectory(records, trajectory_json)
        _write_submission_zip(
            answer_csv=answer_csv,
            trajectory_json=trajectory_json,
            zip_path=zip_path,
        )
        metrics.update(
            {
                "submission_answer_csv": str(answer_csv),
                "submission_trajectory_json": str(trajectory_json),
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
    p.add_argument("--model", default=None)
    p.add_argument("--llm-url", default=None)
    p.add_argument("--metrics-output", type=Path, default=None)
    p.add_argument("--group-id", default=None, help="Generate group_{id}.csv/json/zip submission files.")
    p.add_argument("--submission-dir", type=Path, default=None, help="Directory for group submission files.")
    p.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Parallel task workers. Start with 4-8 for large benchmark.csv runs.",
    )
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
        group_id=args.group_id,
        submission_dir=args.submission_dir,
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
