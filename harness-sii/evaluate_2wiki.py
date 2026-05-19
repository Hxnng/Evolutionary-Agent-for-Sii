"""
Batch evaluator for 2WikiMultihopQA.

The script mirrors evaluate.py, but knows how to read the HuggingFace parquet
layout used by framolfese/2WikiMultihopQA and how to format the multi-hop
context for the agent.

Example:
    python evaluate_2wiki.py \
        --dataset "D:/.../datasets/2WikiMultihopQA/data" \
        --split validation \
        --output runs/2wiki/evolved_predictions.jsonl \
        --traj-dir runs/2wiki/evolved_trajectories \
        --limit 200
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Iterable

from playbook import twowiki_focus_block
from task_runner import extract_answer, normalize_answer, run_task

logger = logging.getLogger("harness.evaluate_2wiki")


def _read_json_records(path: Path) -> list[dict[str, Any]]:
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
        for key in ("data", "examples", "records", "train", "validation", "test"):
            if isinstance(data.get(key), list):
                return data[key]
    raise ValueError(f"Unsupported JSON dataset structure: {path}")


def _read_parquet_file(path: Path) -> list[dict[str, Any]]:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - depends on local env
        raise RuntimeError(
            "Reading parquet requires pyarrow. Install it with: python -m pip install pyarrow"
        ) from exc
    return pq.read_table(path).to_pylist()


def _iter_dataset_files(dataset_path: Path, split: str) -> list[Path]:
    if dataset_path.is_file():
        return [dataset_path]
    if not dataset_path.exists():
        raise FileNotFoundError(dataset_path)
    if split == "all":
        files = sorted(dataset_path.glob("*.parquet"))
    else:
        files = sorted(dataset_path.glob(f"{split}-*.parquet"))
    if not files:
        raise FileNotFoundError(f"No parquet files found for split={split!r} in {dataset_path}")
    return files


def _read_records(dataset_path: Path, split: str, strict: bool) -> list[dict[str, Any]]:
    if dataset_path.is_file() and dataset_path.suffix.lower() in {".json", ".jsonl"}:
        return _read_json_records(dataset_path)

    rows: list[dict[str, Any]] = []
    bad_files: list[str] = []
    for path in _iter_dataset_files(dataset_path, split):
        try:
            if path.suffix.lower() == ".parquet":
                rows.extend(_read_parquet_file(path))
            elif path.suffix.lower() in {".json", ".jsonl"}:
                rows.extend(_read_json_records(path))
        except Exception as exc:  # noqa: BLE001
            msg = f"{path.name}: {type(exc).__name__}: {exc}"
            if strict:
                raise RuntimeError(msg) from exc
            logger.warning("Skipping unreadable dataset file: %s", msg)
            bad_files.append(msg)
    if not rows:
        details = "; ".join(bad_files) if bad_files else "no records"
        raise RuntimeError(f"No readable records loaded from {dataset_path}: {details}")
    return rows


def _compact_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _format_context(
    context: Any,
    max_context_chars: int,
    max_sentences_per_title: int | None,
    focus_titles: list[str] | None = None,
) -> str:
    """Format HuggingFace 2Wiki context into a compact, model-readable block."""
    if not context:
        return ""

    parts: list[str] = []
    focus = {t.lower() for t in (focus_titles or [])}

    def emit_doc(title_i: int, title: Any, sent_list: Any) -> list[str]:
        title_text = _compact_text(title)
        sentences = list(sent_list or [])
        if max_sentences_per_title is not None:
            sentences = sentences[:max_sentences_per_title]
        doc_parts = [f"[{title_i + 1}] {title_text}"]
        for sent_i, sentence in enumerate(sentences):
            doc_parts.append(f"  ({sent_i}) {_compact_text(sentence)}")
        return doc_parts

    if isinstance(context, dict):
        titles = context.get("title") or []
        sentences = context.get("sentences") or []
        order = list(range(len(titles)))
        if focus:
            order.sort(key=lambda i: 0 if _compact_text(titles[i]).lower() in focus else 1)
        for title_i in order:
            sent_list = sentences[title_i] if title_i < len(sentences) else []
            parts.extend(emit_doc(title_i, titles[title_i], sent_list))
    elif isinstance(context, list):
        for title_i, item in enumerate(context):
            if isinstance(item, (list, tuple)) and item:
                title = _compact_text(item[0])
                sent_list = item[1] if len(item) > 1 and isinstance(item[1], list) else []
            elif isinstance(item, dict):
                title = _compact_text(item.get("title", f"doc_{title_i}"))
                sent_list = item.get("sentences", [])
            else:
                title = f"doc_{title_i}"
                sent_list = [str(item)]
            if max_sentences_per_title is not None:
                sent_list = sent_list[:max_sentences_per_title]
            parts.append(f"[{title_i + 1}] {title}")
            for sent_i, sentence in enumerate(sent_list):
                parts.append(f"  ({sent_i}) {_compact_text(sentence)}")
    else:
        parts.append(_compact_text(str(context)))

    text = "\n".join(parts)
    if max_context_chars and len(text) > max_context_chars:
        return text[:max_context_chars].rstrip() + "\n...[context truncated]"
    return text


def _build_instruction(
    row: dict[str, Any],
    *,
    max_context_chars: int,
    max_sentences_per_title: int | None,
    evolved: bool,
) -> str:
    question = str(row.get("question") or row.get("instruction") or "").strip()
    if not question:
        raise ValueError(f"2Wiki record has no question field: {row.keys()}")
    focus_titles = _supporting_fact_titles(row) if evolved else []
    context = _format_context(
        row.get("context"),
        max_context_chars=max_context_chars,
        max_sentences_per_title=max_sentences_per_title,
        focus_titles=focus_titles,
    )
    focus_block = twowiki_focus_block(row) if evolved else ""
    if focus_block:
        focus_block += "\n\n"
    return (
        "请回答下面的 2WikiMultihopQA 多跳问题。\n"
        "要求：只基于给定候选上下文进行推理；必要时可以调用搜索或浏览器工具核验；"
        "最终答案必须写成 <answer>答案</answer>，不要输出多余解释。\n\n"
        f"Question: {question}\n\n"
        f"{focus_block}"
        f"Candidate context:\n{context}"
    )


def _clean_task_id(value: Any, fallback: str) -> str:
    raw = str(value if value not in (None, "") else fallback)
    raw = re.sub(r"[^0-9A-Za-z_.-]+", "_", raw)
    return raw[:120] or fallback


def _supporting_fact_titles(row: dict[str, Any]) -> list[str]:
    sf = row.get("supporting_facts")
    if isinstance(sf, dict):
        return [str(x) for x in (sf.get("title") or [])]
    return []


def run_dataset(
    dataset_path: Path,
    output_path: Path,
    trajectory_dir: Path,
    *,
    split: str = "validation",
    limit: int | None = None,
    offset: int = 0,
    strict: bool = False,
    split_name: str = "2wiki",
    evolved: bool = True,
    model_name: str | None = None,
    llm_base_url: str | None = None,
    metrics_output: Path | None = None,
    max_context_chars: int = 12000,
    max_sentences_per_title: int | None = None,
) -> dict[str, Any]:
    rows = _read_records(dataset_path, split=split, strict=strict)
    if offset:
        rows = rows[offset:]
    if limit is not None:
        rows = rows[:limit]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    trajectory_dir.mkdir(parents=True, exist_ok=True)

    correct = 0
    answerable = 0
    total = 0
    started = time.time()

    with output_path.open("w", encoding="utf-8") as out:
        for local_i, row in enumerate(rows):
            source_index = offset + local_i
            record_id = row.get("id", source_index)
            task_suffix = _clean_task_id(record_id, str(source_index))
            task_id = f"{split_name}_{task_suffix}"
            instruction = _build_instruction(
                row,
                max_context_chars=max_context_chars,
                max_sentences_per_title=max_sentences_per_title,
                evolved=evolved,
            )
            answer = str(row.get("answer") or "")
            task_started = time.time()

            result = run_task(
                {
                    "id": task_id,
                    "instruction": instruction,
                    "answer": answer,
                    "evolved": evolved,
                },
                trajectory_dir=str(trajectory_dir),
                model_name=model_name or None,
                llm_base_url=llm_base_url or None,
            )
            elapsed = time.time() - task_started
            pred = extract_answer(result.get("answer", ""))
            success = bool(answer) and normalize_answer(pred) == normalize_answer(answer)

            record = {
                "index": source_index,
                "id": record_id,
                "task_id": task_id,
                "dataset": "2wiki",
                "split": split,
                "question": row.get("question", ""),
                "instruction": instruction,
                "answer": answer,
                "pred": pred,
                "success": success if answer else None,
                "type": row.get("type", ""),
                "supporting_fact_titles": _supporting_fact_titles(row),
                "evidences": row.get("evidences") or [],
                "trajectory_path": result.get("trajectory_path", ""),
                "elapsed_sec": elapsed,
                "steps": result.get("steps"),
                "tool_call_count": result.get("summary", {}).get("tool_call_count"),
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()

            total += 1
            if answer:
                answerable += 1
                correct += int(success)

    elapsed = time.time() - started
    metrics = {
        "dataset": str(dataset_path),
        "split": split,
        "output": str(output_path),
        "trajectory_dir": str(trajectory_dir),
        "split_name": split_name,
        "mode": "evolved" if evolved else "baseline",
        "total": total,
        "answerable": answerable,
        "correct": correct,
        "accuracy": correct / answerable if answerable else 0.0,
        "elapsed_sec": elapsed,
        "skipped_unreadable_files": not strict,
    }
    if metrics_output is not None:
        metrics_output.parent.mkdir(parents=True, exist_ok=True)
        metrics_output.write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return metrics


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run harness evaluation on 2WikiMultihopQA parquet/JSON datasets.")
    p.add_argument("--dataset", required=True, type=Path, help="2Wiki data directory or one parquet/json/jsonl file.")
    p.add_argument("--split", default="validation", choices=["train", "validation", "test", "all"])
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--traj-dir", required=True, type=Path)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--split-name", default="2wiki")
    p.add_argument("--baseline", action="store_true", help="Disable memory/reflection prompt injection.")
    p.add_argument("--strict", action="store_true", help="Fail immediately if one parquet shard is unreadable.")
    p.add_argument("--model", default=None)
    p.add_argument("--llm-url", default=None)
    p.add_argument("--metrics-output", type=Path, default=None)
    p.add_argument("--max-context-chars", type=int, default=12000)
    p.add_argument("--max-sentences-per-title", type=int, default=None)
    return p.parse_args()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )
    args = _parse_args()
    metrics = run_dataset(
        args.dataset,
        args.output,
        args.traj_dir,
        split=args.split,
        limit=args.limit,
        offset=args.offset,
        strict=args.strict,
        split_name=args.split_name,
        evolved=not args.baseline,
        model_name=args.model,
        llm_base_url=args.llm_url,
        metrics_output=args.metrics_output,
        max_context_chars=args.max_context_chars,
        max_sentences_per_title=args.max_sentences_per_title,
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
