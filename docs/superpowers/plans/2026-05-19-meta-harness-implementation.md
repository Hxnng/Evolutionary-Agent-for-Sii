# Meta-Harness 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现Meta-Harness外循环搜索系统，自动优化harness配置以提升SimpleVQA和2Wiki任务性能。

**Architecture:** 复制harness-sii到meta-harness-sii，在副本上实现外循环搜索系统。使用mimo V2.5 pro作为proposer，通过文件系统反馈机制让proposer学习先前候选的代码、轨迹和分数，提出更优的harness变体。

**Tech Stack:** Python 3.10+, OpenAI SDK, JSONL, 文件系统反馈

---

## 文件结构

```
meta-harness-sii/
├── [harness-sii的完整副本]
├── meta_loop.py          # 外循环主逻辑
├── proposer.py           # 提案代理（mimo V2.5 pro）
├── evaluator.py          # 评估器
├── filesystem.py         # 文件系统管理
├── config.py             # 配置
├── search_state.json     # 搜索状态
├── pareto_front.json     # 当前Pareto前沿
└── harnesses/            # 候选harness存储目录
```

---

## Task 1: 复制harness-sii到meta-harness-sii

**Files:**
- Create: `meta-harness-sii/` (整个目录)

- [ ] **Step 1: 复制目录**

```bash
cp -r harness-sii meta-harness-sii
```

- [ ] **Step 2: 验证复制成功**

```bash
ls -la meta-harness-sii/
```

Expected: 看到harness-sii的所有文件和目录

- [ ] **Step 3: 删除.env文件（避免冲突）**

```bash
rm meta-harness-sii/.env
```

- [ ] **Step 4: 提交**

```bash
git add meta-harness-sii/
git commit -m "feat: copy harness-sii to meta-harness-sii for Meta-Harness development"
```

---

## Task 2: 实现config.py - 配置管理

**Files:**
- Create: `meta-harness-sii/config.py`

- [ ] **Step 1: 创建配置文件**

```python
"""
Meta-Harness Configuration
===========================

集中管理所有配置项，包括API配置、搜索参数、评估策略等。
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class APIConfig:
    """API配置"""
    # Proposer配置（mimo V2.5 pro）
    proposer_api_key: str = "tp-cjeqnl3h4ekv8c1oot1s6pzp0x20yq886hs5d6x6e94f83qb"
    proposer_base_url: str = "https://token-plan-cn.xiaomimimo.com/v1"
    proposer_model: str = "mimo-v2.5-pro"
    
    # Generator配置（测试环境使用mimo，生产环境替换为Qwen）
    generator_api_key: str = "tp-cjeqnl3h4ekv8c1oot1s6pzp0x20yq886hs5d6x6e94f83qb"
    generator_base_url: str = "https://token-plan-cn.xiaomimimo.com/v1"
    generator_model: str = "mimo-v2.5-pro"
    
    # Reflector配置（测试环境使用mimo，生产环境替换为Qwen）
    reflector_api_key: str = "tp-cjeqnl3h4ekv8c1oot1s6pzp0x20yq886hs5d6x6e94f83qb"
    reflector_base_url: str = "https://token-plan-cn.xiaomimimo.com/v1"
    reflector_model: str = "mimo-v2.5-pro"


@dataclass
class SearchConfig:
    """搜索配置"""
    max_iterations: int = 30  # 最大迭代次数
    candidates_per_iteration: int = 2  # 每次迭代生成的候选数
    initial_population_size: int = 10  # 初始种群大小
    
    # 分阶段评估
    eval_stage_1_size: int = 50  # 探索期评估条数
    eval_stage_2_size: int = 100  # 收敛期评估条数
    eval_stage_3_size: int = 200  # 精调期评估条数（全量）
    
    eval_stage_1_iterations: int = 10  # 探索期迭代次数
    eval_stage_2_iterations: int = 10  # 收敛期迭代次数
    # 精调期：剩余迭代
    
    # 并行评估
    parallel_threads: int = 10  # 并行线程数
    
    # 早停策略
    patience: int = 5  # 连续无改进则停止
    min_improvement: float = 0.01  # 最小改进阈值


@dataclass
class DataConfig:
    """数据配置"""
    simplevqa_path: str = "datasets/simpleVQA"
    wiki2_path: str = "datasets/2WikiMultihopQA"
    
    simplevqa_eval_size: int = 100  # SimpleVQA评估条数
    wiki2_eval_size: int = 100  # 2Wiki评估条数
    
    # 分阶段评估使用的子集
    simplevqa_subset_sizes: List[int] = None
    wiki2_subset_sizes: List[int] = None
    
    def __post_init__(self):
        if self.simplevqa_subset_sizes is None:
            self.simplevqa_subset_sizes = [50, 100, 100]
        if self.wiki2_subset_sizes is None:
            self.wiki2_subset_sizes = [50, 100, 100]


@dataclass
class ScoreWeights:
    """评分权重（按课程评分标准）"""
    # 进化效率（35分）
    accuracy_weight: float = 15.0  # 准确率提升（权重最高，略提高）
    token_weight: float = 5.0  # Token优化
    reasoning_weight: float = 5.0  # 推理轮数优化
    tool_weight: float = 5.0  # 工具调用优化
    time_weight: float = 5.0  # 推理时间优化
    
    # 最终结果（10分）
    final_accuracy_weight: float = 10.0  # 最终准确率


@dataclass
class MetaHarnessConfig:
    """Meta-Harness主配置"""
    api: APIConfig = None
    search: SearchConfig = None
    data: DataConfig = None
    scores: ScoreWeights = None
    
    # 目录配置
    harnesses_dir: str = "harnesses"
    search_state_file: str = "search_state.json"
    pareto_front_file: str = "pareto_front.json"
    
    def __post_init__(self):
        if self.api is None:
            self.api = APIConfig()
        if self.search is None:
            self.search = SearchConfig()
        if self.data is None:
            self.data = DataConfig()
        if self.scores is None:
            self.scores = ScoreWeights()


# 默认配置
DEFAULT_CONFIG = MetaHarnessConfig()
```

