"""
Meta-Harness Filesystem Manager
================================

管理候选harness的存储、查询和反馈机制。
每个候选harness一个目录，包含代码、分数、轨迹和推理过程。
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import glob
from datetime import datetime


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

    def _get_candidate_dir(self, candidate_id: str) -> Path:
        """获取候选目录路径"""
        return self.base_dir / candidate_id

    def create_candidate(self, candidate_id: str, iteration: int,
                        parent_id: Optional[str] = None,
                        description: str = "") -> CandidateInfo:
        """创建新的候选目录结构"""
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

    def store_harness_code(self, candidate_id: str, code: str):
        """存储harness代码"""
        harness_path = self._get_candidate_dir(candidate_id) / "harness.py"
        with open(harness_path, "w", encoding="utf-8") as f:
            f.write(code)

    def store_scores(self, candidate_id: str, scores: Dict[str, Any]):
        """存储评估分数"""
        scores_path = self._get_candidate_dir(candidate_id) / "scores.json"
        with open(scores_path, "w", encoding="utf-8") as f:
            json.dump(scores, f, ensure_ascii=False, indent=2)

    def store_trajectory(self, candidate_id: str, task_id: str, trajectory: List[Dict]):
        """存储单个任务的轨迹"""
        trajectories_dir = self._get_candidate_dir(candidate_id) / "trajectories"
        trajectory_file = trajectories_dir / f"{task_id}.jsonl"

        with open(trajectory_file, "w", encoding="utf-8") as f:
            for step in trajectory:
                f.write(json.dumps(step, ensure_ascii=False) + "\n")

    def store_reasoning(self, candidate_id: str, reasoning: str):
        """存储proposer的推理过程"""
        reasoning_path = self._get_candidate_dir(candidate_id) / "reasoning.txt"
        with open(reasoning_path, "w", encoding="utf-8") as f:
            f.write(reasoning)

    def get_candidate_info(self, candidate_id: str) -> Optional[CandidateInfo]:
        """获取候选信息"""
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
        harness_path = self._get_candidate_dir(candidate_id) / "harness.py"
        if harness_path.exists():
            with open(harness_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def get_scores(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        """获取评估分数"""
        scores_path = self._get_candidate_dir(candidate_id) / "scores.json"
        if scores_path.exists():
            with open(scores_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def get_trajectory(self, candidate_id: str, task_id: str) -> Optional[List[Dict]]:
        """获取单个任务的轨迹"""
        trajectory_file = self._get_candidate_dir(candidate_id) / "trajectories" / f"{task_id}.jsonl"
        if trajectory_file.exists():
            trajectory = []
            with open(trajectory_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        trajectory.append(json.loads(line))
            return trajectory
        return None

    def get_all_trajectories(self, candidate_id: str) -> Dict[str, List[Dict]]:
        """获取候选的所有轨迹"""
        trajectories_dir = self._get_candidate_dir(candidate_id) / "trajectories"
        trajectories = {}

        if trajectories_dir.exists():
            for trajectory_file in trajectories_dir.glob("*.jsonl"):
                task_id = trajectory_file.stem
                trajectories[task_id] = self.get_trajectory(candidate_id, task_id)

        return trajectories

    def get_reasoning(self, candidate_id: str) -> Optional[str]:
        """获取proposer的推理过程"""
        reasoning_path = self._get_candidate_dir(candidate_id) / "reasoning.txt"
        if reasoning_path.exists():
            with open(reasoning_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def list_candidates(self) -> List[str]:
        """列出所有候选ID"""
        candidates = []
        for item in self.base_dir.iterdir():
            if item.is_dir() and (item / "harness.py").exists():
                candidates.append(item.name)
        return sorted(candidates)

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
        candidate_dir = self._get_candidate_dir(candidate_id)
        if candidate_dir.exists():
            shutil.rmtree(candidate_dir)

    def clear_all(self):
        """清空所有候选"""
        if self.base_dir.exists():
            shutil.rmtree(self.base_dir)
            self.base_dir.mkdir(parents=True, exist_ok=True)
