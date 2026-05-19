"""
Meta-Harness Proposer
=====================

使用mimo V2.5 pro作为提案代理，读取文件系统中的先前候选，
理解失败原因，提出新的harness变体。

支持两种搜索模式：
- full: 生成完整 task_runner.py 替换
- module: 生成/修改子模块（preprocessor.py, postprocessor.py 等）
- mixed: 混合模式，交替使用 full 和 module
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from openai import OpenAI

from config import APIConfig, SearchConfig, DEFAULT_CONFIG
from filesystem import FilesystemManager, CandidateInfo


class Proposer:
    """提案代理"""

    def __init__(self, api_config: APIConfig = None, filesystem: FilesystemManager = None,
                 search_config: SearchConfig = None):
        self.api_config = api_config or DEFAULT_CONFIG.api
        self.filesystem = filesystem or FilesystemManager()
        self.search_config = search_config or DEFAULT_CONFIG.search
        self.logger = logging.getLogger("meta_harness.proposer")

        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=self.api_config.proposer_api_key,
            base_url=self.api_config.proposer_base_url
        )

        # 读取当前 task_runner.py 源码（作为上下文）
        self.base_dir = Path(__file__).parent
        self._task_runner_source = self._read_source("task_runner.py")
        self._preprocessor_source = self._read_source("preprocessor.py")
        self._postprocessor_source = self._read_source("postprocessor.py")

    def _read_source(self, filename: str) -> str:
        """读取源码文件"""
        path = self.base_dir / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _build_context(self, mode: str = "full") -> str:
        """构建proposer的上下文"""
        context_parts = []

        # 添加项目概述
        context_parts.append(f"""# Meta-Harness 搜索上下文

你是一个harness优化专家。你的任务是分析先前候选的代码、执行轨迹和分数，
理解为什么某些harness表现好而其他表现差，然后提出新的、更优的harness变体。

## 优化目标
- 数据集：SimpleVQA（视觉问答）+ 2WikiMultihopQA（多跳推理问答）
- 评分标准：准确率（权重最高）、Token优化、推理轮数优化、工具调用优化、推理时间优化
- 搜索维度：系统提示词、反思策略、记忆检索、工具调用逻辑、上下文管理、**架构变更**

## 当前搜索模式：{mode}

## 关键原则
1. 分析失败原因：不仅要知道"什么失败了"，还要理解"为什么失败"
2. 学习成功经验：分析表现好的harness，理解其成功因素
3. 提出有针对性的改进：基于分析结果，提出具体的修改方案
4. 保持多样性：提出不同方向的变体，避免局部最优
""")

        # 添加当前源码上下文
        if mode == "full":
            context_parts.append("\n## 当前 task_runner.py 源码\n```python")
            # 截断过长的源码
            src = self._task_runner_source
            if len(src) > 8000:
                src = src[:8000] + "\n# ... (截断)"
            context_parts.append(src)
            context_parts.append("```\n")
        elif mode == "module":
            context_parts.append("\n## 当前可插拔模块\n")
            if self._preprocessor_source:
                context_parts.append("### preprocessor.py\n```python")
                context_parts.append(self._preprocessor_source)
                context_parts.append("```\n")
            if self._postprocessor_source:
                context_parts.append("### postprocessor.py\n```python")
                context_parts.append(self._postprocessor_source)
                context_parts.append("```\n")
            context_parts.append("""## 模块接口说明

preprocessor.py 需要实现：
```python
def preprocess_question(instruction: str, client, model_name: str, image_url: str = "") -> str:
    # 返回分析结果字符串，注入到 system prompt
```

postprocessor.py 需要实现：
```python
def postprocess_answer(instruction: str, raw_answer: str, client, model_name: str) -> str:
    # 返回精炼后的答案字符串
```

