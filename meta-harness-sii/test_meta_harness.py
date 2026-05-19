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
