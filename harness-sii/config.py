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

    # Generator配置
    #generator_api_key: str = "tp-cjeqnl3h4ekv8c1oot1s6pzp0x20yq886hs5d6x6e94f83qb"
    generator_base_url: str = "http://localhost:8000/v1"
    generator_model: str = "Qwen3.5-9B"

    # Reflector配置
    #reflector_api_key: str = "tp-cjeqnl3h4ekv8c1oot1s6pzp0x20yq886hs5d6x6e94f83qb"
    reflector_base_url: str = "http://localhost:8001/v1"
    reflector_model: str = "Qwen3-32B"


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


@dataclass
class DataConfig:
    """数据配置"""
    simplevqa_path: str = "data/simpleVQA/simpleVQA_final_modified.json"
    simplevqa_image_root: str = "data/simpleVQA/simpleVQA_datasets"
    wiki2_path: str = "data/2wiki"

    simplevqa_eval_size: int = 100  # SimpleVQA评估条数
    wiki2_eval_size: int = 100  # 2Wiki评估条数

    # 分阶段评估使用的子集
    simplevqa_subset_sizes: Optional[List[int]] = None
    wiki2_subset_sizes: Optional[List[int]] = None

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
    token_weight: float = 5.0  # Token优化（task_runner暂无token统计，evaluator中用steps替代）
    reasoning_weight: float = 5.0  # 推理轮数优化
    tool_weight: float = 5.0  # 工具调用优化
    time_weight: float = 5.0  # 推理时间优化

    # 最终结果（10分）
    final_accuracy_weight: float = 10.0  # 最终准确率


@dataclass
class MetaHarnessConfig:
    """Meta-Harness主配置"""
    api: Optional[APIConfig] = None
    search: Optional[SearchConfig] = None
    data: Optional[DataConfig] = None
    scores: Optional[ScoreWeights] = None

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
