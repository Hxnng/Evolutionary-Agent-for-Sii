"""
子进程评估入口
==============

被 evaluator.py 在子进程中调用，负责：
1. 将候选目录插入 sys.path（使候选 task_runner.py 优先导入）
2. 动态导入候选的 run_task
3. 执行评估并输出 JSON 结果到 stdout

用法（由 evaluator 自动调用，不手动运行）：
    CANDIDATE_DIR=/tmp/candidate_xxx python evaluate_runner.py \
        --dataset data.jsonl --output out.jsonl --traj-dir traj/ \
        --limit 50 --split-name eval
"""

import argparse
import json
import sys
import os
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--traj-dir", required=True, type=Path)
    parser.add_argument("--image-root", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--split-name", default="eval")
    parser.add_argument("--evolved", type=lambda x: x.lower() == "true", default=True)
    parser.add_argument("--model-name", default=None)
    parser.add_argument("--llm-base-url", default=None)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    # 关键：将候选目录插入 sys.path 最前面
    candidate_dir = os.environ.get("CANDIDATE_DIR")
    if candidate_dir:
        candidate_path = Path(candidate_dir)
        if candidate_path.exists():
            sys.path.insert(0, str(candidate_path))
            # 同时将候选目录的父目录（meta-harness-sii）也加入，
            # 以便候选代码能导入 memory、roles 等同级模块
            parent = candidate_path.parent
            if str(parent) not in sys.path:
                sys.path.insert(0, str(parent))

    # 动态导入 run_task —— 会优先使用候选目录中的 task_runner.py
    try:
        from task_runner import run_task, extract_answer, normalize_answer
    except ImportError as e:
        # 输出错误到 stderr，stdout 输出空结果
        print(f"[ERROR] Failed to import task_runner: {e}", file=sys.stderr)
        _write_empty_output(args.output, args.dataset, args.split_name)
        sys.exit(1)

    # 执行评估（复用 evaluate.py 的逻辑）
    try:
        metrics = _run_dataset(
            run_task_fn=run_task,
            extract_answer_fn=extract_answer,
            normalize_answer_fn=normalize_answer,
            dataset_path=args.dataset,
            output_path=args.output,
            trajectory_dir=args.traj_dir,
            image_root=args.image_root,
            limit=args.limit,
            offset=args.offset,
            split_name=args.split_name,
            evolved=args.evolved,
            model_name=args.model_name,
            llm_base_url=args.llm_base_url,
            workers=args.workers,
        )
        # 将 metrics 输出到 stdout
        print(json.dumps(metrics, ensure_ascii=False))
    except Exception as e:
        print(f"[ERROR] Evaluation failed: {e}", file=sys.stderr)
        _write_empty_output(args.output, args.dataset, args.split_name)
        sys.exit(1)


def _write_empty_output(output_path: Path, dataset_path: Path, split_name: str):
    """写入空的评估结果"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    metrics = {
        "dataset": str(dataset_path),
        "output": str(output_path),
        "split_name": split_name,
        "total": 0,
        "correct": 0,
        "accuracy": 0.0,
        "elapsed_sec": 0.0,
        "error": "import or execution failed",
    }
    output_path.write_text("", encoding="utf-8")
    # 输出空 metrics 到 stdout
    print(json.dumps(metrics, ensure_ascii=False))


def _run_dataset(
    run_task_fn,
    extract_answer_fn,
    normalize_answer_fn,
    dataset_path: Path,
    output_path: Path,
    trajectory_dir: Path,
    image_root: Path | None = None,
    limit: int | None = None,
    offset: int = 0,
    split_name: str = "eval",
    evolved: bool = True,
    model_name: str | None = None,
    llm_base_url: str | None = None,
    workers: int = 1,
) -> dict:
    """复制 evaluate.py 的 run_dataset 逻辑，但使用传入的函数引用"""
    import base64
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # 读取数据集
    if dataset_path.suffix.lower() == ".jsonl":
        rows = []
        for line in dataset_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    else:
        data = json.loads(dataset_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict):
            for key in ("data", "examples", "records", "test"):
                if isinstance(data.get(key), list):
                    rows = data[key]
                    break
            else:
                rows = []
        else:
            rows = []

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

    def _field(row, names, default=""):
        for name in names:
            value = row.get(name)
            if value is not None:
                return str(value)
        return default

    def _build_instruction(row):
        instruction = _field(row, ("instruction", "question", "query", "input", "prompt"))
        if not instruction:
            raise ValueError(f"Record has no instruction/question field: {row.keys()}")
        image_description = _field(row, ("image_description", "caption", "description"), "")
        if image_description:
            instruction = f"{instruction}\n\n图像描述参考：{image_description}"
        return instruction

    def _image_to_b64(image, image_root):
        if not image or image.startswith(("http://", "https://", "data:")):
            return None
        path = Path(image)
        if not path.is_absolute() and image_root is not None:
            path = image_root / image
        if not path.exists():
            return None
        return base64.b64encode(path.read_bytes()).decode("utf-8")

    def _run_one(row, source_index):
        index = row.get("index", row.get("data_id", row.get("id", source_index)))
        instruction = _build_instruction(row)
        answer = _field(row, ("answer", "gold", "label", "target"))
        image = _field(row, ("image", "image_path", "image_url", "img"), "")
        image_url = image if image.startswith(("http://", "https://", "data:")) else ""
        image_b64 = _image_to_b64(image, image_root)

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
        result = run_task_fn(
            task,
            trajectory_dir=str(trajectory_dir),
            model_name=model_name or None,
            llm_base_url=llm_base_url or None,
        )
        pred = extract_answer_fn(result.get("answer", ""))
        success = bool(answer) and normalize_answer_fn(pred) == normalize_answer_fn(answer)
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

    with output_path.open("w", encoding="utf-8") as out:
        if workers == 1:
            for local_i, row in enumerate(rows):
                record = _run_one(row, offset + local_i)
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                out.flush()
                total += 1
                correct += int(bool(record.get("answer")) and bool(record.get("success")))
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [
                    pool.submit(_run_one, row, offset + local_i)
                    for local_i, row in enumerate(rows)
                ]
                for future in as_completed(futures):
                    record = future.result()
                    out.write(json.dumps(record, ensure_ascii=False) + "\n")
                    out.flush()
                    total += 1
                    correct += int(bool(record.get("answer")) and bool(record.get("success")))

    elapsed = time.time() - started
    return {
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


if __name__ == "__main__":
    main()
