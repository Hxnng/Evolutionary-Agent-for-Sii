"""
Meta-Harness 测试脚本
=====================

测试Meta-Harness系统的各个组件。
"""

import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import DEFAULT_CONFIG, MetaHarnessConfig, APIConfig, SearchConfig
from filesystem import FilesystemManager
from evaluator import Evaluator
from proposer import Proposer
from meta_loop import MetaLoop


def test_config():
    """测试配置"""
    print("Testing config...")
    config = DEFAULT_CONFIG

    # 断言：配置对象结构正确
    assert config.api is not None, "API config should not be None"
    assert config.search is not None, "Search config should not be None"
    assert config.data is not None, "Data config should not be None"
    assert config.scores is not None, "Scores config should not be None"

    # 断言：API配置默认值正确
    assert config.api.proposer_model == "mimo-v2.5-pro", f"Unexpected proposer model: {config.api.proposer_model}"
    assert config.api.generator_model == "mimo-v2.5-pro", f"Unexpected generator model: {config.api.generator_model}"
    assert config.api.reflector_model == "mimo-v2.5-pro", f"Unexpected reflector model: {config.api.reflector_model}"

    # 断言：搜索配置默认值正确
    assert config.search.max_iterations == 30, f"Unexpected max_iterations: {config.search.max_iterations}"
    assert config.search.parallel_threads == 10, f"Unexpected parallel_threads: {config.search.parallel_threads}"
    assert config.search.patience == 5, f"Unexpected patience: {config.search.patience}"
    assert config.search.candidates_per_iteration == 2, f"Unexpected candidates_per_iteration: {config.search.candidates_per_iteration}"

    # 断言：自定义配置可正常创建
    custom_config = MetaHarnessConfig(api=APIConfig(proposer_model="custom-model"))
    assert custom_config.api.proposer_model == "custom-model", "Custom config not applied"
    assert custom_config.search is not None, "Default search config should be auto-created"

    print(f"  Proposer model: {config.api.proposer_model}")
    print(f"  Max iterations: {config.search.max_iterations}")
    print(f"  Parallel threads: {config.search.parallel_threads}")
    print("  Config test passed!")


def test_filesystem():
    """测试文件系统"""
    print("\nTesting filesystem...")
    fs = FilesystemManager("test_harnesses")

    try:
        # 创建测试候选
        info = fs.create_candidate("test_001", iteration=0, description="Test candidate")
        assert info.candidate_id == "test_001", f"Candidate ID mismatch: {info.candidate_id}"
        assert info.iteration == 0, f"Iteration mismatch: {info.iteration}"
        assert info.description == "Test candidate", f"Description mismatch: {info.description}"
        assert info.parent_id is None, f"Parent ID should be None: {info.parent_id}"

        # 存储和读取代码
        fs.store_harness_code("test_001", "# Test harness code")
        code = fs.get_harness_code("test_001")
        assert code == "# Test harness code", f"Code mismatch: {code}"

        # 存储和读取分数
        fs.store_scores("test_001", {"accuracy": 0.85, "total_score": 25.5})
        scores = fs.get_scores("test_001")
        assert scores["accuracy"] == 0.85, f"Score mismatch: {scores}"
        assert scores["total_score"] == 25.5, f"Total score mismatch: {scores}"

        # 测试get_candidate_info
        retrieved_info = fs.get_candidate_info("test_001")
        assert retrieved_info is not None, "get_candidate_info returned None"
        assert retrieved_info.candidate_id == "test_001", f"Retrieved ID mismatch: {retrieved_info.candidate_id}"
        assert retrieved_info.iteration == 0, f"Retrieved iteration mismatch: {retrieved_info.iteration}"

        # 测试get_candidate_summary
        summary = fs.get_candidate_summary("test_001")
        assert summary["candidate_id"] == "test_001", f"Summary ID mismatch: {summary['candidate_id']}"
        assert summary["scores"]["accuracy"] == 0.85, f"Summary scores mismatch: {summary['scores']}"

        # 测试存储和读取推理过程
        fs.store_reasoning("test_001", "This is a reasoning trace")
        reasoning = fs.get_reasoning("test_001")
        assert reasoning == "This is a reasoning trace", f"Reasoning mismatch: {reasoning}"

        # 测试list_candidates
        candidates = fs.list_candidates()
        assert "test_001" in candidates, f"test_001 not in candidates list: {candidates}"

        # 测试创建带parent_id的候选
        info2 = fs.create_candidate("test_002", iteration=1, parent_id="test_001", description="Child candidate")
        assert info2.parent_id == "test_001", f"Parent ID mismatch: {info2.parent_id}"
        assert info2.iteration == 1, f"Iteration mismatch: {info2.iteration}"

        # 测试存储和读取轨迹
        trajectory = [
            {"step": 1, "action": "search", "result": "found"},
            {"step": 2, "action": "answer", "result": "42"}
        ]
        fs.store_trajectory("test_001", "task_001", trajectory)
        retrieved_traj = fs.get_trajectory("test_001", "task_001")
        assert retrieved_traj is not None, "Trajectory should not be None"
        assert len(retrieved_traj) == 2, f"Trajectory length mismatch: {len(retrieved_traj)}"
        assert retrieved_traj[0]["step"] == 1, f"First step mismatch: {retrieved_traj[0]}"

        # 测试get_all_trajectories
        all_trajectories = fs.get_all_trajectories("test_001")
        assert "task_001" in all_trajectories, f"task_001 not in all_trajectories: {all_trajectories.keys()}"

        # 测试不存在的候选返回None
        assert fs.get_harness_code("nonexistent") is None, "Nonexistent code should be None"
        assert fs.get_scores("nonexistent") is None, "Nonexistent scores should be None"
        assert fs.get_candidate_info("nonexistent") is None, "Nonexistent info should be None"

        # 测试删除候选
        fs.delete_candidate("test_002")
        assert fs.get_candidate_info("test_002") is None, "Deleted candidate should return None"

        # 测试无效ID
        try:
            fs.create_candidate("invalid/id", iteration=0)
            assert False, "Should have raised ValueError for invalid ID"
        except ValueError:
            pass  # expected

        print("  Filesystem test passed!")
    finally:
        # 确保清理，无论测试是否成功
        fs.clear_all()


def test_proposer():
    """测试proposer导入"""
    print("\nTesting proposer...")
    proposer = Proposer()
    assert proposer is not None, "Proposer instance should not be None"
    print("  Proposer imported successfully")
    print("  Proposer test passed!")


def test_evaluator():
    """测试evaluator导入"""
    print("\nTesting evaluator...")
    evaluator = Evaluator()
    assert evaluator is not None, "Evaluator instance should not be None"
    print("  Evaluator imported successfully")
    print("  Evaluator test passed!")


def test_meta_loop():
    """测试meta_loop导入"""
    print("\nTesting meta_loop...")
    meta_loop = MetaLoop()
    assert meta_loop is not None, "MetaLoop instance should not be None"
    print("  MetaLoop imported successfully")
    print("  MetaLoop test passed!")


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
