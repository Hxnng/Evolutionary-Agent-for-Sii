"""
Meta-Harness Evaluator
=======================

评估候选harness的性能。
包装现有task_runner.py的调用接口，支持并行评估。
"""

import json
import os
import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import importlib.util

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import ScoreWeights, DEFAULT_CONFIG


@dataclass
class TaskResult:
    """单个任务的评估结果"""
    task_id: str
    instruction: str
    image: Optional[str]
    answer: str
    pred: str
    correct: bool
    total_tokens: int
    reasoning_turns: int
    tool_calls: int
    failed_tool_calls: int
    elapsed_time: float
    trajectory: List[Dict]


@dataclass
class HarnessScores:
    """harness的整体分数"""
    accuracy: float
    avg_tokens: float
    avg_reasoning_turns: float
    avg_tool_calls: float
    avg_failed_tool_calls: float
    avg_elapsed_time: float
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

    def _load_dataset(self, dataset_name: str, size: int) -> List[Dict]:
        """加载数据集"""
        if dataset_name == "simplevqa":
            data_path = Path(self.config.data.simplevqa_path)
            # 加载SimpleVQA数据集
            # 实现细节取决于数据集格式
            pass
        elif dataset_name == "wiki2":
            data_path = Path(self.config.data.wiki2_path)
            # 加载2Wiki数据集
            # 实现细节取决于数据集格式
            pass
        return []

    def _evaluate_single_task(self, task_runner_module, harness_code: str,
                             task: Dict, task_id: str) -> TaskResult:
        """评估单个任务"""
        start_time = time.time()

        # 动态加载harness代码
        # 这里需要实现harness代码的动态加载和执行
        # 暂时使用task_runner的默认行为

        try:
            # 调用task_runner执行任务
            result = task_runner_module.run_task(
                instruction=task.get("instruction", ""),
                image=task.get("image"),
                task_id=task_id
            )

            elapsed_time = time.time() - start_time

            # 解析结果
            return TaskResult(
                task_id=task_id,
                instruction=task.get("instruction", ""),
                image=task.get("image"),
                answer=task.get("answer", ""),
                pred=result.get("pred", ""),
                correct=self._check_answer(result.get("pred", ""), task.get("answer", "")),
                total_tokens=result.get("total_tokens", 0),
                reasoning_turns=result.get("reasoning_turns", 0),
                tool_calls=result.get("tool_calls", 0),
                failed_tool_calls=result.get("failed_tool_calls", 0),
                elapsed_time=elapsed_time,
                trajectory=result.get("trajectory", [])
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
                total_tokens=0,
                reasoning_turns=0,
                tool_calls=0,
                failed_tool_calls=0,
                elapsed_time=elapsed_time,
                trajectory=[]
            )

    def _check_answer(self, pred: str, answer: str) -> bool:
        """检查答案是否正确"""
        # 简单的字符串匹配，可以根据需要改进
        pred_clean = pred.strip().lower()
        answer_clean = answer.strip().lower()
        return pred_clean == answer_clean

    def _calculate_scores(self, task_results: List[TaskResult]) -> HarnessScores:
        """计算整体分数"""
        if not task_results:
            return HarnessScores(
                accuracy=0.0,
                avg_tokens=0.0,
                avg_reasoning_turns=0.0,
                avg_tool_calls=0.0,
                avg_failed_tool_calls=0.0,
                avg_elapsed_time=0.0,
                total_score=0.0,
                task_results=[]
            )

        # 计算各项指标
        correct_count = sum(1 for r in task_results if r.correct)
        accuracy = correct_count / len(task_results)

        avg_tokens = sum(r.total_tokens for r in task_results) / len(task_results)
        avg_reasoning_turns = sum(r.reasoning_turns for r in task_results) / len(task_results)
        avg_tool_calls = sum(r.tool_calls for r in task_results) / len(task_results)
        avg_failed_tool_calls = sum(r.failed_tool_calls for r in task_results) / len(task_results)
        avg_elapsed_time = sum(r.elapsed_time for r in task_results) / len(task_results)

        # 计算总分（按权重）
        weights = self.config.scores
        total_score = (
            accuracy * weights.accuracy_weight +
            (1.0 / (1.0 + avg_tokens / 1000)) * weights.token_weight +  # Token越少越好
            (1.0 / (1.0 + avg_reasoning_turns)) * weights.reasoning_weight +  # 推理轮数越少越好
            (1.0 / (1.0 + avg_tool_calls)) * weights.tool_weight +  # 工具调用越少越好
            (1.0 / (1.0 + avg_elapsed_time)) * weights.time_weight +  # 时间越短越好
            accuracy * weights.final_accuracy_weight
        )

        return HarnessScores(
            accuracy=accuracy,
            avg_tokens=avg_tokens,
            avg_reasoning_turns=avg_reasoning_turns,
            avg_tool_calls=avg_tool_calls,
            avg_failed_tool_calls=avg_failed_tool_calls,
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
                accuracy=0.0, avg_tokens=0.0, avg_reasoning_turns=0.0,
                avg_tool_calls=0.0, avg_failed_tool_calls=0.0,
                avg_elapsed_time=0.0, total_score=0.0, task_results=[]
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
                accuracy=0.0, avg_tokens=0.0, avg_reasoning_turns=0.0,
                avg_tool_calls=0.0, avg_failed_tool_calls=0.0,
                avg_elapsed_time=0.0, total_score=0.0, task_results=[]
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
                futures[future] = task_id

            for future in as_completed(futures):
                task_id = futures[future]
                try:
                    result = future.result()
                    task_results.append(result)
                    self.logger.info(f"Completed task {task_id}: "
                                   f"correct={result.correct}, "
                                   f"tokens={result.total_tokens}")
                except Exception as e:
                    self.logger.error(f"Task {task_id} failed: {e}")

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
            avg_tokens=(simplevqa_scores.avg_tokens + wiki2_scores.avg_tokens) / 2,
            avg_reasoning_turns=(simplevqa_scores.avg_reasoning_turns + wiki2_scores.avg_reasoning_turns) / 2,
            avg_tool_calls=(simplevqa_scores.avg_tool_calls + wiki2_scores.avg_tool_calls) / 2,
            avg_failed_tool_calls=(simplevqa_scores.avg_failed_tool_calls + wiki2_scores.avg_failed_tool_calls) / 2,
            avg_elapsed_time=(simplevqa_scores.avg_elapsed_time + wiki2_scores.avg_elapsed_time) / 2,
            total_score=combined_total_score,
            task_results=[]
        )

        return results
