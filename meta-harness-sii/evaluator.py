"""
Meta-Harness Evaluator
=======================

评估候选harness的性能。
通过子进程沙盒执行候选代码，支持动态加载 task_runner.py 变体。
"""

import ast
import json
import os
import sys
import time
import shutil
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

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
    """评估器 - 通过子进程沙盒执行候选代码"""

    def __init__(self, config=None):
        self.config = config or DEFAULT_CONFIG
        self.logger = logging.getLogger("meta_harness.evaluator")
        # meta-harness-sii 目录
        self.base_dir = Path(__file__).parent

    def evaluate_both_datasets(self, harness_code: str, size: int,
                               threads: int = 10,
                               candidate_id: str = "test",
                               module_files: Optional[Dict[str, str]] = None
                               ) -> Dict[str, HarnessScores]:
        """在两个数据集上评估harness

        Args:
            harness_code: 完整的 task_runner.py 代码字符串
            size: 评估条数
            threads: 并行线程数
            candidate_id: 候选ID
            module_files: 子模块文件 {filename: content}，如 {"preprocessor.py": "..."}
        """
        results = {}

        # 评估SimpleVQA
        simplevqa_size = min(size, self.config.data.simplevqa_eval_size)
        results["simplevqa"] = self._evaluate_single_dataset(
            harness_code, "simplevqa", simplevqa_size, threads,
            f"{candidate_id}_simplevqa", module_files
        )

        # 评估2Wiki
        wiki2_size = min(size, self.config.data.wiki2_eval_size)
        results["wiki2"] = self._evaluate_single_dataset(
            harness_code, "wiki2", wiki2_size, threads,
            f"{candidate_id}_wiki2", module_files
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

    def _check_syntax(self, code: str, filename: str = "task_runner.py") -> bool:
        """语法检查：ast.parse()"""
        try:
            ast.parse(code, filename=filename)
            return True
        except SyntaxError as e:
            self.logger.error("Syntax error in %s: %s", filename, e)
            return False

    def _prepare_candidate_dir(self, candidate_id: str,
                               harness_code: str,
                               module_files: Optional[Dict[str, str]] = None
                               ) -> Optional[Path]:
        """准备候选代码临时目录

        Returns:
            临时目录路径，失败返回 None
        """
        # 语法检查
        if not self._check_syntax(harness_code, "task_runner.py"):
            return None

        if module_files:
            for fname, content in module_files.items():
                if not self._check_syntax(content, fname):
                    return None

        # 创建临时目录
        temp_dir = Path(tempfile.mkdtemp(prefix=f"candidate_{candidate_id}_"))

        try:
            # 写入 task_runner.py
            (temp_dir / "task_runner.py").write_text(harness_code, encoding="utf-8")

            # 写入子模块
            if module_files:
                for fname, content in module_files.items():
                    (temp_dir / fname).write_text(content, encoding="utf-8")

            # 复制 meta-harness-sii 的依赖模块到临时目录
            # （候选代码可能导入 memory, roles, trajectory, tools 等）
            for dep in ["memory.py", "roles.py", "trajectory.py",
                        "reflection.py", "preprocessor.py", "postprocessor.py"]:
                src = self.base_dir / dep
                if src.exists() and not (temp_dir / dep).exists():
                    shutil.copy2(src, temp_dir / dep)

            # 复制 tools 目录
            tools_src = self.base_dir / "tools"
            tools_dst = temp_dir / "tools"
            if tools_src.exists() and not tools_dst.exists():
                shutil.copytree(tools_src, tools_dst)

            # 复制 memory 目录
            memory_src = self.base_dir / "memory"
            memory_dst = temp_dir / "memory"
            if memory_src.exists() and not memory_dst.exists():
                shutil.copytree(memory_src, memory_dst)

            return temp_dir

        except Exception as e:
            self.logger.error("Failed to prepare candidate dir: %s", e)
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

    def _evaluate_single_dataset(self, harness_code: str, dataset_name: str,
                                 size: int, threads: int,
                                 candidate_id: str,
                                 module_files: Optional[Dict[str, str]] = None
                                 ) -> HarnessScores:
        """评估单个数据集 — 通过子进程沙盒执行"""
        # 准备候选目录
        temp_dir = self._prepare_candidate_dir(candidate_id, harness_code, module_files)

        if temp_dir is None:
            self.logger.warning("Candidate %s failed syntax check, using fallback", candidate_id)
            return self._evaluate_fallback(dataset_name, size, threads, candidate_id)

        # 构建子进程命令
        output_path = temp_dir / "predictions.jsonl"
        traj_dir = temp_dir / "trajectories"

        dataset_path = Path(
            self.config.data.simplevqa_path if dataset_name == "simplevqa"
            else self.config.data.wiki2_path
        )
        image_root = (
            Path(self.config.data.simplevqa_image_root) if dataset_name == "simplevqa"
            else None
        )

        cmd = [
            sys.executable, str(self.base_dir / "evaluate_runner.py"),
            "--dataset", str(dataset_path),
            "--output", str(output_path),
            "--traj-dir", str(traj_dir),
            "--limit", str(size),
            "--split-name", dataset_name,
            "--evolved", "True",
            "--workers", str(threads),
        ]
        if image_root:
            cmd.extend(["--image-root", str(image_root)])
        if self.config.api.generator_model:
            cmd.extend(["--model-name", self.config.api.generator_model])
        if self.config.api.generator_base_url:
            cmd.extend(["--llm-base-url", self.config.api.generator_base_url])

        env = os.environ.copy()
        env["CANDIDATE_DIR"] = str(temp_dir)

        timeout = getattr(self.config.search, "sandbox_timeout", 300)

        try:
            self.logger.info("Evaluating %s in subprocess (timeout=%ds)", candidate_id, timeout)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                cwd=str(self.base_dir),
            )

            if result.returncode != 0:
                self.logger.warning("Subprocess exited with code %d for %s",
                                    result.returncode, candidate_id)
                if result.stderr:
                    self.logger.warning("stderr: %s", result.stderr[:500])
                # 即使返回非0，也可能有部分结果
                if not output_path.exists():
                    return self._evaluate_fallback(dataset_name, size, threads, candidate_id)

            # 解析结果
            scores = self._parse_results(output_path, dataset_name)
            return scores

        except subprocess.TimeoutExpired:
            self.logger.warning("Subprocess timeout for %s", candidate_id)
            return self._evaluate_fallback(dataset_name, size, threads, candidate_id)
        except Exception as e:
            self.logger.error("Subprocess execution failed for %s: %s", candidate_id, e)
            return self._evaluate_fallback(dataset_name, size, threads, candidate_id)
        finally:
            # 清理临时目录
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    def _evaluate_fallback(self, dataset_name: str, size: int,
                           threads: int, candidate_id: str) -> HarnessScores:
        """Fallback：使用原始 task_runner.py 评估"""
        self.logger.info("Fallback: evaluating with original task_runner.py for %s", candidate_id)

        output_path = Path(f"/tmp/{candidate_id}_fallback_predictions.jsonl")
        traj_dir = Path(f"/tmp/{candidate_id}_fallback_trajectories")

        dataset_path = Path(
            self.config.data.simplevqa_path if dataset_name == "simplevqa"
            else self.config.data.wiki2_path
        )
        image_root = (
            Path(self.config.data.simplevqa_image_root) if dataset_name == "simplevqa"
            else None
        )

        cmd = [
            sys.executable, str(self.base_dir / "evaluate_runner.py"),
            "--dataset", str(dataset_path),
            "--output", str(output_path),
            "--traj-dir", str(traj_dir),
            "--limit", str(size),
            "--split-name", dataset_name,
            "--evolved", "True",
            "--workers", str(threads),
        ]
        if image_root:
            cmd.extend(["--image-root", str(image_root)])
        if self.config.api.generator_model:
            cmd.extend(["--model-name", self.config.api.generator_model])
        if self.config.api.generator_base_url:
            cmd.extend(["--llm-base-url", self.config.api.generator_base_url])

        # 不设置 CANDIDATE_DIR，使用原始代码
        env = os.environ.copy()
        env.pop("CANDIDATE_DIR", None)

        timeout = getattr(self.config.search, "sandbox_timeout", 300)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                cwd=str(self.base_dir),
            )
            if output_path.exists():
                return self._parse_results(output_path, dataset_name)
        except Exception as e:
            self.logger.error("Fallback evaluation also failed: %s", e)

        return HarnessScores(
            accuracy=0.0, avg_steps=0, avg_tool_calls=0,
            avg_elapsed_time=0.0, total_score=0.0, task_results=[]
        )

    def _parse_results(self, output_path: Path, dataset_name: str) -> HarnessScores:
        """解析评估输出文件"""
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

        accuracy = sum(1 for r in task_results if r.correct) / len(task_results) if task_results else 0.0
        avg_steps = sum(r.steps for r in task_results) / len(task_results) if task_results else 0
        avg_tool_calls = sum(r.tool_call_count for r in task_results) / len(task_results) if task_results else 0
        avg_elapsed_time = sum(r.elapsed_time for r in task_results) / len(task_results) if task_results else 0

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
