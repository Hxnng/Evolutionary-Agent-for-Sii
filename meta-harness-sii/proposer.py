"""
Meta-Harness Proposer
=====================

使用mimo V2.5 pro作为提案代理，读取文件系统中的先前候选，
理解失败原因，提出新的harness变体。
"""

import json
import logging
import re
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

        # 按准确率排序所有候选
        if candidates:
            candidates_with_scores = []
            candidates_without_scores = []
            for candidate in candidates:
                scores = self.filesystem.get_scores(candidate.candidate_id)
                if scores and "accuracy" in scores:
                    candidates_with_scores.append((candidate, scores))
                else:
                    candidates_without_scores.append(candidate)

            if candidates_with_scores:
                candidates_with_scores.sort(key=lambda x: x[1]["accuracy"], reverse=True)
                best_candidate, best_scores = candidates_with_scores[0]
                worst_candidate, worst_scores = candidates_with_scores[-1]

                # 展示表现最好的候选的详细信息
                context_parts.append(f"\n## 表现最好的候选：{best_candidate.candidate_id}\n")
                context_parts.append(f"分数：{json.dumps(best_scores, ensure_ascii=False)}\n")

                code = self.filesystem.get_harness_code(best_candidate.candidate_id)
                if code:
                    context_parts.append("### 代码\n```python")
                    context_parts.append(code)
                    context_parts.append("```\n")

                reasoning = self.filesystem.get_reasoning(best_candidate.candidate_id)
                if reasoning:
                    context_parts.append("### 推理过程\n")
                    context_parts.append(reasoning)
                    context_parts.append("")

                # 读取表现最好的候选的轨迹数据（采样展示）
                best_trajectories = self.filesystem.get_all_trajectories(best_candidate.candidate_id)
                if best_trajectories:
                    context_parts.append("### 轨迹数据（采样）\n")
                    sample_count = 0
                    for task_id, trajectory in best_trajectories.items():
                        if sample_count >= 3:
                            context_parts.append(f"（共 {len(best_trajectories)} 条轨迹，仅展示前3条）\n")
                            break
                        context_parts.append(f"**任务 {task_id}**：\n```json")
                        # 截断过长的轨迹，避免上下文爆炸
                        trajectory_str = json.dumps(trajectory[:10], ensure_ascii=False, indent=2)
                        if len(trajectory_str) > 3000:
                            trajectory_str = trajectory_str[:3000] + "\n... (截断)"
                        context_parts.append(trajectory_str)
                        context_parts.append("```\n")
                        sample_count += 1

                # 展示表现最差的候选的详细信息（帮助分析失败原因）
                if len(candidates_with_scores) > 1 and worst_candidate.candidate_id != best_candidate.candidate_id:
                    context_parts.append(f"\n## 表现最差的候选：{worst_candidate.candidate_id}\n")
                    context_parts.append(f"分数：{json.dumps(worst_scores, ensure_ascii=False)}\n")

                    worst_code = self.filesystem.get_harness_code(worst_candidate.candidate_id)
                    if worst_code:
                        context_parts.append("### 代码\n```python")
                        context_parts.append(worst_code)
                        context_parts.append("```\n")

                    worst_reasoning = self.filesystem.get_reasoning(worst_candidate.candidate_id)
                    if worst_reasoning:
                        context_parts.append("### 推理过程\n")
                        context_parts.append(worst_reasoning)
                        context_parts.append("")

                    # 读取表现最差的候选的轨迹数据（采样展示）
                    worst_trajectories = self.filesystem.get_all_trajectories(worst_candidate.candidate_id)
                    if worst_trajectories:
                        context_parts.append("### 轨迹数据（采样）\n")
                        sample_count = 0
                        for task_id, trajectory in worst_trajectories.items():
                            if sample_count >= 3:
                                context_parts.append(f"（共 {len(worst_trajectories)} 条轨迹，仅展示前3条）\n")
                                break
                            context_parts.append(f"**任务 {task_id}**：\n```json")
                            trajectory_str = json.dumps(trajectory[:10], ensure_ascii=False, indent=2)
                            if len(trajectory_str) > 3000:
                                trajectory_str = trajectory_str[:3000] + "\n... (截断)"
                            context_parts.append(trajectory_str)
                            context_parts.append("```\n")
                            sample_count += 1

            # 展示无分数的候选（可能是执行失败的）
            if candidates_without_scores:
                context_parts.append("\n## 未完成评估的候选（可能执行失败）\n")
                for candidate in candidates_without_scores:
                    context_parts.append(f"- **{candidate.candidate_id}**：{candidate.description}")

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
                max_completion_tokens=16384,
                temperature=0.8,
                top_p=0.95
            )

            # 校验API响应
            if not response or not response.choices:
                self.logger.error("API response is empty or has no choices")
                return []

            response_text = response.choices[0].message.content
            if not response_text:
                self.logger.error("API response content is empty")
                return []

            # 解析响应
            candidates = self._parse_response(response_text, num_candidates)

            # 将候选代码和推理过程存储到文件系统
            for candidate in candidates:
                candidate_id = candidate.get("id", "")
                if not candidate_id:
                    continue
                try:
                    # 确保候选目录存在
                    self.filesystem.create_candidate(
                        candidate_id=candidate_id,
                        iteration=iteration,
                        description=candidate.get("description", "")
                    )
                    # 存储代码
                    if "code" in candidate:
                        self.filesystem.store_harness_code(candidate_id, candidate["code"])
                    # 存储推理过程
                    if "reasoning" in candidate:
                        self.filesystem.store_reasoning(candidate_id, candidate["reasoning"])
                    self.logger.info(f"Stored candidate {candidate_id} to filesystem")
                except Exception as store_err:
                    self.logger.error(f"Failed to store candidate {candidate_id}: {store_err}")

            self.logger.info(f"Proposed {len(candidates)} candidates")
            return candidates

        except Exception as e:
            self.logger.error(f"Failed to propose candidates: {e}")
            return []

    def _extract_json_from_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        从响应文本中提取JSON，使用多种策略：
        1. 首先尝试匹配 ```json ... ``` 代码块
        2. 然后尝试匹配 ``` ... ``` 代码块
        3. 最后fallback到查找第一个 { 和最后一个 }
        """
        # 策略1: 匹配 ```json ... ``` 代码块
        json_block_pattern = r'```json\s*\n?(.*?)\n?\s*```'
        matches = re.findall(json_block_pattern, response_text, re.DOTALL)
        if matches:
            for match in matches:
                try:
                    return json.loads(match.strip())
                except json.JSONDecodeError:
                    continue

        # 策略2: 匹配 ``` ... ``` 代码块（不指定语言）
        code_block_pattern = r'```\s*\n?(.*?)\n?\s*```'
        matches = re.findall(code_block_pattern, response_text, re.DOTALL)
        if matches:
            for match in matches:
                try:
                    return json.loads(match.strip())
                except json.JSONDecodeError:
                    continue

        # 策略3: fallback - 查找第一个 { 和最后一个 }
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        if json_start != -1 and json_end > 0:
            try:
                return json.loads(response_text[json_start:json_end])
            except json.JSONDecodeError:
                pass

        return None

    def _parse_response(self, response_text: str, num_candidates: int) -> List[Dict[str, Any]]:
        """解析proposer的响应"""
        try:
            data = self._extract_json_from_response(response_text)
            if not data:
                self.logger.error("No JSON found in response")
                return []

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
                max_completion_tokens=16384,
                temperature=0.9,
                top_p=0.95
            )

            # 校验API响应
            if not response or not response.choices:
                self.logger.error("API response is empty or has no choices")
                return []

            response_text = response.choices[0].message.content
            if not response_text:
                self.logger.error("API response content is empty")
                return []

            # 解析响应
            variants = self._parse_initial_population_response(response_text, population_size)

            # 将变体代码和描述存储到文件系统
            for variant in variants:
                variant_id = variant.get("id", "")
                if not variant_id:
                    continue
                try:
                    # 确保候选目录存在
                    self.filesystem.create_candidate(
                        candidate_id=variant_id,
                        iteration=0,  # 初始种群迭代为0
                        description=variant.get("description", "")
                    )
                    # 存储代码
                    if "code" in variant:
                        self.filesystem.store_harness_code(variant_id, variant["code"])
                    # 存储推理过程（使用changes字段）
                    if "changes" in variant:
                        self.filesystem.store_reasoning(variant_id, variant["changes"])
                    self.logger.info(f"Stored initial variant {variant_id} to filesystem")
                except Exception as store_err:
                    self.logger.error(f"Failed to store variant {variant_id}: {store_err}")

            self.logger.info(f"Generated {len(variants)} initial variants")
            return variants

        except Exception as e:
            self.logger.error(f"Failed to generate initial population: {e}")
            return []

    def _parse_initial_population_response(self, response_text: str,
                                          population_size: int) -> List[Dict[str, Any]]:
        """解析初始种群生成的响应"""
        try:
            data = self._extract_json_from_response(response_text)
            if not data:
                self.logger.error("No JSON found in response")
                return []

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

        except Exception as e:
            self.logger.error(f"Failed to parse response: {e}")
            return []
