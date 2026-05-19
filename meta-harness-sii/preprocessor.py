"""
问题预处理器（可选模块）
========================

在 agent 主循环之前对问题进行分析，提取关键信息，
为后续推理提供结构化的上下文。

此模块可被 meta-harness proposer 自动修改/替换。
"""

import json
import logging

logger = logging.getLogger("harness.preprocessor")

# 预处理提示词 — proposer 可修改此模板
ANALYSIS_PROMPT = """请分析以下问题，提取关键信息并输出结构化分析。

## 问题
{question}

## 分析要求
请输出以下信息（JSON格式）：
1. **question_type**: 问题类型（事实查询/多跳推理/列表枚举/比较分析/视觉问答/计算推理）
2. **key_entities**: 关键实体列表（人名、地名、组织、时间等）
3. **search_queries**: 推荐的搜索关键词列表（2-3个不同角度的搜索词）
4. **expected_answer_type**: 预期答案类型（人名/数字/日期/地点/列表/布尔值/自由文本）
5. **reasoning_strategy**: 推荐的推理策略（单步搜索/多步推理/对比验证/信息聚合）
6. **difficulty**: 问题难度（easy/medium/hard）

## 输出格式
```json
{{
  "question_type": "...",
  "key_entities": ["...", "..."],
  "search_queries": ["...", "..."],
  "expected_answer_type": "...",
  "reasoning_strategy": "...",
  "difficulty": "..."
}}
```
"""


def preprocess_question(instruction: str, client, model_name: str,
                        image_url: str = "") -> str:
    """分析问题，返回结构化分析结果。

    Args:
        instruction: 用户问题/指令
        client: OpenAI 兼容客户端
        model_name: 模型名称
        image_url: 图片URL（可选）

    Returns:
        格式化的分析结果字符串，注入到 system prompt 中
    """
    try:
        prompt = ANALYSIS_PROMPT.format(question=instruction)

        messages = [{"role": "user", "content": prompt}]
        if image_url:
            messages = [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }]

        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            max_tokens=1000,
            temperature=0.3,
        )

        raw = response.choices[0].message.content or ""

        # 尝试提取 JSON
        analysis = _extract_json(raw)
        if analysis:
            return _format_analysis(analysis)
        return raw.strip()

    except Exception as e:
        logger.warning("preprocess_question failed: %s", e)
        return ""


def postprocess_answer(instruction: str, raw_answer: str,
                       client, model_name: str) -> str:
    """对 agent 输出的答案进行后处理/精炼。

    Args:
        instruction: 原始问题
        raw_answer: agent 的原始输出
        client: OpenAI 兼容客户端
        model_name: 模型名称

    Returns:
        精炼后的答案字符串
    """
    try:
        prompt = f"""请检查以下回答是否准确、简洁，并进行必要的修正。

## 原始问题
{instruction}

## Agent 回答
{raw_answer}

## 要求
1. 如果回答正确且简洁，直接返回原回答
2. 如果回答有明显错误，请修正
3. 如果回答过于冗长，请精简
4. 最终答案用 <answer>...</answer> 包裹

请输出最终答案："""

        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.3,
        )

        return response.choices[0].message.content or raw_answer

    except Exception as e:
        logger.warning("postprocess_answer failed: %s", e)
        return raw_answer


def _extract_json(text: str) -> dict:
    """从文本中提取 JSON 对象"""
    import re
    # 尝试 ```json ... ``` 代码块
    m = re.search(r'```json\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    # 尝试找 { ... }
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > 0:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return {}


def _format_analysis(analysis: dict) -> str:
    """将分析结果格式化为可注入 prompt 的字符串"""
    lines = []
    if analysis.get("question_type"):
        lines.append(f"- 问题类型：{analysis['question_type']}")
    if analysis.get("key_entities"):
        lines.append(f"- 关键实体：{', '.join(analysis['key_entities'])}")
    if analysis.get("search_queries"):
        lines.append(f"- 推荐搜索词：{'; '.join(analysis['search_queries'])}")
    if analysis.get("expected_answer_type"):
        lines.append(f"- 预期答案类型：{analysis['expected_answer_type']}")
    if analysis.get("reasoning_strategy"):
        lines.append(f"- 推荐策略：{analysis['reasoning_strategy']}")
    if analysis.get("difficulty"):
        lines.append(f"- 难度评估：{analysis['difficulty']}")
    return "\n".join(lines) if lines else ""