- [ ] **Step 2: 测试配置导入**

```bash
cd meta-harness-sii && python -c "from config import DEFAULT_CONFIG; print(DEFAULT_CONFIG)"
```

Expected: 打印配置对象

- [ ] **Step 3: 提交**

```bash
git add meta-harness-sii/config.py
git commit -m "feat: add Meta-Harness configuration management"
```

---

## Task 3: 实现filesystem.py - 文件系统管理

**Files:**
- Create: `meta-harness-sii/filesystem.py`

- [ ] **Step 1: 创建文件系统管理模块**

```python
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
            "created_at": str(pd.Timestamp.now()) if 'pd' in globals() else str(__import__('datetime').datetime.now())
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
```

- [ ] **Step 2: 测试文件系统管理**

```bash
cd meta-harness-sii && python -c "
from filesystem import FilesystemManager
fs = FilesystemManager('test_harnesses')
info = fs.create_candidate('test_001', iteration=0)
fs.store_harness_code('test_001', '# test harness code')
fs.store_scores('test_001', {'accuracy': 0.85})
print('Candidate created:', info.candidate_id)
print('Code:', fs.get_harness_code('test_001'))
print('Scores:', fs.get_scores('test_001'))
fs.clear_all()
print('Test passed!')
"
```

Expected: 打印测试信息，最后显示"Test passed!"

- [ ] **Step 3: 提交**

```bash
git add meta-harness-sii/filesystem.py
git commit -m "feat: add filesystem manager for Meta-Harness candidates"
```

---

## Task 4: 实现evaluator.py - 评估器

**Files:**
- Create: `meta-harness-sii/evaluator.py`

- [ ] **Step 1: 创建评估器模块**

```python
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
```

- [ ] **Step 2: 测试评估器导入**

```bash
cd meta-harness-sii && python -c "from evaluator import Evaluator; print('Evaluator imported')"
```

Expected: 打印"Evaluator imported"

- [ ] **Step 3: 提交**

```bash
git add meta-harness-sii/evaluator.py
git commit -m "feat: add evaluator for Meta-Harness candidates"
```

---

## Task 5: 实现proposer.py - 提案代理

**Files:**
- Create: `meta-harness-sii/proposer.py`

- [ ] **Step 1: 创建提案代理模块**

