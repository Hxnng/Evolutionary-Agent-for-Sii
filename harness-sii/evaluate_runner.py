"""Unified evaluation entry point.

Use this when you want one command surface for dataset + mode selection, while
keeping the dataset-specific evaluators responsible for loading and scoring.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import evaluate as simplevqa_eval
import evaluate_2wiki as twowiki_eval
import evaluate_benchmark as benchmark_eval
from eval_modes import add_mode_args, resolve_mode


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run a dataset evaluation with explicit project modes.")
    p.add_argument("--dataset-name", choices=["simplevqa", "2wiki", "benchmark"], required=True)
    p.add_argument("--dataset", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--traj-dir", required=True, type=Path)
    p.add_argument("--image-root", type=Path, default=None)
    p.add_argument("--split", default="validation", choices=["train", "validation", "test", "all"])
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--split-name", default=None)
    p.add_argument("--baseline", action="store_true")
    add_mode_args(p, dataset_name=None)
    p.add_argument("--strict", action="store_true")
    p.add_argument("--model", default=None)
    p.add_argument("--llm-url", default=None)
    p.add_argument("--metrics-output", type=Path, default=None)
    p.add_argument("--trajectory-output", type=Path, default=None)
    p.add_argument("--max-context-chars", type=int, default=12000)
    p.add_argument("--max-sentences-per-title", type=int, default=None)
    p.add_argument("--max-steps", type=int, default=None)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--group-id", default=None)
    p.add_argument("--submission-dir", type=Path, default=None)
    p.add_argument(
        "--no-fastpath",
        action="store_true",
        help="Disable dataset deterministic shortcuts so 2Wiki runs through the generator.",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    eval_mode = resolve_mode(args, dataset_name=args.dataset_name, trajectory_dir=args.traj_dir)
    common = {
        "limit": args.limit,
        "offset": args.offset,
        "evolved": not args.baseline,
        "model_name": args.model,
        "llm_base_url": args.llm_url,
        "metrics_output": args.metrics_output,
        "workers": args.workers,
        "trajectory_output": args.trajectory_output,
        "skills_dir": eval_mode.skills_dir,
        "learned_skills_dir": eval_mode.learned_skills_dir,
        "enable_reflection": eval_mode.reflection,
        "mode_label": eval_mode.label if not args.baseline else "baseline",
    }
    if args.dataset_name == "simplevqa":
        metrics = simplevqa_eval.run_dataset(
            args.dataset,
            args.output,
            args.traj_dir,
            image_root=args.image_root,
            split_name=args.split_name or "simplevqa",
            **common,
        )
    elif args.dataset_name == "2wiki":
        metrics = twowiki_eval.run_dataset(
            args.dataset,
            args.output,
            args.traj_dir,
            split=args.split,
            strict=args.strict,
            split_name=args.split_name or "2wiki",
            max_context_chars=args.max_context_chars,
            max_sentences_per_title=args.max_sentences_per_title,
            enable_fastpath=not args.no_fastpath,
            **common,
        )
    else:
        metrics = benchmark_eval.run_dataset(
            args.dataset,
            args.output,
            args.traj_dir,
            image_root=args.image_root,
            split_name=args.split_name or "benchmark",
            group_id=args.group_id,
            submission_dir=args.submission_dir,
            max_steps=args.max_steps,
            **common,
        )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
