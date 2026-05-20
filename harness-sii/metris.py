"""
Unified metrics and ranking script for SimpleVQA and 2WikiMultihopQA outputs.

The filename intentionally follows the requested spelling: metris.py.

It can:
  1. summarize one prediction JSONL + trajectory directory;
  2. compare baseline vs evolved runs on the same cases;
  3. score one or more baseline/evolved pairs for leaderboard reporting.

Examples:
    python metris.py \
        --pred runs/evolved_browser_check/simplevqa_predictions_5.jsonl \
        --traj-dir runs/evolved_browser_check/simplevqa_trajectories_5

    python metris.py \
        --baseline-pred runs/base/pred.jsonl --baseline-traj runs/base/traj \
        --evolved-pred runs/evolved/pred.jsonl --evolved-traj runs/evolved/traj \
        --case-limit 200

    python metris.py --pairs pairs.json --output report.json

pairs.json:
[
  {
    "name": "team_a",
    "baseline_pred": "runs/team_a_base/pred.jsonl",
    "baseline_traj": "runs/team_a_base/traj",
    "evolved_pred": "runs/team_a_evolved/pred.jsonl",
    "evolved_traj": "runs/team_a_evolved/traj"
  }
]
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


ANSWER_FIELDS = ("answer", "gold", "label", "target")
PRED_FIELDS = ("pred", "prediction", "output", "response")


def normalize_answer(text: Any) -> str:
    text = str(text or "").strip().lower()
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"(?<=\d)年(?=$|[\s,，。.!?？])", "", text)
    text = re.sub(r"[\s\W_]+", "", text, flags=re.UNICODE)
    return text


def token_f1(pred: Any, answer: Any) -> float:
    pred_text = str(pred or "").lower()
    ans_text = str(answer or "").lower()
    pred_tokens = re.findall(r"\w+", pred_text, flags=re.UNICODE)
    ans_tokens = re.findall(r"\w+", ans_text, flags=re.UNICODE)
    if not pred_tokens and not ans_tokens:
        return 1.0
    if not pred_tokens or not ans_tokens:
        return 0.0
    pred_counts = Counter(pred_tokens)
    ans_counts = Counter(ans_tokens)
    common = sum((pred_counts & ans_counts).values())
    if common == 0:
        return 0.0
    precision = common / len(pred_tokens)
    recall = common / len(ans_tokens)
    return 2 * precision * recall / (precision + recall)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _first(row: dict[str, Any], names: tuple[str, ...], default: Any = "") -> Any:
    for name in names:
        if name in row and row[name] is not None:
            return row[name]
    return default


def _case_key(row: dict[str, Any], fallback: int) -> str:
    for key in ("task_id", "index", "id"):
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return str(fallback)


def _load_trajectory(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                rows.append(
                    {
                        "role": "tool",
                        "content": f"[MALFORMED JSONL LINE {line_no}]",
                        "timestamp": None,
                    }
                )
    return rows


def _candidate_traj_files(traj_dir: Path, row: dict[str, Any], ordinal: int) -> list[Path]:
    candidates: list[Path] = []
    explicit = row.get("trajectory_path")
    if explicit:
        candidates.append(Path(explicit))
    for value in (row.get("task_id"), row.get("index"), row.get("id")):
        if value not in (None, ""):
            safe = re.sub(r"[^0-9A-Za-z_.-]+", "_", str(value))
            candidates.extend(sorted(traj_dir.glob(f"*{safe}.jsonl")))
            candidates.extend(sorted(traj_dir.glob(f"*_{safe}.jsonl")))
    all_files = sorted(traj_dir.glob("*.jsonl"))
    if ordinal < len(all_files):
        candidates.append(all_files[ordinal])

    seen: set[str] = set()
    unique: list[Path] = []
    for path in candidates:
        resolved = str(path)
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    return unique


def _is_failed_tool(content: Any) -> bool:
    text = str(content or "")
    if "[ERROR]" in text or "[HARNESS ERROR]" in text:
        return True
    try:
        parsed = json.loads(text)
    except Exception:  # noqa: BLE001
        return False
    if isinstance(parsed, dict):
        return parsed.get("ok") is False or parsed.get("success") is False
    if isinstance(parsed, list):
        return any(isinstance(x, dict) and x.get("ok") is False for x in parsed)
    return False


@dataclass
class TrajectoryStats:
    total_tokens: int = 0
    assistant_turns: int = 0
    tool_calls: int = 0
    repeated_tool_calls: int = 0
    failed_tool_calls: int = 0
    empty_assistant_turns: int = 0
    elapsed_sec: float = 0.0
    reached_max_steps: bool = False
    missing: bool = False

    @property
    def invalid_steps(self) -> int:
        return self.failed_tool_calls + self.empty_assistant_turns + int(self.reached_max_steps)


def trajectory_stats(path: Path | None) -> TrajectoryStats:
    if path is None or not path.exists():
        return TrajectoryStats(missing=True)
    rows = _load_trajectory(path)
    stats = TrajectoryStats()
    timestamps: list[float] = []
    tool_signatures: Counter[str] = Counter()
    for row in rows:
        ts = row.get("timestamp")
        if isinstance(ts, (int, float)):
            timestamps.append(float(ts))
        role = row.get("role")
        content = row.get("content", "")
        if role == "assistant":
            stats.assistant_turns += 1
            try:
                stats.total_tokens += int(row.get("total_tokens") or 0)
            except (TypeError, ValueError):
                pass
            tool_calls = row.get("tool_calls") or []
            stats.tool_calls += len(tool_calls)
            if not str(content or "").strip() and not tool_calls:
                stats.empty_assistant_turns += 1
        elif role == "tool":
            if row.get("fn_name"):
                try:
                    sig = json.dumps(
                        {"fn": row.get("fn_name"), "args": row.get("fn_args") or {}},
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                except TypeError:
                    sig = f"{row.get('fn_name')}:{row.get('fn_args')}"
                tool_signatures[sig] += 1
            if row.get("fn_name") and stats.tool_calls == 0:
                # Older trajectories can be counted from tool rows if assistant
                # tool_calls were not persisted.
                stats.tool_calls += 1
            if _is_failed_tool(content):
                stats.failed_tool_calls += 1
            if "Max steps reached" in str(content):
                stats.reached_max_steps = True
        if row.get("reached_max_steps") is True:
            stats.reached_max_steps = True
    if timestamps:
        stats.elapsed_sec = max(timestamps) - min(timestamps)
    stats.repeated_tool_calls = sum(max(0, count - 1) for count in tool_signatures.values())
    return stats


@dataclass
class RunSummary:
    name: str
    prediction_path: str
    trajectory_dir: str
    cases: int
    answerable_cases: int
    correct: int
    accuracy: float
    avg_f1: float
    avg_tokens: float
    avg_reasoning_turns: float
    avg_tool_calls: float
    avg_repeated_tool_calls: float
    avg_failed_tool_calls: float
    avg_invalid_steps: float
    avg_elapsed_sec: float
    total_tokens: int
    total_tool_calls: int
    total_repeated_tool_calls: int
    total_failed_tool_calls: int
    total_elapsed_sec: float
    missing_trajectories: int


def summarize_run(
    pred_path: Path,
    traj_dir: Path,
    *,
    name: str = "run",
    case_limit: int | None = None,
) -> tuple[RunSummary, dict[str, dict[str, Any]]]:
    rows = read_jsonl(pred_path)
    if case_limit is not None:
        rows = rows[:case_limit]

    per_case: dict[str, dict[str, Any]] = {}
    correct = 0
    answerable = 0
    f1_values: list[float] = []
    token_values: list[int] = []
    turn_values: list[int] = []
    tool_values: list[int] = []
    repeated_tool_values: list[int] = []
    failed_tool_values: list[int] = []
    invalid_values: list[int] = []
    elapsed_values: list[float] = []
    missing_traj = 0

    for ordinal, row in enumerate(rows):
        key = _case_key(row, ordinal)
        answer = _first(row, ANSWER_FIELDS)
        pred = _first(row, PRED_FIELDS)
        has_answer = bool(str(answer or ""))
        if isinstance(row.get("success"), bool):
            is_correct = bool(row["success"])
        else:
            is_correct = has_answer and normalize_answer(pred) == normalize_answer(answer)
        if has_answer:
            answerable += 1
            correct += int(is_correct)
            f1_values.append(token_f1(pred, answer))

        chosen_traj: Path | None = None
        for candidate in _candidate_traj_files(traj_dir, row, ordinal):
            if candidate.exists():
                chosen_traj = candidate
                break
        stats = trajectory_stats(chosen_traj)
        if stats.missing:
            missing_traj += 1

        elapsed = row.get("elapsed_sec")
        if isinstance(elapsed, (int, float)) and elapsed > 0:
            stats.elapsed_sec = float(elapsed)

        token_values.append(stats.total_tokens)
        turn_values.append(stats.assistant_turns)
        tool_values.append(stats.tool_calls)
        repeated_tool_values.append(stats.repeated_tool_calls)
        failed_tool_values.append(stats.failed_tool_calls)
        invalid_values.append(stats.invalid_steps)
        elapsed_values.append(stats.elapsed_sec)

        per_case[key] = {
            "problem": row.get("problem") or row.get("question") or row.get("instruction", ""),
            "answer": answer,
            "pred": pred,
            "correct": is_correct,
            "f1": token_f1(pred, answer) if has_answer else None,
            "tokens": stats.total_tokens,
            "reasoning_turns": stats.assistant_turns,
            "tool_calls": stats.tool_calls,
            "repeated_tool_calls": stats.repeated_tool_calls,
            "failed_tool_calls": stats.failed_tool_calls,
            "invalid_steps": stats.invalid_steps,
            "elapsed_sec": stats.elapsed_sec,
            "trajectory_path": str(chosen_traj) if chosen_traj else "",
        }

    cases = len(rows)
    summary = RunSummary(
        name=name,
        prediction_path=str(pred_path),
        trajectory_dir=str(traj_dir),
        cases=cases,
        answerable_cases=answerable,
        correct=correct,
        accuracy=correct / answerable if answerable else 0.0,
        avg_f1=statistics.mean(f1_values) if f1_values else 0.0,
        avg_tokens=statistics.mean(token_values) if token_values else 0.0,
        avg_reasoning_turns=statistics.mean(turn_values) if turn_values else 0.0,
        avg_tool_calls=statistics.mean(tool_values) if tool_values else 0.0,
        avg_repeated_tool_calls=statistics.mean(repeated_tool_values) if repeated_tool_values else 0.0,
        avg_failed_tool_calls=statistics.mean(failed_tool_values) if failed_tool_values else 0.0,
        avg_invalid_steps=statistics.mean(invalid_values) if invalid_values else 0.0,
        avg_elapsed_sec=statistics.mean(elapsed_values) if elapsed_values else 0.0,
        total_tokens=sum(token_values),
        total_tool_calls=sum(tool_values),
        total_repeated_tool_calls=sum(repeated_tool_values),
        total_failed_tool_calls=sum(failed_tool_values),
        total_elapsed_sec=sum(elapsed_values),
        missing_trajectories=missing_traj,
    )
    return summary, per_case


def _ratio_reduction(old: float, new: float) -> float:
    if old <= 0:
        return 0.0 if new <= 0 else -1.0
    return (old - new) / old


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _dimension_score(value: float, target: float, points: float = 7.0) -> float:
    if target <= 0:
        return 0.0
    return points * _clamp(value / target)


def compare_runs(
    baseline: RunSummary,
    evolved: RunSummary,
) -> dict[str, Any]:
    accuracy_gain = evolved.accuracy - baseline.accuracy
    token_reduction = _ratio_reduction(baseline.avg_tokens, evolved.avg_tokens)
    reasoning_reduction = _ratio_reduction(baseline.avg_invalid_steps, evolved.avg_invalid_steps)
    if baseline.avg_invalid_steps == 0:
        reasoning_reduction = _ratio_reduction(baseline.avg_reasoning_turns, evolved.avg_reasoning_turns)
    tool_reduction = _ratio_reduction(baseline.avg_tool_calls, evolved.avg_tool_calls)
    repeated_tool_reduction = _ratio_reduction(
        baseline.avg_repeated_tool_calls,
        evolved.avg_repeated_tool_calls,
    )
    failed_tool_reduction = _ratio_reduction(
        baseline.avg_failed_tool_calls,
        evolved.avg_failed_tool_calls,
    )
    time_reduction = _ratio_reduction(baseline.avg_elapsed_sec, evolved.avg_elapsed_sec)

    dimensions = {
        "accuracy_improvement": {
            "value": accuracy_gain,
            "score": _dimension_score(accuracy_gain, target=0.10),
            "max_score": 7,
        },
        "token_optimization": {
            "value": token_reduction,
            "score": _dimension_score(token_reduction, target=0.20),
            "max_score": 7,
        },
        "reasoning_round_optimization": {
            "value": reasoning_reduction,
            "score": _dimension_score(reasoning_reduction, target=0.20),
            "max_score": 7,
        },
        "tool_call_optimization": {
            "value": max(tool_reduction, failed_tool_reduction, repeated_tool_reduction),
            "score": _dimension_score(
                max(tool_reduction, failed_tool_reduction, repeated_tool_reduction),
                target=0.20,
            ),
            "max_score": 7,
            "avg_tool_call_reduction": tool_reduction,
            "avg_failed_tool_call_reduction": failed_tool_reduction,
            "avg_repeated_tool_call_reduction": repeated_tool_reduction,
        },
        "time_optimization": {
            "value": time_reduction,
            "score": _dimension_score(time_reduction, target=0.20),
            "max_score": 7,
        },
    }
    efficiency_score = sum(float(v["score"]) for v in dimensions.values())

    mechanism_raw = (
        max(0.0, accuracy_gain) * 2.0
        + max(0.0, token_reduction)
        + max(0.0, reasoning_reduction)
        + max(0.0, max(tool_reduction, failed_tool_reduction))
        + max(0.0, time_reduction)
    )
    final_raw = evolved.accuracy

    return {
        "baseline": asdict(baseline),
        "evolved": asdict(evolved),
        "dimensions": dimensions,
        "evolution_efficiency_score_35_linear": efficiency_score,
        "mechanism_raw": mechanism_raw,
        "final_result_raw": final_raw,
        "notes": [
            "The 35-point linear score gives each dimension up to 7 points.",
            "Full dimension credit targets: +10 absolute accuracy points, or 20% reduction for tokens/steps/tools/time.",
            "Leaderboard rank points are computed separately when multiple pairs are supplied.",
        ],
    }


def _rank_points(items: list[dict[str, Any]], key: str, points: float) -> dict[str, float]:
    if not items:
        return {}
    if len(items) == 1:
        return {items[0]["name"]: points}
    sorted_items = sorted(items, key=lambda x: x[key], reverse=True)
    result: dict[str, float] = {}
    i = 0
    n = len(sorted_items)
    while i < n:
        j = i
        while j + 1 < n and math.isclose(sorted_items[j + 1][key], sorted_items[i][key]):
            j += 1
        avg_rank = (i + j) / 2
        score = points * (1 - avg_rank / (n - 1))
        for k in range(i, j + 1):
            result[sorted_items[k]["name"]] = score
        i = j + 1
    return result


def build_leaderboard(pair_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for report in pair_reports:
        rows.append(
            {
                "name": report["name"],
                "efficiency_raw": report["comparison"]["evolution_efficiency_score_35_linear"],
                "mechanism_raw": report["comparison"]["mechanism_raw"],
                "final_raw": report["comparison"]["final_result_raw"],
            }
        )
    efficiency_points = _rank_points(rows, "efficiency_raw", 35.0)
    mechanism_points = _rank_points(rows, "mechanism_raw", 25.0)
    final_points = _rank_points(rows, "final_raw", 10.0)
    for row in rows:
        name = row["name"]
        row["evolution_efficiency_rank_score_35"] = efficiency_points.get(name, 0.0)
        row["evolution_mechanism_rank_score_25"] = mechanism_points.get(name, 0.0)
        row["final_result_rank_score_10"] = final_points.get(name, 0.0)
        row["total_rank_score_70"] = (
            row["evolution_efficiency_rank_score_35"]
            + row["evolution_mechanism_rank_score_25"]
            + row["final_result_rank_score_10"]
        )
    return sorted(rows, key=lambda x: x["total_rank_score_70"], reverse=True)


def _load_pairs(args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.pairs:
        data = json.loads(Path(args.pairs).read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("--pairs JSON must be a list")
        return data
    if args.baseline_pred and args.baseline_traj and args.evolved_pred and args.evolved_traj:
        return [
            {
                "name": args.name,
                "baseline_pred": str(args.baseline_pred),
                "baseline_traj": str(args.baseline_traj),
                "evolved_pred": str(args.evolved_pred),
                "evolved_traj": str(args.evolved_traj),
            }
        ]
    return []


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Unified SimpleVQA/2Wiki metrics and ranking.")
    p.add_argument("--pred", type=Path, default=None, help="Single run prediction JSONL.")
    p.add_argument("--traj-dir", type=Path, default=None, help="Single run trajectory directory.")
    p.add_argument("--baseline-pred", type=Path, default=None)
    p.add_argument("--baseline-traj", type=Path, default=None)
    p.add_argument("--evolved-pred", type=Path, default=None)
    p.add_argument("--evolved-traj", type=Path, default=None)
    p.add_argument("--pairs", type=Path, default=None, help="JSON list of baseline/evolved run pairs.")
    p.add_argument("--name", default="submission")
    p.add_argument("--case-limit", type=int, default=200)
    p.add_argument("--output", type=Path, default=None)
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    if args.pred and args.traj_dir:
        summary, _ = summarize_run(
            args.pred,
            args.traj_dir,
            name=args.name,
            case_limit=args.case_limit,
        )
        report: dict[str, Any] = {"single_run": asdict(summary)}
    else:
        pairs = _load_pairs(args)
        if not pairs:
            raise SystemExit(
                "Provide either --pred/--traj-dir, --baseline-* + --evolved-*, or --pairs."
            )
        pair_reports = []
        for pair in pairs:
            name = pair.get("name", "submission")
            baseline_summary, _ = summarize_run(
                Path(pair["baseline_pred"]),
                Path(pair["baseline_traj"]),
                name=f"{name}_baseline",
                case_limit=args.case_limit,
            )
            evolved_summary, _ = summarize_run(
                Path(pair["evolved_pred"]),
                Path(pair["evolved_traj"]),
                name=f"{name}_evolved",
                case_limit=args.case_limit,
            )
            pair_reports.append(
                {
                    "name": name,
                    "comparison": compare_runs(baseline_summary, evolved_summary),
                }
            )
        report = {
            "case_limit": args.case_limit,
            "pairs": pair_reports,
            "leaderboard": build_leaderboard(pair_reports),
        }

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