```python
"""
Meta-Harness Proposer
=====================

使用mimo V2.5 pro作为提案代理，读取文件系统中的先前候选，
理解失败原因，提出新的harness变体。
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from openai import OpenAI

from config import APIConfig, DEFAULT_CONFIG
from filesystem import FilesystemManager, CandidateInfo


class Proposer:
    """提案代理"""
    
    def __init__(self, api_config: APIConfig = None, filesystem: FilesystemManager = None):
        self.api_config = api_config or DEFAULT_CONFIG.api
        self.filesystem = filesystem or FilesystemManager()
        self.logger = logging.getLogger("meta_harness.proposer")
        
        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=self.api_config.proposer_api_key,
            base_url=self.api_config.proposer_base_url
        )
    
    def _build_context(self) -> str:
        """构建proposer的上下文（读取文件系统中的所有先前候选）"""
        context_parts = []
        
        # 添加项目概述
        context_parts.append("""# Meta-Harness 搜索上下文

你是一个harness优化专家。你的任务是分析先前候选的代码、执行轨迹和分数，
理解为什么某些harness表现好而其他表现差，然后提出新的、更优的harness变体。

## 优化目标
- 数据集：SimpleVQA（视觉问答）+ 2WikiMultihopQA（多跳推理问答）
- 评分标准：准确率（权重最高）、Token优化、推理轮数优化、工具调用优化、推理时间优化
- 搜索维度：系统提示词、反思策略、记忆检索、工具调用逻辑、上下文管理

## 关键原则
1. 分析失败原因：不仅要知道"什么失败了"，还要理解"为什么失败"
2. 学习成功经验：分析表现好的harness，理解其成功因素
3. 提出有针对性的改进：基于分析结果，提出具体的修改方案
4. 保持多样性：提出不同方向的变体，避免局部最优
""")
        
        # 添加所有候选的摘要
        candidates = self.filesystem.get_all_candidates_info()
        if candidates:
            context_parts.append("\n## 先前候选概览\n")
            for candidate in candidates:
                summary = self.filesystem.get_candidate_summary(candidate.candidate_id)
                context_parts.append(f"### 候选 {candidate.candidate_id}\n")
                context_parts.append(f"- 迭代：{candidate.iteration}")
                context_parts.append(f"- 描述：{candidate.description}")
                context_parts.append(f"- 分数：{json.dumps(summary.get('scores', {}), ensure_ascii=False)}")
                context_parts.append("")
        
        # 添加表现最好的候选的详细信息
        if candidates:
            # 按准确率排序
            candidates_with_scores = []
            for candidate in candidates:
                scores = self.filesystem.get_scores(candidate.candidate_id)
                if scores and "accuracy" in scores:
                    candidates_with_scores.append((candidate, scores["accuracy"]))
            
            if candidates_with_scores:
                candidates_with_scores.sort(key=lambda x: x[1], reverse=True)
                best_candidate, best_accuracy = candidates_with_scores[0]
                
                context_parts.append(f"\n## 表现最好的候选：{best_candidate.candidate_id}\n")
                context_parts.append(f"准确率：{best_accuracy:.3f}\n")
                
                # 添加代码
                code = self.filesystem.get_harness_code(best_candidate.candidate_id)
                if code:
                    context_parts.append("### 代码\n```python")
                    context_parts.append(code)
                    context_parts.append("```\n")
                
                # 添加推理过程
                reasoning = self.filesystem.get_reasoning(best_candidate.candidate_id)
                if reasoning:
                    context_parts.append("### 推理过程\n")
                    context_parts.append(reasoning)
                    context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _build_prompt(self, context: str, iteration: int, 
                     num_candidates: int) -> str:
        """构建proposer的提示词"""
        prompt = f"""基于以下上下文，请提出{num_candidates}个新的harness变体。

## 当前迭代：{iteration}

## 任务要求
1. 分析先前候选的代码、轨迹和分数
2. 理解成功和失败的原因
3. 提出{num_candidates}个有针对性的改进方案
4. 每个方案应该是完整的、可执行的harness代码

## 输出格式
请以JSON格式输出，包含以下字段：
```json
{{
  "analysis": "对先前候选的分析总结",
  "candidates": [
    {{
      "id": "candidate_1",
      "description": "变体描述",
      "reasoning": "为什么认为这个变体会更好",
      "code": "完整的harness代码"
    }}
  ]
}}
```

## 上下文
{context}

请开始分析和提案。
"""
        return prompt
    
    def propose(self, iteration: int, num_candidates: int = 2) -> List[Dict[str, Any]]:
        """提出新的harness变体"""
        self.logger.info(f"Proposing {num_candidates} candidates for iteration {iteration}")
        
        # 构建上下文
        context = self._build_context()
        
        # 构建提示词
        prompt = self._build_prompt(context, iteration, num_candidates)
        
        # 调用mimo API
        try:
            response = self.client.chat.completions.create(
                model=self.api_config.proposer_model,
                messages=[
                    {"role": "system", "content": "你是一个harness优化专家，擅长分析代码和执行轨迹，提出改进方案。"},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=4096,
                temperature=0.8,
                top_p=0.95
            )
            
            response_text = response.choices[0].message.content
            
            # 解析响应
            candidates = self._parse_response(response_text, num_candidates)
            
            self.logger.info(f"Proposed {len(candidates)} candidates")
            return candidates
            
        except Exception as e:
            self.logger.error(f"Failed to propose candidates: {e}")
            return []
    
    def _parse_response(self, response_text: str, num_candidates: int) -> List[Dict[str, Any]]:
        """解析proposer的响应"""
        try:
            # 尝试从响应中提取JSON
            # 首先找到JSON块
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            
            if json_start == -1 or json_end == 0:
                self.logger.error("No JSON found in response")
                return []
            
            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)
            
            candidates = data.get("candidates", [])
            
            # 确保每个候选都有必要的字段
            parsed_candidates = []
            for i, candidate in enumerate(candidates[:num_candidates]):
                if "code" in candidate:
                    parsed_candidates.append({
                        "id": candidate.get("id", f"candidate_{i+1}"),
                        "description": candidate.get("description", ""),
                        "reasoning": candidate.get("reasoning", ""),
                        "code": candidate["code"]
                    })
            
            return parsed_candidates
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Failed to parse response: {e}")
            return []
    
    def generate_initial_population(self, base_harness_code: str, 
                                   population_size: int = 10) -> List[Dict[str, Any]]:
        """生成初始种群"""
        self.logger.info(f"Generating initial population of {population_size} candidates")
        
        prompt = f"""基于以下基础harness代码，请生成{population_size}个不同的变体。

## 基础harness代码
```python
{base_harness_code}
```

## 变体要求
1. 每个变体应该在不同方面进行修改：
   - 系统提示词风格
   - 反思策略
   - 记忆检索逻辑
   - 工具调用策略
   - 上下文管理方式
2. 保持核心功能不变，但尝试不同的实现方式
3. 每个变体应该是完整的、可执行的代码

## 输出格式
请以JSON格式输出：
```json
{{
  "variants": [
    {{
      "id": "variant_1",
      "description": "变体描述",
      "changes": "修改了哪些部分",
      "code": "完整的harness代码"
    }}
  ]
}}
```

请生成{population_size}个变体。
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.api_config.proposer_model,
                messages=[
                    {"role": "system", "content": "你是一个代码变体生成专家，擅长基于现有代码创建多样化的变体。"},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=8192,
                temperature=0.9,
                top_p=0.95
            )
            
            response_text = response.choices[0].message.content
            
            # 解析响应
            variants = self._parse_initial_population_response(response_text, population_size)
            
            self.logger.info(f"Generated {len(variants)} initial variants")
            return variants
            
        except Exception as e:
            self.logger.error(f"Failed to generate initial population: {e}")
            return []
    
    def _parse_initial_population_response(self, response_text: str, 
                                          population_size: int) -> List[Dict[str, Any]]:
        """解析初始种群生成的响应"""
        try:
            # 提取JSON
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            
            if json_start == -1 or json_end == 0:
                self.logger.error("No JSON found in response")
                return []
            
            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)
            
            variants = data.get("variants", [])
            
            # 确保每个变体都有必要的字段
            parsed_variants = []
            for i, variant in enumerate(variants[:population_size]):
                if "code" in variant:
                    parsed_variants.append({
                        "id": variant.get("id", f"variant_{i+1}"),
                        "description": variant.get("description", ""),
                        "changes": variant.get("changes", ""),
                        "code": variant["code"]
                    })
            
            return parsed_variants
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Failed to parse response: {e}")
            return []
```

- [ ] **Step 2: 测试proposer导入**

```bash
cd meta-harness-sii && python -c "from proposer import Proposer; print('Proposer imported')"
```

Expected: 打印"Proposer imported"

- [ ] **Step 3: 提交**

```bash
git add meta-harness-sii/proposer.py
git commit -m "feat: add proposer using mimo V2.5 pro"
```

---

## Task 6: 实现meta_loop.py - 外循环主逻辑

**Files:**
- Create: `meta-harness-sii/meta_loop.py`

- [ ] **Step 1: 创建外循环主逻辑**

```python
"""
Meta-Harness Outer Loop
========================

