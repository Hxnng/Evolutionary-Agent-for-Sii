"""
Meta-Harness Evaluator
=======================

评估候选harness的性能。
直接使用harness-sii中的evaluate.py函数，确保数据加载逻辑一致。
"""

import json
import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

# 添加harness-sii目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "harness-sii"))

from config import ScoreWeights, DEFAULT_CONFIG
from evaluate import _read_records, _field, _build_instruction, _image_to_b64, _image_to_path, run_dataset


@dataclass
class TaskResult:
    """单个任务的评估结果"""
    task_id: str
    instruction: str
    image: Optional[str]
    answer: str
    pred: str
    correct: bool
    steps: int
    tool_call_count: int
    elapsed_time: float
    trajectory_path: str
    summary: Dict = field(default_factory=dict)


@dataclass
class HarnessScores:
    """harness的整体分数"""
    accuracy: float
    avg_steps: float
    avg_tool_calls: float
    avg_elapsed_time: float
    total_score: float
    task_results: List[TaskResult]


class Evaluator:
    """评估器 - 直接使用harness-sii的evaluate.py"""
    
    def __init__(self, config=None):
        self.config = config or DEFAULT_CONFIG
        self.logger = logging.getLogger("meta_harness.evaluator")
    
    def evaluate_both_datasets(self, harness_code: str, size: int,
                              threads: int = 10, 
                              candidate_id: str = "test") -> Dict[str, HarnessScores]:
        """在两个数据集上评估harness"""
        results = {}
        
        # 评估SimpleVQA
        simplevqa_size = min(size, self.config.data.simplevqa_eval_size)
        results["simplevqa"] = self._evaluate_single_dataset(
            harness_code, "simplevqa", simplevqa_size, threads, 
            f"{candidate_id}_simplevqa"
        )
        
        # 评估2Wiki
        wiki2_size = min(size, self.config.data.wiki2_eval_size)
        results["wiki2"] = self._evaluate_single_dataset(
            harness_code, "wiki2", wiki2_size, threads,
            f"{candidate_id}_wiki2"
        )
        
        # 计算综合分数
        simplevqa_scores = results["simplevqa"]
        wiki2_scores = results["wiki2"]
        
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
    
    def _evaluate_single_dataset(self, harness_code: str, dataset_name: str,
                                size: int, threads: int,
                                candidate_id: str) -> HarnessScores:
        """评估单个数据集"""
        # 使用harness-sii的run_dataset函数
        output_path = Path(f"/tmp/{candidate_id}_predictions.jsonl")
        traj_dir = Path(f"/tmp/{candidate_id}_trajectories")

        # 获取模型配置
        model_name = self.config.api.generator_model
        llm_base_url = self.config.api.generator_base_url

        try:
            metrics = run_dataset(
                dataset_path=Path(self.config.data.simplevqa_path if dataset_name == "simplevqa" else self.config.data.wiki2_path),
                output_path=output_path,
                trajectory_dir=traj_dir,
                image_root=Path(self.config.data.simplevqa_image_root) if dataset_name == "simplevqa" else None,
                limit=size,
                split_name=dataset_name,
                evolved=True,
                model_name=model_name,
                llm_base_url=llm_base_url,
                workers=threads,
            )
            
            # 读取结果并计算分数
            task_results = []
            if output_path.exists():
                with open(output_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            record = json.loads(line)
                            task_results.append(TaskResult(
                                task_id=record.get("task_id", ""),
                                instruction=record.get("instruction", ""),
                                image=record.get("image", ""),
                                answer=record.get("answer", ""),
                                pred=record.get("pred", ""),
                                correct=record.get("success", False),
                                steps=record.get("steps", 0),
                                tool_call_count=record.get("tool_call_count", 0),
                                elapsed_time=record.get("elapsed_sec", 0),
                                trajectory_path=record.get("trajectory_path", ""),
                            ))
            
            # 计算分数
            accuracy = metrics.get("accuracy", 0.0)
            avg_steps = sum(r.steps for r in task_results) / len(task_results) if task_results else 0
            avg_tool_calls = sum(r.tool_call_count for r in task_results) / len(task_results) if task_results else 0
            avg_elapsed_time = sum(r.elapsed_time for r in task_results) / len(task_results) if task_results else 0
            
            # 计算总分
            weights = self.config.scores
            total_score = (
                accuracy * weights.accuracy_weight +
                (1.0 / (1.0 + avg_steps)) * weights.reasoning_weight +
                (1.0 / (1.0 + avg_steps)) * weights.token_weight +
                (1.0 / (1.0 + avg_tool_calls)) * weights.tool_weight +
                (1.0 / (1.0 + avg_elapsed_time)) * weights.time_weight +
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
            
        except Exception as e:
            self.logger.error(f"Evaluation failed for {dataset_name}: {e}")
            return HarnessScores(
                accuracy=0.0, avg_steps=0, avg_tool_calls=0,
                avg_elapsed_time=0.0, total_score=0.0, task_results=[]
            )
