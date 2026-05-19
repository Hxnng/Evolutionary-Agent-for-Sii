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