外循环搜索系统，协调proposer和evaluator，实现分阶段评估和断点续跑。
"""

import json
import signal
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from config import MetaHarnessConfig, DEFAULT_CONFIG
from filesystem import FilesystemManager
from evaluator import Evaluator, HarnessScores
from proposer import Proposer


class MetaLoop:
    """Meta-Harness外循环"""
    
    def __init__(self, config: MetaHarnessConfig = None):
        self.config = config or DEFAULT_CONFIG
        self.logger = logging.getLogger("meta_harness.meta_loop")
        
        # 初始化组件
        self.filesystem = FilesystemManager(self.config.harnesses_dir)
        self.evaluator = Evaluator(self.config)
        self.proposer = Proposer(self.config.api, self.filesystem)
        
        # 搜索状态
        self.current_iteration = 0
        self.pareto_front = []  # Pareto前沿
        self.best_score = 0.0
        self.patience_counter = 0
        
        # 优雅中断支持
        self.interrupted = False
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # 加载搜索状态（如果存在）
        self._load_search_state()
    
    def _signal_handler(self, signum, frame):
        """信号处理器，实现优雅中断"""
        self.logger.info(f"Received signal {signum}, stopping gracefully...")
        self.interrupted = True
    
    def _load_search_state(self):
        """加载搜索状态"""
        state_file = Path(self.config.search_state_file)
        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                
                self.current_iteration = state.get("current_iteration", 0)
                self.best_score = state.get("best_score", 0.0)
                self.patience_counter = state.get("patience_counter", 0)
                
                self.logger.info(f"Loaded search state: iteration={self.current_iteration}, "
                               f"best_score={self.best_score:.3f}")
            except Exception as e:
                self.logger.error(f"Failed to load search state: {e}")
    
    def _save_search_state(self):
        """保存搜索状态"""
        state = {
            "current_iteration": self.current_iteration,
            "best_score": self.best_score,
            "patience_counter": self.patience_counter,
            "last_updated": datetime.now().isoformat()
        }
        
        try:
            with open(self.config.search_state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save search state: {e}")
    
    def _load_pareto_front(self):
        """加载Pareto前沿"""
        pareto_file = Path(self.config.pareto_front_file)
        if pareto_file.exists():
            try:
                with open(pareto_file, "r", encoding="utf-8") as f:
                    self.pareto_front = json.load(f)
                
                self.logger.info(f"Loaded Pareto front with {len(self.pareto_front)} candidates")
            except Exception as e:
                self.logger.error(f"Failed to load Pareto front: {e}")
    
    def _save_pareto_front(self):
        """保存Pareto前沿"""
        try:
            with open(self.config.pareto_front_file, "w", encoding="utf-8") as f:
                json.dump(self.pareto_front, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save Pareto front: {e}")
    
    def _get_eval_size(self, iteration: int) -> int:
        """获取当前迭代的评估规模"""
        if iteration <= self.config.search.eval_stage_1_iterations:
            return self.config.search.eval_stage_1_size
        elif iteration <= self.config.search.eval_stage_1_iterations + self.config.search.eval_stage_2_iterations:
            return self.config.search.eval_stage_2_size
        else:
            return self.config.search.eval_stage_3_size
    
    def _update_pareto_front(self, candidate_id: str, scores: Dict[str, HarnessScores]):
        """更新Pareto前沿"""
        # 计算综合分数
        combined_scores = scores.get("combined")
        if not combined_scores:
            return
        
        # 添加到Pareto前沿
        candidate_entry = {
            "candidate_id": candidate_id,
            "iteration": self.current_iteration,
            "accuracy": combined_scores.accuracy,
            "total_score": combined_scores.total_score,
            "avg_tokens": combined_scores.avg_tokens,
            "avg_reasoning_turns": combined_scores.avg_reasoning_turns,
            "avg_tool_calls": combined_scores.avg_tool_calls,
            "avg_elapsed_time": combined_scores.avg_elapsed_time
        }
        
        self.pareto_front.append(candidate_entry)
        
        # 按总分排序
        self.pareto_front.sort(key=lambda x: x["total_score"], reverse=True)
        
        # 只保留前10个
        self.pareto_front = self.pareto_front[:10]
        
        # 更新最佳分数
        if combined_scores.total_score > self.best_score:
            self.best_score = combined_scores.total_score
            self.patience_counter = 0
            self.logger.info(f"New best score: {self.best_score:.3f}")
        else:
            self.patience_counter += 1
    
    def _should_stop(self) -> bool:
        """检查是否应该停止搜索"""
        # 检查中断信号
        if self.interrupted:
            self.logger.info("Search interrupted by user")
            return True
        
        # 检查是否达到最大迭代次数
        if self.current_iteration >= self.config.search.max_iterations:
            self.logger.info(f"Reached maximum iterations ({self.config.search.max_iterations})")
            return True
        
        # 检查早停条件
        if self.patience_counter >= self.config.search.patience:
            self.logger.info(f"No improvement for {self.patience_counter} iterations, stopping early")
            return True
        
        return False
    
    def generate_initial_population(self, base_harness_code: str):
        """生成初始种群"""
        self.logger.info("Generating initial population...")
        
        # 生成初始变体
        variants = self.proposer.generate_initial_population(
            base_harness_code, 
            self.config.search.initial_population_size
        )
        
        if not variants:
            self.logger.error("Failed to generate initial population")
            return
        
        # 存储初始种群
        for i, variant in enumerate(variants):
            candidate_id = f"initial_{i:03d}"
            
            # 创建候选目录
            info = self.filesystem.create_candidate(
                candidate_id, 
                iteration=0,
                description=variant.get("description", "")
            )
            
            # 存储代码
            self.filesystem.store_harness_code(candidate_id, variant["code"])
            
            # 存储推理过程
            reasoning = f"初始种群变体 {i+1}\n"
            reasoning += f"描述：{variant.get('description', '')}\n"
            reasoning += f"修改：{variant.get('changes', '')}\n"
            self.filesystem.store_reasoning(candidate_id, reasoning)
            
            self.logger.info(f"Created initial variant: {candidate_id}")
        
        self.logger.info(f"Generated {len(variants)} initial variants")
    
    def run_iteration(self, iteration: int):
        """运行单次迭代"""
        self.logger.info(f"Starting iteration {iteration}")
        self.current_iteration = iteration
        
        # 获取当前评估规模
        eval_size = self._get_eval_size(iteration)
        self.logger.info(f"Evaluation size: {eval_size}")
        
        # Proposer提出新候选
        candidates = self.proposer.propose(
            iteration, 
            self.config.search.candidates_per_iteration
        )
        
        if not candidates:
            self.logger.warning(f"No candidates proposed for iteration {iteration}")
            return
        
        # 评估每个候选
        for candidate in candidates:
            candidate_id = f"iter{iteration:03d}_{candidate['id']}"
            
            # 创建候选目录
            info = self.filesystem.create_candidate(
                candidate_id,
                iteration=iteration,
                description=candidate.get("description", "")
            )
            
            # 存储代码
            self.filesystem.store_harness_code(candidate_id, candidate["code"])
            
            # 存储推理过程
            self.filesystem.store_reasoning(candidate_id, candidate.get("reasoning", ""))
            
            # 评估候选
            self.logger.info(f"Evaluating candidate {candidate_id}...")
            scores = self.evaluator.evaluate_both_datasets(
                candidate["code"],
                eval_size,
                self.config.search.parallel_threads,
                candidate_id
            )
            
            # 存储分数
            scores_dict = {}
            for dataset_name, harness_scores in scores.items():
                scores_dict[dataset_name] = {
                    "accuracy": harness_scores.accuracy,
                    "avg_tokens": harness_scores.avg_tokens,
                    "avg_reasoning_turns": harness_scores.avg_reasoning_turns,
                    "avg_tool_calls": harness_scores.avg_tool_calls,
                    "avg_failed_tool_calls": harness_scores.avg_failed_tool_calls,
                    "avg_elapsed_time": harness_scores.avg_elapsed_time,
                    "total_score": harness_scores.total_score
                }
            
            self.filesystem.store_scores(candidate_id, scores_dict)
            
            # 存储轨迹
            for dataset_name, harness_scores in scores.items():
                if harness_scores.task_results:
                    for task_result in harness_scores.task_results:
                        self.filesystem.store_trajectory(
                            candidate_id,
                            task_result.task_id,
                            task_result.trajectory
                        )
            
            # 更新Pareto前沿
            self._update_pareto_front(candidate_id, scores)
            
            self.logger.info(f"Candidate {candidate_id} evaluated: "
                           f"accuracy={scores['combined'].accuracy:.3f}, "
                           f"total_score={scores['combined'].total_score:.3f}")
        
        # 保存搜索状态
        self._save_search_state()
        self._save_pareto_front()
        
        # 输出当前最佳
        if self.pareto_front:
            best = self.pareto_front[0]
            self.logger.info(f"Current best: {best['candidate_id']} "
                           f"(accuracy={best['accuracy']:.3f}, "
                           f"total_score={best['total_score']:.3f})")
    
    def run(self, base_harness_code: str):
        """运行Meta-Harness搜索"""
        self.logger.info("Starting Meta-Harness search...")
        
        # 加载Pareto前沿
        self._load_pareto_front()
        
        # 如果没有初始种群，生成一个
        if not self.filesystem.list_candidates():
            self.generate_initial_population(base_harness_code)
        
        # 运行迭代
        while not self._should_stop():
            self.run_iteration(self.current_iteration + 1)
        
        # 输出最终结果
        self.logger.info("Meta-Harness search completed!")
        if self.pareto_front:
            best = self.pareto_front[0]
            self.logger.info(f"Best candidate: {best['candidate_id']}")
            self.logger.info(f"  Accuracy: {best['accuracy']:.3f}")
            self.logger.info(f"  Total score: {best['total_score']:.3f}")
            self.logger.info(f"  Avg tokens: {best['avg_tokens']:.1f}")
            self.logger.info(f"  Avg reasoning turns: {best['avg_reasoning_turns']:.1f}")
            self.logger.info(f"  Avg tool calls: {best['avg_tool_calls']:.1f}")
            self.logger.info(f"  Avg elapsed time: {best['avg_elapsed_time']:.2f}s")
            
            # 返回最佳候选的代码
            best_code = self.filesystem.get_harness_code(best['candidate_id'])
            return best_code
        
        return None
    
    def get_current_best(self) -> Optional[Dict[str, Any]]:
        """获取当前最佳候选"""
        if self.pareto_front:
            best = self.pareto_front[0]
            best_code = self.filesystem.get_harness_code(best['candidate_id'])
            return {
                **best,
                "code": best_code
            }
        return None


def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
    )
    
    # 加载基础harness代码
    base_harness_path = Path(__file__).parent / "task_runner.py"
    if base_harness_path.exists():
        with open(base_harness_path, "r", encoding="utf-8") as f:
            base_harness_code = f.read()
    else:
        print("Error: task_runner.py not found")
        sys.exit(1)
    
    # 创建MetaLoop实例
    meta_loop = MetaLoop()
    
    # 运行搜索
    best_code = meta_loop.run(base_harness_code)
    
    if best_code:
        print("\n" + "="*50)
        print("Best harness code:")
        print("="*50)
        print(best_code[:1000] + "..." if len(best_code) > 1000 else best_code)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 测试meta_loop导入**

```bash
cd meta-harness-sii && python -c "from meta_loop import MetaLoop; print('MetaLoop imported')"
```

Expected: 打印"MetaLoop imported"

- [ ] **Step 3: 提交**

```bash
git add meta-harness-sii/meta_loop.py
git commit -m "feat: add Meta-Harness outer loop main logic"
```

---

## Task 7: 集成测试和验证

**Files:**
- Modify: `meta-harness-sii/meta_loop.py`

- [ ] **Step 1: 创建测试脚本**

```python
"""
Meta-Harness 测试脚本
=====================

