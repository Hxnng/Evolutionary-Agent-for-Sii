"""
Meta-Harness Filesystem Manager
================================

管理候选harness的存储、查询和反馈机制。
每个候选harness一个目录，包含代码、分数、轨迹和推理过程。
"""

import json
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import glob
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CandidateInfo:
    """候选harness信息"""
    candidate_id: str
    harness_path: str
    scores_path: str
    trajectories_dir: str
    reasoning_path: str
    iteration: int
    parent_id: Optional[str] = None
    description: str = ""


class FilesystemManager:
    """文件系统管理器"""

    def __init__(self, base_dir: str = "harnesses"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _is_valid_id(candidate_id: str) -> bool:
        """验证candidate_id是否安全（仅允许字母数字、下划线、连字符）"""
        if not candidate_id or len(candidate_id) > 100:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', candidate_id))

    def _get_candidate_dir(self, candidate_id: str) -> Path:
        """获取候选目录路径"""
        return self.base_dir / candidate_id

    def create_candidate(self, candidate_id: str, iteration: int,
                        parent_id: Optional[str] = None,
                        description: str = "") -> CandidateInfo:
        """创建新的候选目录结构"""
        if not self._is_valid_id(candidate_id):
            raise ValueError(f"无效的candidate_id: {candidate_id}")

        try:
            candidate_dir = self._get_candidate_dir(candidate_id)
            candidate_dir.mkdir(parents=True, exist_ok=True)

            # 创建子目录
            trajectories_dir = candidate_dir / "trajectories"
            trajectories_dir.mkdir(exist_ok=True)

            # 创建文件路径
            harness_path = candidate_dir / "harness.py"
            scores_path = candidate_dir / "scores.json"
            reasoning_path = candidate_dir / "reasoning.txt"

            # 写入元数据
            metadata = {
                "candidate_id": candidate_id,
                "iteration": iteration,
                "parent_id": parent_id,
                "description": description,
                "created_at": str(datetime.now())
            }

            with open(candidate_dir / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            return CandidateInfo(
                candidate_id=candidate_id,
                harness_path=str(harness_path),
                scores_path=str(scores_path),
                trajectories_dir=str(trajectories_dir),
                reasoning_path=str(reasoning_path),
                iteration=iteration,
                parent_id=parent_id,
                description=description
            )
        except OSError as e:
            raise RuntimeError(f"创建候选目录失败: {e}")

    def store_harness_code(self, candidate_id: str, code: str):
        """存储harness代码"""
        if not self._is_valid_id(candidate_id):
            raise ValueError(f"无效的candidate_id: {candidate_id}")

        try:
            harness_path = self._get_candidate_dir(candidate_id) / "harness.py"
            with open(harness_path, "w", encoding="utf-8") as f:
                f.write(code)
        except OSError as e:
            raise RuntimeError(f"存储harness代码失败: {e}")

    def store_scores(self, candidate_id: str, scores: Dict[str, Any]):
        """存储评估分数"""
        if not self._is_valid_id(candidate_id):
            raise ValueError(f"无效的candidate_id: {candidate_id}")

        try:
            scores_path = self._get_candidate_dir(candidate_id) / "scores.json"
            with open(scores_path, "w", encoding="utf-8") as f:
                json.dump(scores, f, ensure_ascii=False, indent=2)
        except OSError as e:
            raise RuntimeError(f"存储分数失败: {e}")

    def store_trajectory(self, candidate_id: str, task_id: str, trajectory: List[Dict]):
        """存储单个任务的轨迹"""
        if not self._is_valid_id(candidate_id):
            raise ValueError(f"无效的candidate_id: {candidate_id}")
        if not self._is_valid_id(task_id):
            raise ValueError(f"无效的task_id: {task_id}")

        try:
            trajectories_dir = self._get_candidate_dir(candidate_id) / "trajectories"
            trajectory_file = trajectories_dir / f"{task_id}.jsonl"

            with open(trajectory_file, "w", encoding="utf-8") as f:
                for step in trajectory:
                    f.write(json.dumps(step, ensure_ascii=False) + "\n")
        except OSError as e:
            raise RuntimeError(f"存储轨迹失败: {e}")

    def store_reasoning(self, candidate_id: str, reasoning: str):
        """存储proposer的推理过程"""
        if not self._is_valid_id(candidate_id):
            raise ValueError(f"无效的candidate_id: {candidate_id}")

        try:
            reasoning_path = self._get_candidate_dir(candidate_id) / "reasoning.txt"
            with open(reasoning_path, "w", encoding="utf-8") as f:
                f.write(reasoning)
        except OSError as e:
            raise RuntimeError(f"存储推理过程失败: {e}")

    def get_candidate_info(self, candidate_id: str) -> Optional[CandidateInfo]:
        """获取候选信息"""
        if not self._is_valid_id(candidate_id):
            raise ValueError(f"无效的candidate_id: {candidate_id}")

        candidate_dir = self._get_candidate_dir(candidate_id)
        if not candidate_dir.exists():
            return None

        metadata_file = candidate_dir / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        else:
            metadata = {}

        return CandidateInfo(
            candidate_id=candidate_id,
            harness_path=str(candidate_dir / "harness.py"),
            scores_path=str(candidate_dir / "scores.json"),
            trajectories_dir=str(candidate_dir / "trajectories"),
            reasoning_path=str(candidate_dir / "reasoning.txt"),
            iteration=metadata.get("iteration", 0),
            parent_id=metadata.get("parent_id"),
            description=metadata.get("description", "")
        )

    def get_harness_code(self, candidate_id: str) -> Optional[str]:
        """获取harness代码"""
        if not self._is_valid_id(candidate_id):
            raise ValueError(f"无效的candidate_id: {candidate_id}")

        try:
            harness_path = self._get_candidate_dir(candidate_id) / "harness.py"
            if harness_path.exists():
                with open(harness_path, "r", encoding="utf-8") as f:
                    return f.read()
            return None
        except OSError as e:
            raise RuntimeError(f"读取harness代码失败: {e}")

    def get_scores(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        """获取评估分数"""
        if not self._is_valid_id(candidate_id):
            raise ValueError(f"无效的candidate_id: {candidate_id}")

        try:
            scores_path = self._get_candidate_dir(candidate_id) / "scores.json"
            if scores_path.exists():
                with open(scores_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            return None
        except (OSError, json.JSONDecodeError) as e:
            raise RuntimeError(f"读取分数失败: {e}")

    def get_trajectory(self, candidate_id: str, task_id: str) -> Optional[List[Dict]]:
        """获取单个任务的轨迹"""
        if not self._is_valid_id(candidate_id):
            raise ValueError(f"无效的candidate_id: {candidate_id}")

        try:
            trajectory_file = self._get_candidate_dir(candidate_id) / "trajectories" / f"{task_id}.jsonl"
            if trajectory_file.exists():
                trajectory = []
                with open(trajectory_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            trajectory.append(json.loads(line))
                return trajectory
            return None
        except (OSError, json.JSONDecodeError) as e:
            raise RuntimeError(f"读取轨迹失败: {e}")

    def get_all_trajectories(self, candidate_id: str) -> Dict[str, List[Dict]]:
        """获取候选的所有轨迹"""
        if not self._is_valid_id(candidate_id):
            raise ValueError(f"无效的candidate_id: {candidate_id}")

        trajectories_dir = self._get_candidate_dir(candidate_id) / "trajectories"
        trajectories = {}

        if trajectories_dir.exists():
            for trajectory_file in trajectories_dir.glob("*.jsonl"):
                task_id = trajectory_file.stem
                trajectories[task_id] = self.get_trajectory(candidate_id, task_id)

        return trajectories

    def get_reasoning(self, candidate_id: str) -> Optional[str]:
        """获取proposer的推理过程"""
        if not self._is_valid_id(candidate_id):
            raise ValueError(f"无效的candidate_id: {candidate_id}")

        try:
            reasoning_path = self._get_candidate_dir(candidate_id) / "reasoning.txt"
            if reasoning_path.exists():
                with open(reasoning_path, "r", encoding="utf-8") as f:
                    return f.read()
            return None
        except OSError as e:
            raise RuntimeError(f"读取推理过程失败: {e}")

    def list_candidates(self) -> List[str]:
        """列出所有候选ID"""
        try:
            candidates = []
            for item in self.base_dir.iterdir():
                if item.is_dir() and (item / "harness.py").exists():
                    candidates.append(item.name)
            return sorted(candidates)
        except OSError as e:
            logger.error(f"列出候选目录失败: {e}")
            return []

    def get_all_candidates_info(self) -> List[CandidateInfo]:
        """获取所有候选的信息"""
        candidates = []
        for candidate_id in self.list_candidates():
            info = self.get_candidate_info(candidate_id)
            if info:
                candidates.append(info)
        return candidates

    def get_candidate_summary(self, candidate_id: str) -> Dict[str, Any]:
        """获取候选摘要（用于proposer上下文）"""
        if not self._is_valid_id(candidate_id):
            raise ValueError(f"无效的candidate_id: {candidate_id}")

        info = self.get_candidate_info(candidate_id)
        scores = self.get_scores(candidate_id)

        summary = {
            "candidate_id": candidate_id,
            "iteration": info.iteration if info else 0,
            "parent_id": info.parent_id if info else None,
            "description": info.description if info else "",
            "scores": scores or {}
        }

        return summary

    def get_all_summaries(self) -> List[Dict[str, Any]]:
        """获取所有候选摘要"""
        summaries = []
        for candidate_id in self.list_candidates():
            summary = self.get_candidate_summary(candidate_id)
            summaries.append(summary)
        return summaries

    def delete_candidate(self, candidate_id: str):
        """删除候选目录"""
        if not self._is_valid_id(candidate_id):
            raise ValueError(f"无效的candidate_id: {candidate_id}")

        try:
            candidate_dir = self._get_candidate_dir(candidate_id)
            if candidate_dir.exists():
                shutil.rmtree(candidate_dir)
        except OSError as e:
            raise RuntimeError(f"删除候选目录失败: {e}")

    def clear_all(self):
        """清空所有候选"""
        if self.base_dir.exists():
            logger.warning(f"清空所有候选目录: {self.base_dir}")
            shutil.rmtree(self.base_dir)
            self.base_dir.mkdir(parents=True, exist_ok=True)
            logger.info("所有候选目录已清空")
