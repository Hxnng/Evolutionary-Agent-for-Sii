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
        self.proposer = Proposer(self.config.api, self.filesystem, self.config.search)

        # 搜索状态
        self.current_iteration = 0
        self.top_candidates = []  # Top候选列表（按total_score排序）
        self.best_score = 0.0
        self.patience_counter = 0

        # 优雅中断支持
        self.interrupted = False
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # 加载搜索状态（如果存在）
        self._load_search_state()
        self._load_top_candidates()

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

    def _load_top_candidates(self):
        """加载Top候选列表"""
        pareto_file = Path(self.config.pareto_front_file)
        if pareto_file.exists():
            try:
                with open(pareto_file, "r", encoding="utf-8") as f:
                    self.top_candidates = json.load(f)

                self.logger.info(f"Loaded top candidates with {len(self.top_candidates)} entries")
            except Exception as e:
                self.logger.error(f"Failed to load top candidates: {e}")

    def _save_top_candidates(self):
        """保存Top候选列表"""
        try:
            with open(self.config.pareto_front_file, "w", encoding="utf-8") as f:
                json.dump(self.top_candidates, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save top candidates: {e}")

    def _get_eval_size(self, iteration: int) -> int:
        """获取当前迭代的评估规模"""
        if iteration <= self.config.search.eval_stage_1_iterations:
            return self.config.search.eval_stage_1_size
        elif iteration <= self.config.search.eval_stage_1_iterations + self.config.search.eval_stage_2_iterations:
            return self.config.search.eval_stage_2_size
        else:
            return self.config.search.eval_stage_3_size

    def _update_top_candidates(self, candidate_id: str, scores: Dict[str, HarnessScores]):
        """更新Top候选列表（按total_score排序取Top-10）

        注意：这不是真正的Pareto前沿（多目标支配关系），
        而是按综合分数排序的Top-K列表。
        """
        # 计算综合分数
        combined_scores = scores.get("combined")
        if not combined_scores:
            return

        # 添加到候选列表
        candidate_entry = {
            "candidate_id": candidate_id,
            "iteration": self.current_iteration,
            "accuracy": combined_scores.accuracy,
            "total_score": combined_scores.total_score,
            "avg_steps": combined_scores.avg_steps,
            "avg_tool_calls": combined_scores.avg_tool_calls,
            "avg_elapsed_time": combined_scores.avg_elapsed_time
        }

        self.top_candidates.append(candidate_entry)

        # 按总分排序
        self.top_candidates.sort(key=lambda x: x["total_score"], reverse=True)

        # 只保留前10个
        self.top_candidates = self.top_candidates[:10]

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

        # 确定搜索模式
        proposer_mode = self.config.search.proposer_mode
        if proposer_mode == "mixed":
            proposer_mode = "full" if iteration % 2 == 0 else "module"
        self.logger.info(f"Proposer mode: {proposer_mode}")

        # Proposer提出新候选
        candidates = self.proposer.propose(
            iteration,
            self.config.search.candidates_per_iteration,
            mode=proposer_mode
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

            # 存储代码和模块
            if proposer_mode == "module" and "modules" in candidate:
                # 模块模式：存储各模块文件
                combined_code = self.proposer._combine_module_code(candidate["modules"])
                self.filesystem.store_harness_code(candidate_id, combined_code)
                for mod_name, mod_code in candidate["modules"].items():
                    mod_path = self.filesystem._get_candidate_dir(candidate_id) / mod_name
                    mod_path.write_text(mod_code, encoding="utf-8")
            else:
                # 完整模式：存储完整 task_runner.py
                self.filesystem.store_harness_code(candidate_id, candidate.get("code", ""))

            # 存储推理过程
            self.filesystem.store_reasoning(candidate_id, candidate.get("reasoning", ""))

            # 提取模块文件（如果有）
            module_files = candidate.get("modules", None)

            # 评估候选
            self.logger.info(f"Evaluating candidate {candidate_id} (mode={proposer_mode})...")
            try:
                # 读取 task_runner.py 代码
                harness_code = self.filesystem.get_harness_code(candidate_id) or ""

                scores = self.evaluator.evaluate_both_datasets(
                    harness_code,
                    eval_size,
                    self.config.search.parallel_threads,
                    candidate_id,
                    module_files=module_files
                )
            except Exception as e:
                self.logger.error(f"Evaluation failed for {candidate_id}: {e}")
                continue

            # 存储分数
            scores_dict = {}
            for dataset_name, harness_scores in scores.items():
                scores_dict[dataset_name] = {
                    "accuracy": harness_scores.accuracy,
                    "avg_steps": harness_scores.avg_steps,
                    "avg_tool_calls": harness_scores.avg_tool_calls,
                    "avg_elapsed_time": harness_scores.avg_elapsed_time,
                    "total_score": harness_scores.total_score
                }

            self.filesystem.store_scores(candidate_id, scores_dict)

            # 存储轨迹（从轨迹文件读取）
            for dataset_name, harness_scores in scores.items():
                if harness_scores.task_results:
                    for task_result in harness_scores.task_results:
                        if task_result.trajectory_path:
                            traj_path = Path(task_result.trajectory_path)
                            if traj_path.exists():
                                try:
                                    import json as _json
                                    trajectory = []
                                    with open(traj_path, "r", encoding="utf-8") as tf:
                                        for line in tf:
                                            if line.strip():
                                                trajectory.append(_json.loads(line))
                                    self.filesystem.store_trajectory(
                                        candidate_id,
                                        task_result.task_id,
                                        trajectory
                                    )
                                except Exception as traj_err:
                                    self.logger.warning(f"Failed to store trajectory: {traj_err}")

            # 更新Top候选列表
            self._update_top_candidates(candidate_id, scores)

            # 记录各数据集的单独分数
            for dataset_name, harness_scores in scores.items():
                if harness_scores.task_results:
                    self.logger.info(
                        f"  {dataset_name}: accuracy={harness_scores.accuracy:.3f}, "
                        f"total_score={harness_scores.total_score:.3f}, "
                        f"avg_steps={harness_scores.avg_steps:.1f}, "
                        f"avg_tool_calls={harness_scores.avg_tool_calls:.1f}, "
                        f"avg_elapsed_time={harness_scores.avg_elapsed_time:.2f}s"
                    )

        # 保存搜索状态
        self._save_search_state()
        self._save_top_candidates()

        # 输出当前最佳
        if self.top_candidates:
            best = self.top_candidates[0]
            self.logger.info(f"Current best: {best['candidate_id']} "
                           f"(accuracy={best['accuracy']:.3f}, "
                           f"total_score={best['total_score']:.3f})")

    def run(self, base_harness_code: str):
        """运行Meta-Harness搜索"""
        self.logger.info("Starting Meta-Harness search...")

        # 如果没有初始种群，生成一个
        if not self.filesystem.list_candidates():
            self.generate_initial_population(base_harness_code)

        # 运行迭代
        while not self._should_stop():
            self.run_iteration(self.current_iteration + 1)

        # 输出最终结果
        self.logger.info("Meta-Harness search completed!")
        if self.top_candidates:
            best = self.top_candidates[0]
            self.logger.info(f"Best candidate: {best['candidate_id']}")
            self.logger.info(f"  Accuracy: {best['accuracy']:.3f}")
            self.logger.info(f"  Total score: {best['total_score']:.3f}")
            self.logger.info(f"  Avg steps: {best['avg_steps']:.1f}")
            self.logger.info(f"  Avg tool calls: {best['avg_tool_calls']:.1f}")
            self.logger.info(f"  Avg elapsed time: {best['avg_elapsed_time']:.2f}s")

            # 返回最佳候选的代码
            best_code = self.filesystem.get_harness_code(best['candidate_id'])
            return best_code

        return None

    def get_current_best(self) -> Optional[Dict[str, Any]]:
        """获取当前最佳候选"""
        if self.top_candidates:
            best = self.top_candidates[0]
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