测试Meta-Harness系统的各个组件。
"""

import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import DEFAULT_CONFIG
from filesystem import FilesystemManager
from evaluator import Evaluator
from proposer import Proposer
from meta_loop import MetaLoop


def test_config():
    """测试配置"""
    print("Testing config...")
    config = DEFAULT_CONFIG
    print(f"  Proposer model: {config.api.proposer_model}")
    print(f"  Max iterations: {config.search.max_iterations}")
    print(f"  Parallel threads: {config.search.parallel_threads}")
    print("  Config test passed!")


def test_filesystem():
    """测试文件系统"""
    print("\nTesting filesystem...")
    fs = FilesystemManager("test_harnesses")
    
    # 创建测试候选
    info = fs.create_candidate("test_001", iteration=0, description="Test candidate")
    fs.store_harness_code("test_001", "# Test harness code")
    fs.store_scores("test_001", {"accuracy": 0.85, "total_score": 25.5})
    
    # 读取测试
    code = fs.get_harness_code("test_001")
    scores = fs.get_scores("test_001")
    
    assert code == "# Test harness code", f"Code mismatch: {code}"
    assert scores["accuracy"] == 0.85, f"Score mismatch: {scores}"
    
    # 清理
    fs.clear_all()
    print("  Filesystem test passed!")


def test_proposer():
    """测试proposer导入"""
    print("\nTesting proposer...")
    try:
        proposer = Proposer()
        print("  Proposer imported successfully")
        print("  Proposer test passed!")
    except Exception as e:
        print(f"  Proposer test failed: {e}")


def test_evaluator():
    """测试evaluator导入"""
    print("\nTesting evaluator...")
    try:
        evaluator = Evaluator()
        print("  Evaluator imported successfully")
        print("  Evaluator test passed!")
    except Exception as e:
        print(f"  Evaluator test failed: {e}")


def test_meta_loop():
    """测试meta_loop导入"""
    print("\nTesting meta_loop...")
    try:
        meta_loop = MetaLoop()
        print("  MetaLoop imported successfully")
        print("  MetaLoop test passed!")
    except Exception as e:
        print(f"  MetaLoop test failed: {e}")


def main():
    """运行所有测试"""
    print("="*50)
    print("Meta-Harness Component Tests")
    print("="*50)
    
    test_config()
    test_filesystem()
    test_proposer()
    test_evaluator()
    test_meta_loop()
    
    print("\n" + "="*50)
    print("All tests passed!")
    print("="*50)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行测试**

```bash
cd meta-harness-sii && python test_meta_harness.py
```

Expected: 所有测试通过

- [ ] **Step 3: 提交**

```bash
git add meta-harness-sii/test_meta_harness.py
git commit -m "feat: add Meta-Harness integration test script"
```

---

## Task 8: 创建启动脚本和文档

**Files:**
- Create: `meta-harness-sii/run_meta_harness.sh`
- Create: `meta-harness-sii/README.md`

- [ ] **Step 1: 创建启动脚本**

```bash
#!/bin/bash
# Meta-Harness 启动脚本

set -e

echo "Starting Meta-Harness search..."
echo "================================"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found"
    exit 1
fi

# 检查依赖
echo "Checking dependencies..."
pip install -q openai

# 运行Meta-Harness
echo "Running Meta-Harness..."
cd "$(dirname "$0")"
python3 meta_loop.py

echo "================================"
echo "Meta-Harness search completed!"
```

- [ ] **Step 2: 创建README文档**

```markdown
# Meta-Harness

基于Meta-Harness论文方法的harness自动优化系统。

## 快速开始

### 1. 安装依赖

```bash
pip install openai
```

### 2. 运行Meta-Harness

```bash
./run_meta_harness.sh
```

或者直接运行Python脚本：

```bash
python meta_loop.py
```

### 3. 查看结果

搜索完成后，结果保存在：
- `harnesses/` - 所有候选harness
- `pareto_front.json` - Pareto前沿
- `search_state.json` - 搜索状态

## 配置

配置在 `config.py` 中，包括：
- API配置（mimo V2.5 pro）
- 搜索参数（迭代次数、评估规模等）
- 数据集路径
- 评分权重

## 目录结构

```
meta-harness-sii/
├── meta_loop.py          # 外循环主逻辑
├── proposer.py           # 提案代理
├── evaluator.py          # 评估器
├── filesystem.py         # 文件系统管理
├── config.py             # 配置
├── test_meta_harness.py  # 测试脚本
├── run_meta_harness.sh   # 启动脚本
├── harnesses/            # 候选harness存储
├── search_state.json     # 搜索状态
└── pareto_front.json     # Pareto前沿
```

## 评分标准

按课程评分权重：
- 准确率提升（权重最高）
- Token优化
- 推理轮数优化
- 工具调用优化
- 推理时间优化

## 注意事项

1. API key已写入源码，无需设置环境变量
2. 测试环境使用mimo-v2.5-pro替代Qwen模型
3. 支持断点续跑，可随时中断并恢复
4. 分阶段评估：50→100→200条
```

- [ ] **Step 3: 设置脚本权限**

```bash
chmod +x meta-harness-sii/run_meta_harness.sh
```

- [ ] **Step 4: 提交**

```bash
git add meta-harness-sii/run_meta_harness.sh meta-harness-sii/README.md
git commit -m "feat: add startup script and documentation"
```

---

## 总结

本实现计划包含8个任务：

1. 复制harness-sii到meta-harness-sii
2. 实现config.py - 配置管理
3. 实现filesystem.py - 文件系统管理
4. 实现evaluator.py - 评估器
5. 实现proposer.py - 提案代理
6. 实现meta_loop.py - 外循环主逻辑
7. 集成测试和验证
8. 创建启动脚本和文档

每个任务都包含详细的步骤、完整的代码和测试命令。按照TDD原则，先写测试，再实现功能。

**执行方式：**

**1. Subagent-Driven（推荐）** - 每个任务分派一个独立的subagent，任务间进行review，快速迭代

**2. Inline Execution** - 在当前会话中执行任务，批量执行并设置检查点

**选择哪种方式？**