task_runner.py 中已预留钩子，会自动导入并调用这些模块。
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
                        trajectory_str = json.dumps(trajectory[:10], ensure_ascii=False, indent=2)
                        if len(trajectory_str) > 3000:
                            trajectory_str = trajectory_str[:3000] + "\n... (截断)"
                        context_parts.append(trajectory_str)
                        context_parts.append("```\n")
                        sample_count += 1

                # 展示表现最差的候选的详细信息
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

            # 展示无分数的候选
            if candidates_without_scores:
                context_parts.append("\n## 未完成评估的候选（可能执行失败）\n")
                for candidate in candidates_without_scores:
                    context_parts.append(f"- **{candidate.candidate_id}**：{candidate.description}")

        return "\n".join(context_parts)

    def _build_prompt(self, context: str, iteration: int,
                      num_candidates: int, mode: str) -> str:
        """构建proposer的提示词"""
        if mode == "full":
            return self._build_full_prompt(context, iteration, num_candidates)
        else:
            return self._build_module_prompt(context, iteration, num_candidates)

    def _build_full_prompt(self, context: str, iteration: int,
                           num_candidates: int) -> str:
        """构建完整 task_runner.py 替换模式的提示词"""
        return f"""基于以下上下文，请提出{num_candidates}个新的harness变体。

## 当前迭代：{iteration}

## 任务要求
1. 分析先前候选的代码、轨迹和分数
2. 理解成功和失败的原因
3. 提出{num_candidates}个有针对性的改进方案
4. 每个方案应该是完整的、可执行的 task_runner.py 代码

## 架构变更维度
你可以从以下方面进行架构级修改：
- **添加问题分析器**：在 agent 循环前添加 LLM 调用分析问题类型、关键实体、搜索策略
- **添加答案精炼器**：在 agent 循环后添加 LLM 调用验证和精炼答案
- **修改工具调用策略**：改变工具选择逻辑、重试策略、并发调用
- **修改上下文管理**：改变消息历史压缩、记忆检索策略
- **修改系统提示词**：优化指令、添加领域知识、调整输出格式要求
- **添加新的工具**：引入新的工具或组合现有工具

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
      "changes": "具体修改了哪些部分",
      "code": "完整的 task_runner.py 代码"
    }}
  ]
}}
```

## 上下文
{context}

请开始分析和提案。
"""

    def _build_module_prompt(self, context: str, iteration: int,
                             num_candidates: int) -> str:
        """构建模块模式的提示词"""
        allowed = self.search_config.allowed_modules or ["preprocessor.py", "postprocessor.py"]
        allowed_str = ", ".join(allowed)

        return f"""基于以下上下文，请提出{num_candidates}个新的子模块变体。

## 当前迭代：{iteration}

## 允许修改的模块
{allowed_str}

## 任务要求
1. 分析先前候选的轨迹和分数
2. 理解成功和失败的原因
3. 提出{num_candidates}个有针对性的模块改进方案
4. 每个方案修改一个或多个子模块

## 模块优化维度
- **问题分析器 (preprocessor.py)**：
  - 改进问题类型分类逻辑
  - 优化搜索关键词生成策略
  - 添加图像分析能力
  - 针对不同问题类型定制分析模板
  - 添加难度评估和策略推荐

- **答案精炼器 (postprocessor.py)**：
  - 改进答案格式化逻辑
  - 添加多源交叉验证
  - 优化答案截断和精简策略
  - 添加置信度评估

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
      "changes": "具体修改了哪些模块的哪些部分",
      "modules": {{
        "preprocessor.py": "完整的模块代码（如果修改了此模块）",
        "postprocessor.py": "完整的模块代码（如果修改了此模块）"
      }}
    }}
  ]
}}
```

## 上下文
{context}

请开始分析和提案。
"""

    def propose(self, iteration: int, num_candidates: int = 2,
                mode: Optional[str] = None) -> List[Dict[str, Any]]:
        """提出新的harness变体

        Args:
            iteration: 当前迭代次数
            num_candidates: 候选数量
            mode: 搜索模式 "full" / "module" / None(使用配置)
        """
        if mode is None:
            mode = self.search_config.proposer_mode
            if mode == "mixed":
                # 交替使用 full 和 module
                mode = "full" if iteration % 2 == 0 else "module"

        self.logger.info(f"Proposing {num_candidates} candidates for iteration {iteration} (mode={mode})")

        # 构建上下文
        context = self._build_context(mode)

        # 构建提示词
        prompt = self._build_prompt(context, iteration, num_candidates, mode)

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
            candidates = self._parse_response(response_text, num_candidates, mode)

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
                    # 存储代码（full 模式存储 task_runner.py，module 模式存储主模块）
                    if mode == "full" and "code" in candidate:
                        self.filesystem.store_harness_code(candidate_id, candidate["code"])
                    elif mode == "module" and "modules" in candidate:
                        # 将模块代码合并到一个 harness.py 中
                        combined = self._combine_module_code(candidate["modules"])
                        self.filesystem.store_harness_code(candidate_id, combined)
                        # 单独存储各模块文件
                        for mod_name, mod_code in candidate["modules"].items():
                            mod_path = self.filesystem._get_candidate_dir(candidate_id) / mod_name
                            mod_path.write_text(mod_code, encoding="utf-8")
                    # 存储推理过程
                    if "reasoning" in candidate:
                        self.filesystem.store_reasoning(candidate_id, candidate["reasoning"])
                    # 存储搜索模式
                    metadata_path = self.filesystem._get_candidate_dir(candidate_id) / "metadata.json"
                    if metadata_path.exists():
                        import json as _json
                        meta = _json.loads(metadata_path.read_text(encoding="utf-8"))
                        meta["proposer_mode"] = mode
                        metadata_path.write_text(_json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

                    self.logger.info(f"Stored candidate {candidate_id} to filesystem")
                except Exception as store_err:
                    self.logger.error(f"Failed to store candidate {candidate_id}: {store_err}")

            self.logger.info(f"Proposed {len(candidates)} candidates")
            return candidates

        except Exception as e:
            self.logger.error(f"Failed to propose candidates: {e}")
            return []

    def _combine_module_code(self, modules: Dict[str, str]) -> str:
        """将多个模块代码合并为一个文件（用于存储）"""
        parts = ["# Meta-Harness Generated Module Code\n"]
        for name, code in modules.items():
            parts.append(f"\n# === {name} ===\n")
            parts.append(code)
        return "\n".join(parts)

    def _extract_json_from_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """从响应文本中提取JSON"""
        # 策略1: 匹配 ```json ... ``` 代码块
        json_block_pattern = r'```json\s*\n?(.*?)\n?\s*```'
        matches = re.findall(json_block_pattern, response_text, re.DOTALL)
        if matches:
            for match in matches:
                try:
                    return json.loads(match.strip())
                except json.JSONDecodeError:
                    continue

        # 策略2: 匹配 ``` ... ``` 代码块
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

    def _parse_response(self, response_text: str, num_candidates: int,
                        mode: str) -> List[Dict[str, Any]]:
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
                if mode == "full":
                    if "code" in candidate:
                        parsed_candidates.append({
                            "id": candidate.get("id", f"candidate_{i+1}"),
                            "description": candidate.get("description", ""),
                            "reasoning": candidate.get("reasoning", ""),
                            "changes": candidate.get("changes", ""),
                            "code": candidate["code"]
                        })
                elif mode == "module":
                    if "modules" in candidate and candidate["modules"]:
                        parsed_candidates.append({
                            "id": candidate.get("id", f"candidate_{i+1}"),
                            "description": candidate.get("description", ""),
                            "reasoning": candidate.get("reasoning", ""),
                            "changes": candidate.get("changes", ""),
                            "modules": candidate["modules"]
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
{base_harness_code[:8000]}
```

## 变体要求
1. 每个变体应该在不同方面进行修改：
   - 系统提示词风格
   - 反思策略
   - 记忆检索逻辑
   - 工具调用策略
   - 上下文管理方式
   - **添加问题分析器**（在 agent 循环前分析问题类型和关键实体）
   - **添加答案精炼器**（在 agent 循环后验证答案）
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
                        iteration=0,
                        description=variant.get("description", "")
                    )
                    # 存储代码
                    if "code" in variant:
                        self.filesystem.store_harness_code(variant_id, variant["code"])
                    # 存储推理过程
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
