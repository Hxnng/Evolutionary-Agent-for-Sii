"""
Meta-Harness Evaluator
=======================

评估候选harness的性能。
包装现有task_runner.py的调用接口，支持并行评估。
"""

import base64
import json
import os
import re
import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
import importlib.util

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import ScoreWeights, DEFAULT_CONFIG


@dataclass
class TaskResult:
    """单个任务的评估结果

    字段对应 task_runner.run_task 的实际返回值：
    {"task_id", "instruction", "answer", "pred", "success", "steps",
     "trajectory_path", "summary"}
    """
    task_id: str
    instruction: str
    image: Optional[str]
    answer: str          # gold answer
    pred: str            # predicted answer
    correct: bool        # success flag from task_runner
    steps: int           # agent loop steps
    tool_call_count: int # tool calls made
    elapsed_time: float
    trajectory_path: str
    summary: Dict = field(default_factory=dict)


@dataclass
class HarnessScores:
    """harness的整体分数"""
    accuracy: float
    avg_steps: float           # 平均 agent loop 步数
    avg_tool_calls: float      # 平均工具调用次数
    avg_elapsed_time: float    # 平均耗时
    total_score: float
    task_results: List[TaskResult]


class Evaluator:
    """评估器"""

    def __init__(self, config=None):
        self.config = config or DEFAULT_CONFIG
        self.logger = logging.getLogger("meta_harness.evaluator")

    def _load_task_runner(self):
        """动态加载task_runner模块"""
        task_runner_path = Path(__file__).parent / "task_runner.py"
        spec = importlib.util.spec_from_file_location("task_runner", task_runner_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    # ------------------------------------------------------------------
    # Dataset reading helpers (ported from evaluate.py / evaluate_2wiki.py)
    # ------------------------------------------------------------------

    @staticmethod
    def _read_json_records(path: Path) -> List[Dict]:
        """Read JSON or JSONL file into a list of dicts."""
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
            for key in ("data", "examples", "records", "test", "validation"):
                if isinstance(data.get(key), list):
                    return data[key]
        raise ValueError(f"Unsupported JSON dataset structure: {path}")

    @staticmethod
    def _read_parquet_file(path: Path) -> List[Dict]:
        """Read a parquet file into a list of dicts."""
        try:
            import pyarrow.parquet as pq
        except ImportError as exc:
            raise RuntimeError(
                "Reading parquet requires pyarrow. Install: python -m pip install pyarrow"
            ) from exc
        return pq.read_table(path).to_pylist()

    @staticmethod
    def _field(row: Dict, names: tuple, default: str = "") -> str:
        """Extract first matching field from a row."""
        for name in names:
            value = row.get(name)
            if value is not None:
                return str(value)
        return default

    @classmethod
    def _build_simplevqa_instruction(cls, row: Dict) -> str:
        """Build instruction for a SimpleVQA-style record."""
        instruction = cls._field(row, ("instruction", "question", "query", "input", "prompt"))
        if not instruction:
            raise ValueError(f"Record has no instruction/question field: {row.keys()}")
        image_description = cls._field(row, ("image_description", "caption", "description"), "")
        if image_description:
            instruction = f"{instruction}\n\n图像描述参考：{image_description}"
        return instruction

    @staticmethod
    def _image_to_b64(image: str, image_root: Optional[Path]) -> Optional[str]:
        """Convert local image path to base64, or return None for URLs."""
        if not image or image.startswith(("http://", "https://", "data:")):
            return None
        path = Path(image)
        if not path.is_absolute() and image_root is not None:
            path = image_root / image
        if not path.exists():
            return None
        return base64.b64encode(path.read_bytes()).decode("utf-8")

    @staticmethod
    def _compact_text(text: str) -> str:
        return re.sub(r"\s+", " ", str(text or "")).strip()

    @classmethod
    def _format_context(cls, context: Any, max_context_chars: int = 12000) -> str:
        """Format HuggingFace 2Wiki context into a compact block."""
        if not context:
            return ""
        parts: List[str] = []
        if isinstance(context, dict):
            titles = context.get("title") or []
            sentences = context.get("sentences") or []
            for title_i, title in enumerate(titles):
                title_text = cls._compact_text(title)
                sent_list = sentences[title_i] if title_i < len(sentences) else []
                parts.append(f"[{title_i + 1}] {title_text}")
                for sent_i, sentence in enumerate(sent_list):
                    parts.append(f"  ({sent_i}) {cls._compact_text(sentence)}")
        elif isinstance(context, list):
            for title_i, item in enumerate(context):
                if isinstance(item, (list, tuple)) and item:
                    title = cls._compact_text(item[0])
                    sent_list = item[1] if len(item) > 1 and isinstance(item[1], list) else []
                elif isinstance(item, dict):
                    title = cls._compact_text(item.get("title", f"doc_{title_i}"))
                    sent_list = item.get("sentences", [])
                else:
                    title = f"doc_{title_i}"
                    sent_list = [str(item)]
                parts.append(f"[{title_i + 1}] {title}")
                for sent_i, sentence in enumerate(sent_list):
                    parts.append(f"  ({sent_i}) {cls._compact_text(sentence)}")
        else:
            parts.append(cls._compact_text(str(context)))
        text = "\n".join(parts)
        if max_context_chars and len(text) > max_context_chars:
            return text[:max_context_chars].rstrip() + "\n...[context truncated]"
        return text

    @classmethod
    def _build_wiki2_instruction(cls, row: Dict) -> str:
        """Build instruction for a 2WikiMultihopQA record."""
        question = str(row.get("question") or row.get("instruction") or "").strip()
        if not question:
            raise ValueError(f"2Wiki record has no question field: {row.keys()}")
        context = cls._format_context(row.get("context"))
        return (
            "请回答下面的 2WikiMultihopQA 多跳问题。\n"
            "要求：只基于给定候选上下文进行推理；必要时可以调用搜索或浏览器工具核验；"
            "最终答案必须写成 <answer>答案</answer>，不要输出多余解释。\n\n"
            f"Question: {question}\n\n"
            f"Candidate context:\n{context}"
        )

    def _load_dataset(self, dataset_name: str, size: int) -> List[Dict]:
        """加载数据集，返回 task dict 列表（可直接传给 task_runner.run_task）。

        每个 task dict 包含:
            id, instruction, answer, image (optional), image_url (optional),
            image_b64 (optional), evolved
        """
        if dataset_name == "simplevqa":
            return self._load_simplevqa(size)
        elif dataset_name in ("wiki2", "2wiki"):
            return self._load_wiki2(size)
        else:
            self.logger.error(f"Unknown dataset: {dataset_name}")
            return []

    def _load_simplevqa(self, size: int) -> List[Dict]:
        """加载 SimpleVQA 数据集"""
        data_path = Path(self.config.data.simplevqa_path)
        image_root = Path(self.config.data.simplevqa_image_root) if hasattr(self.config.data, 'simplevqa_image_root') else (data_path if data_path.is_dir() else data_path.parent)

        # Find dataset files
        if data_path.is_dir():
            candidates = sorted(data_path.glob("*.jsonl")) + sorted(data_path.glob("*.json"))
            if not candidates:
                self.logger.error(f"No JSON/JSONL files found in {data_path}")
                return []
            data_file = candidates[0]
        else:
            data_file = data_path

        rows = self._read_json_records(data_file)[:size]
        tasks: List[Dict] = []
        for i, row in enumerate(rows):
            instruction = self._build_simplevqa_instruction(row)
            answer = self._field(row, ("answer", "gold", "label", "target"))
            image = self._field(row, ("image", "image_path", "image_url", "img"), "")
            image_url = image if image.startswith(("http://", "https://", "data:")) else ""
            image_b64 = self._image_to_b64(image, image_root)
            task_id = row.get("index", row.get("data_id", row.get("id", i)))
            tasks.append({
                "id": f"simplevqa_{task_id}",
                "instruction": instruction,
                "answer": answer,
                "image": image,
                "image_url": image_url,
                "image_b64": image_b64,
                "evolved": True,
            })
        self.logger.info(f"Loaded {len(tasks)} SimpleVQA tasks from {data_file}")
        return tasks

    def _load_wiki2(self, size: int) -> List[Dict]:
        """加载 2WikiMultihopQA 数据集"""
        data_path = Path(self.config.data.wiki2_path)

        # Find dataset files (parquet or json)
        if data_path.is_dir():
            parquet_files = sorted(data_path.glob("**/*.parquet"))
            json_files = sorted(data_path.glob("**/*.json")) + sorted(data_path.glob("**/*.jsonl"))
            if parquet_files:
                rows = []
                for pf in parquet_files:
                    rows.extend(self._read_parquet_file(pf))
            elif json_files:
                rows = []
                for jf in json_files:
                    rows.extend(self._read_json_records(jf))
            else:
                self.logger.error(f"No dataset files found in {data_path}")
                return []
        elif data_path.suffix.lower() == ".parquet":
            rows = self._read_parquet_file(data_path)
        else:
            rows = self._read_json_records(data_path)

        rows = rows[:size]
        tasks: List[Dict] = []
        for i, row in enumerate(rows):
            instruction = self._build_wiki2_instruction(row)
            answer = str(row.get("answer") or "")
            task_id = row.get("id", i)
            tasks.append({
                "id": f"wiki2_{task_id}",
                "instruction": instruction,
                "answer": answer,
                "evolved": True,
            })
        self.logger.info(f"Loaded {len(tasks)} 2Wiki tasks")
        return tasks

    def _evaluate_single_task(self, task_runner_module, harness_code: str,
                             task: Dict, task_id: str) -> TaskResult:
        """评估单个任务

        Args:
            task_runner_module: 动态加载的 task_runner 模块
            harness_code:       候选 harness 代码（当前未使用，保留供未来动态加载）
            task:               任务 dict，可直接传给 task_runner.run_task(task=...)
            task_id:            任务标识符
        """
        # NOTE: harness_code 当前未使用，保留供未来动态加载候选 harness 代码
        start_time = time.time()

        # 确保 task dict 中的 id 与传入的 task_id 一致
        task_copy = dict(task)
        task_copy["id"] = task_id

        try:
            # 调用 task_runner.run_task，签名: run_task(task: dict, ...) -> dict
            # 返回值: {"task_id", "instruction", "answer", "pred", "success",
            #          "steps", "trajectory_path", "summary"}
            result = task_runner_module.run_task(task_copy)

            elapsed_time = time.time() - start_time
            summary = result.get("summary", {})

            return TaskResult(
                task_id=result.get("task_id", task_id),
                instruction=result.get("instruction", task.get("instruction", "")),
                image=task.get("image"),
                answer=task.get("answer", ""),
                pred=result.get("pred", ""),
                correct=bool(result.get("success", False)),
                steps=result.get("steps", 0),
                tool_call_count=summary.get("tool_call_count", 0),
                elapsed_time=elapsed_time,
                trajectory_path=result.get("trajectory_path", ""),
                summary=summary,
            )
        except Exception as e:
            self.logger.error(f"Task {task_id} failed: {e}")
            elapsed_time = time.time() - start_time
            return TaskResult(
                task_id=task_id,
                instruction=task.get("instruction", ""),
                image=task.get("image"),
                answer=task.get("answer", ""),
                pred="",
                correct=False,
                steps=0,
                tool_call_count=0,
                elapsed_time=elapsed_time,
                trajectory_path="",
                summary={},
            )

    def _calculate_scores(self, task_results: List[TaskResult]) -> HarnessScores:
        """计算整体分数"""
        if not task_results:
            return HarnessScores(
                accuracy=0.0,
                avg_steps=0.0,
                avg_tool_calls=0.0,
                avg_elapsed_time=0.0,
                total_score=0.0,
                task_results=[]
            )

        # 计算各项指标
        correct_count = sum(1 for r in task_results if r.correct)
        accuracy = correct_count / len(task_results)

        avg_steps = sum(r.steps for r in task_results) / len(task_results)
        avg_tool_calls = sum(r.tool_call_count for r in task_results) / len(task_results)
        avg_elapsed_time = sum(r.elapsed_time for r in task_results) / len(task_results)

        # 计算总分（按权重）
        # task_runner 不返回 token 统计，token_weight 暂用 steps 的倒数替代
        weights = self.config.scores
        total_score = (
            accuracy * weights.accuracy_weight +
            (1.0 / (1.0 + avg_steps)) * weights.reasoning_weight +  # 步数越少越好
            (1.0 / (1.0 + avg_steps)) * weights.token_weight +  # token_weight: 无token统计，用steps替代
            (1.0 / (1.0 + avg_tool_calls)) * weights.tool_weight +  # 工具调用越少越好
            (1.0 / (1.0 + avg_elapsed_time)) * weights.time_weight +  # 时间越短越好
            accuracy * weights.final_accuracy_weight
        )

        return HarnessScores(
            accuracy=accuracy,
            avg_steps=avg_steps,
            avg_tool_calls=avg_tool_calls,
            avg_elapsed_time=avg_elapsed_time,
            total_score=total_score,
            task_results=task_results
        )

    def evaluate(self, harness_code: str, dataset_name: str,
                size: int, candidate_id: str = "test") -> HarnessScores:
        """评估harness"""
        self.logger.info(f"Evaluating harness on {dataset_name} with {size} tasks")

        # 加载数据集
        tasks = self._load_dataset(dataset_name, size)
        if not tasks:
            self.logger.error(f"Failed to load dataset {dataset_name}")
            return HarnessScores(
                accuracy=0.0, avg_steps=0.0,
                avg_tool_calls=0.0, avg_elapsed_time=0.0,
                total_score=0.0, task_results=[]
            )

        # 加载task_runner
        task_runner_module = self._load_task_runner()

        # 执行评估
        task_results = []
        for i, task in enumerate(tasks[:size]):
            task_id = f"{candidate_id}_{dataset_name}_{i}"
            self.logger.info(f"Evaluating task {i+1}/{size}: {task_id}")

            result = self._evaluate_single_task(
                task_runner_module, harness_code, task, task_id
            )
            task_results.append(result)

        # 计算分数
        scores = self._calculate_scores(task_results)

        self.logger.info(f"Evaluation complete: accuracy={scores.accuracy:.3f}, "
                        f"total_score={scores.total_score:.3f}")

        return scores

    def evaluate_parallel(self, harness_code: str, dataset_name: str,
                         size: int, threads: int = 10,
                         candidate_id: str = "test") -> HarnessScores:
        """并行评估harness"""
        self.logger.info(f"Evaluating harness in parallel on {dataset_name} "
                        f"with {size} tasks using {threads} threads")

        # 加载数据集
        tasks = self._load_dataset(dataset_name, size)
        if not tasks:
            self.logger.error(f"Failed to load dataset {dataset_name}")
            return HarnessScores(
                accuracy=0.0, avg_steps=0.0,
                avg_tool_calls=0.0, avg_elapsed_time=0.0,
                total_score=0.0, task_results=[]
            )

        # 加载task_runner
        task_runner_module = self._load_task_runner()

        # 并行执行评估
        task_results = []
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {}
            for i, task in enumerate(tasks[:size]):
                task_id = f"{candidate_id}_{dataset_name}_{i}"
                future = executor.submit(
                    self._evaluate_single_task,
                    task_runner_module, harness_code, task, task_id
                )
                futures[future] = (task_id, task)

            for future in as_completed(futures):
                task_id, task = futures[future]
                try:
                    result = future.result()
                    task_results.append(result)
                    self.logger.info(f"Completed task {task_id}: "
                                   f"correct={result.correct}, "
                                   f"steps={result.steps}")
                except Exception as e:
                    self.logger.error(f"Task {task_id} failed in future: {e}")
                    # 将失败的任务也加入结果，避免accuracy被高估
                    task_results.append(TaskResult(
                        task_id=task_id,
                        instruction=task.get("instruction", ""),
                        image=task.get("image"),
                        answer=task.get("answer", ""),
                        pred="",
                        correct=False,
                        steps=0,
                        tool_call_count=0,
                        elapsed_time=0.0,
                        trajectory_path="",
                        summary={},
                    ))

        # 计算分数
        scores = self._calculate_scores(task_results)

        self.logger.info(f"Parallel evaluation complete: accuracy={scores.accuracy:.3f}, "
                        f"total_score={scores.total_score:.3f}")

        return scores

    def evaluate_both_datasets(self, harness_code: str, size: int,
                              threads: int = 10,
                              candidate_id: str = "test") -> Dict[str, HarnessScores]:
        """在两个数据集上评估harness"""
        results = {}

        # 评估SimpleVQA
        simplevqa_size = min(size, self.config.data.simplevqa_eval_size)
        results["simplevqa"] = self.evaluate_parallel(
            harness_code, "simplevqa", simplevqa_size, threads,
            f"{candidate_id}_simplevqa"
        )

        # 评估2Wiki
        wiki2_size = min(size, self.config.data.wiki2_eval_size)
        results["wiki2"] = self.evaluate_parallel(
            harness_code, "wiki2", wiki2_size, threads,
            f"{candidate_id}_wiki2"
        )

        # 计算综合分数
        simplevqa_scores = results["simplevqa"]
        wiki2_scores = results["wiki2"]

        # 综合分数 = 两个数据集分数的平均
        combined_accuracy = (simplevqa_scores.accuracy + wiki2_scores.accuracy) / 2
        combined_total_score = (simplevqa_scores.total_score + wiki2_scores.total_score) / 2

        results["combined"] = HarnessScores(
            accuracy=combined_accuracy,
            avg_steps=(simplevqa_scores.avg_steps + wiki2_scores.avg_steps) / 2,
            avg_tool_calls=(simplevqa_scores.avg_tool_calls + wiki2_scores.avg_tool_calls) / 2,
            avg_elapsed_time=(simplevqa_scores.avg_elapsed_time + wiki2_scores.avg_elapsed_time) / 2,
            total_score=combined_total_score,
            task_results=[]
        )

        return results
