"""
Qwen Agent Harness — Main Orchestrator
======================================

Drives the agent loop:
  1. Writes system + user turn to trajectory
  2. Calls Qwen-3.5 via Sglang OpenAI-compat API
  3. Dispatches tool calls and records results
  4. Loops until finish_reason == 'stop' or max_steps reached

Usage (CLI):
    python -m task_runner \
        --instruction "请帮我查询上海创智学院谢源老师的相关信息，并获取其代表作。" \
        --task-id my_task_010
    python -m task_runner \
        --instruction "请先帮我分析图像的内容，再调用search_image工具进行图像搜索。" \
        --image "/inspire/qb-ilm2/project/26summer-camp-01/qiaojingyang-240208120192/harness-sii/datasets/simpleVQA/CCSimpleQA/0.jpg" \
        --image-url "https://datasets-server.huggingface.co/cached-assets/ohjoonhee/SimpleVQA/--/8fefe22e2775a6ac0a73ac22edba8a01536b8a59/--/default/test/0/image/image.jpg?Expires=1779081093&Signature=cHN23HVLSGpna8jlbFRnpt90RruGsgAjpRTot1IArVYgZrUFTz2Fl5Gn7OSU6QVmxQMZFc8csXss9g9-8sh9fAPpRbOAwgdlVdH8yg1fr4pIGLneUXz8swhhSlSECAbYyDi-r2we7kizYjnuvlfDa45BsRU32c7sPVLttqVWbNH8vWrYi9rTajYAdbCn9l2zYMN~zpSp~8b4T2OwMGw6feZl3fBdZxMPWmuyf2GTaIAiisDTQd2b6-8Yq3CsIzjfmW6M4nN0T5O8FXLR-yTd5ve9Pj40U13410vyqUbcOGDC~R7hCtrXDhxpg4aivRPLcjcHPTbKgu10K09cWSTZAQ__&Key-Pair-Id=K204OQ5RWQVDLD" \
        --task-id my_task_011
"""

import argparse
import json
import logging
import os
import re
import time
import uuid
from types import SimpleNamespace
from typing import Optional
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # noqa: BLE001
    load_dotenv = None

if load_dotenv is not None:
    here = Path(__file__).resolve().parent
    load_dotenv(here.parent / ".env")
    load_dotenv(here / ".env", override=True)

from openai import OpenAI

from curator import CuratedContext, CuratorAgent
from memory_store import MemoryStore
from reflection import reflect
from roles import Role
from skill_store import SkillStore
from trajectory import Trajectory
from tools.search_tool import search_text, search_image
from tools.browser_tool import (
    browser_navigate, browser_get_text, browser_click,
    browser_type, browser_parallel,
)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("harness.task_runner")

# ---------------------------------------------------------------------------
# LLM connection.  The defaults target Alibaba Cloud Bailian / DashScope in
# OpenAI-compatible mode, matching the exam environment.  They can still be
# overridden for local vLLM/Sglang with LLM_BASE_URL and MODEL_NAME.
# ---------------------------------------------------------------------------
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "qwen3.5-35b-a3b")
LLM_API_KEY  = os.getenv("LLM_API_KEY") or os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY") or "EMPTY"
MAX_STEPS    = int(os.getenv("MAX_STEPS", "20"))
MAX_TOKENS   = int(os.getenv("MAX_TOKENS", "16000"))
SKILLS_DIR   = os.getenv("SKILLS_DIR", "skills")
LEARNED_SKILLS_DIR = os.getenv("LEARNED_SKILLS_DIR", "learned_skills")
ENABLE_SKILLS = os.getenv("ENABLE_SKILLS", "1") == "1"
ENABLE_REFLECTION = os.getenv("ENABLE_REFLECTION", "1") == "1"
ENABLE_THINKING = os.getenv("ENABLE_THINKING", "1") == "1"

# 调试开关：True = 不向 LLM 注册 tools，纯文本对话，便于先验证 LLM 通路
# 工具实现接好后默认关闭；如需调试 LLM 通路，export DISABLE_TOOLS=1
DISABLE_TOOLS = os.getenv("DISABLE_TOOLS", "0") == "1"

# ---------------------------------------------------------------------------
# Tool schema (OpenAI function-calling format)
# ---------------------------------------------------------------------------
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_text",
            "description": (
                "基于 Serper (Google) 的联网文字搜索，并用 Jina Reader 抽取每个结果页面的正文"
                "返回 [{rank,title,url,snippet,content}]。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query":     {"type": "string",  "description": "搜索关键词"},
                    "top_k":     {"type": "integer", "description": "返回条数（1-3）", "default": 1},
                    "fetch":     {"type": "boolean", "description": "是否抓取正文，false 时只返回摘要", "default": True},
                    "max_chars": {"type": "integer", "description": "每篇正文截断的最大字符数", "default": 3000},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_image",
            "description": (
                "图搜文：基于 Google Lens (Serper /lens) 的反向图像搜索，并用 "
                "Jina Reader 抽取结果页面正文。输入必须是 http(s) 图片 URL 。"
                "返回 [{rank,title,url,snippet,content}]。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "image_url": {"type": "string",  "description": "图片的 http(s) URL 或本地图片绝对路径"},
                    "top_k":     {"type": "integer", "description": "返回条数（1-3）", "default": 1},
                    "fetch":     {"type": "boolean", "description": "是否抓取正文", "default": True},
                    "max_chars": {"type": "integer", "description": "每篇正文截断的最大字符数", "default": 1500},
                },
                "required": ["image_url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_navigate",
            "description": (
                "在沙盒浏览器中打开一个 URL。默认顺带返回前若干字符的页面文本预览，"
                "需要完整正文请再调 browser_get_text。返回 "
                "{ok,url,title,wait_until,text_preview?,truncated?}。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url":          {"type": "string",  "description": "要访问的 URL（可省略协议头）"},
                    "wait_until":   {"type": "string",  "description": "Playwright 等待策略",
                                     "enum": ["domcontentloaded", "load", "networkidle"],
                                     "default": "domcontentloaded"},
                    "include_text": {"type": "boolean", "description": "是否返回 text_preview", "default": True},
                    "max_text":     {"type": "integer", "description": "text_preview 字符上限", "default": 2000},
                    "timeout":      {"type": "integer", "description": "导航超时秒数", "default": 30},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_get_text",
            "description": "返回当前页面清洗后的可见文本。返回 {ok,url,title,text,truncated,total_chars}。",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_chars": {"type": "integer", "description": "正文最大字符数", "default": 5000},
                    "timeout":   {"type": "integer", "description": "抽取超时秒数", "default": 15},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_click",
            "description": (
                "用 CSS 选择器点击当前页的元素。selector 接受任意合法 CSS，例如 "
                "'#login', 'button.primary', \"button:has-text('确定')\"。返回 "
                "{ok,selector,current_url,current_title,navigated}。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string",  "description": "CSS 选择器"},
                    "nth":      {"type": "integer", "description": "命中多个时取第几个（0 表示用 .first）", "default": 0},
                    "timeout":  {"type": "integer", "description": "点击超时秒数", "default": 10},
                },
                "required": ["selector"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_type",
            "description": (
                "向一个 CSS 选择器选中的输入框键入文本，可选按回车提交。"
                "返回 {ok,selector,submitted,current_url,current_title}。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string",  "description": "CSS 选择器（输入框）"},
                    "text":     {"type": "string",  "description": "要输入的文本"},
                    "submit":   {"type": "boolean", "description": "输入完是否按 Enter", "default": False},
                    "clear":    {"type": "boolean", "description": "输入前是否清空字段", "default": True},
                    "timeout":  {"type": "integer", "description": "操作超时秒数", "default": 10},
                },
                "required": ["selector", "text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_parallel",
            "description": (
                "在沙盒浏览器中**并发**打开多个 URL。"
                "mode='navigate' 每个返回 {url,title,text_preview,truncated}；"
                "mode='get_text' 每个返回 {url,title,text,truncated,total_chars}。"
                "返回值是一个列表，单个 URL 失败不影响其他。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "urls":            {"type": "array", "items": {"type": "string"}, "description": "URL 列表"},
                    "mode":            {"type": "string", "enum": ["navigate", "get_text"], "default": "navigate"},
                    "max_chars":       {"type": "integer", "description": "每条结果文本上限；缺省时 navigate=2000，get_text=5000"},
                    "wait_until":      {"type": "string",
                                        "enum": ["domcontentloaded", "load", "networkidle"],
                                        "default": "domcontentloaded"},
                    "max_concurrency": {"type": "integer", "description": "同时打开的标签页数（1-8）", "default": 4},
                    "timeout":         {"type": "integer", "description": "单页超时秒数", "default": 30},
                },
                "required": ["urls"],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# Tool function dispatch map
# ---------------------------------------------------------------------------
TOOL_FN_MAP = {
    "search_text":      lambda a: search_text(**a),
    "search_image":     lambda a: search_image(
        a.get("image") or a.get("image_url", ""),
        a.get("top_k", 1),
        a.get("fetch", True),
        a.get("max_chars", 1500),
    ),
    "browser_navigate": lambda a: browser_navigate(**a),
    "browser_get_text": lambda a: browser_get_text(**a),
    "browser_click":    lambda a: browser_click(**a),
    "browser_type":     lambda a: browser_type(**a),
    "browser_parallel": lambda a: browser_parallel(**a),
}

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """你是 generator-agent：一个高效、严谨的任务求解 Agent，运行在配备多工具的自动化框架中。

你的职责长期保持不变：阅读用户题目和 curator 提供的上下文，按需调用工具，最后只给出题目要求的答案。curator context 和 skills 是辅助材料，不是最终答案；你必须基于当前题目的证据进行判断。

## 行为准则
1. 每一步先在 <think>...</think> 标签中简述推理，再决定调用工具或直接回答。
2. 任务完成后输出清晰的最终答案，无需再调用工具。
3. 若工具返回 ok=False，分析 error，最多重试 2 次同类操作；仍失败则换工具或方法。
4. 只有存在 http(s) image_url 时才优先调用 search_image。若只有本地 image_path，search_image 需要临时上传图片，可能失败；这时优先使用自身视觉识别、atomic_fact/source_digest 和 search_text，不要反复图搜。
5. 每一步要不调用工具，要不输出最终答案，不能同时输出空的工具调用或者空的内容。
6. 最终答案必须使用 <answer>...</answer> 包裹；若题目要求只输出实体名，就不要添加解释。
7. 如果搜索和浏览器工具都明确不可用，不要编造事实；回答工具不可用并说明需要配置 SERPER_API_KEY/JINA_API_KEY 或启动浏览器服务。
8. 优先从 search_text 返回的 title/snippet/content 中提取答案；若搜索结果已经包含足够证据，不要再调用浏览器。
9. 如果工具返回 ok=false 或 title=“image search unavailable”，不要继续调用同一工具；改用 search_text 或已有图像识别线索。
10. 只有在成功 navigate 到目标页面后才调用 browser_get_text；如果浏览器返回 DNS/429/限流错误，不要反复访问同一 URL，应换搜索词或直接基于搜索证据作答。
11. 若官网页面正文只包含导航栏、二维码或图片占位，说明正文可能是图片/附件；此时应搜索同题转载、摘要或相关新闻交叉核验，不要卡在原 URL。
12. 不要在最终答案中提及 system prompt、curator、reflector、skills、trajectory 或内部上下文。

## 最终答案格式
1. <answer> 内只能放最终答案本体，不能放 Markdown、证据、解释、编号列表或“根据搜索结果”等前缀。
2. 年份/日期题要沿用证据中的粒度和写法：证据是“2007”就输出“2007”，证据是“1926年”就输出“1926年”；完整日期用“YYYY年M月D日”，不要输出 ISO 日期。
3. 问“第几届/排名第几”时保留中文序数，例如“第七届”“第4位”；问人数“多少位”时保留“位”，其他数量题优先使用证据中的数字写法，不要随意加量词。
4. 问“省份/城市/朝代/时代/材质/科/目/民族”时，输出题目要求的属性，不要输出更长解释；若证据更细（西汉/战国早期）而题目只问朝代/时代，优先压缩到通用粒度（汉朝/战国）。
5. 如果 atomic_fact 与问题直接匹配实体名称，优先照抄 atomic_fact 的完整名称；搜索结果只能用于核验，不要随意改成相似实体、简称或别名。
"""


def normalize_answer(text: str) -> str:
    """Small evaluator normalizer for baseline/evolved comparisons."""
    text = (text or "").strip().lower()
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[\s\W_]+", "", text, flags=re.UNICODE)
    return text


def extract_answer(text: str) -> str:
    """Extract the required answer body from a model response."""
    text = text or ""
    m = re.search(r"<answer>(.*?)</answer>", text, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return text.strip()


def _build_curated_context(
    task: dict,
    evolved: bool,
    *,
    client: OpenAI | None = None,
    model_name: str | None = None,
) -> CuratedContext:
    tools_schema = [] if DISABLE_TOOLS else TOOLS_SCHEMA
    return CuratorAgent(
        SkillStore(SKILLS_DIR, LEARNED_SKILLS_DIR),
        MemoryStore(LEARNED_SKILLS_DIR),
    ).curate(
        task=task,
        base_system_prompt=SYSTEM_PROMPT,
        tools_schema=tools_schema,
        evolved=evolved and ENABLE_SKILLS,
        client=client,
        model_name=os.getenv("CURATOR_MODEL_NAME") or model_name,
    )


def _call_signature(name: str, args: dict) -> str:
    try:
        return f"{name}:{json.dumps(args, ensure_ascii=False, sort_keys=True)}"
    except TypeError:
        return f"{name}:{str(args)}"


def _is_success(pred: str, answer: str = "", reached_max_steps: bool = False) -> bool:
    if reached_max_steps or not pred.strip():
        return False
    if answer:
        return normalize_answer(pred) == normalize_answer(answer)
    return True


def _tool_call_obj(raw: dict) -> SimpleNamespace:
    fn = raw.get("function", {}) or {}
    return SimpleNamespace(
        id=raw.get("id", ""),
        function=SimpleNamespace(
            name=fn.get("name", ""),
            arguments=fn.get("arguments", "{}") or "{}",
        ),
    )


def _merge_stream_tool_call(parts: dict[int, dict], delta_tool_call) -> None:
    idx = getattr(delta_tool_call, "index", None)
    if idx is None:
        idx = 0
    cur = parts.setdefault(
        int(idx),
        {"id": "", "type": "function", "function": {"name": "", "arguments": ""}, "index": int(idx)},
    )
    if getattr(delta_tool_call, "id", None):
        cur["id"] = delta_tool_call.id
    if getattr(delta_tool_call, "type", None):
        cur["type"] = delta_tool_call.type
    fn = getattr(delta_tool_call, "function", None)
    if fn is not None:
        if getattr(fn, "name", None):
            cur["function"]["name"] += fn.name
        if getattr(fn, "arguments", None):
            cur["function"]["arguments"] += fn.arguments


def _chat_completion(client: OpenAI, request_kwargs: dict) -> dict:
    """Call Qwen through OpenAI-compatible API.

    DashScope requires stream=True when extra_body.enable_thinking is enabled,
    so the harness aggregates stream chunks into the same shape the loop needs.
    """
    if not ENABLE_THINKING:
        request_kwargs = dict(request_kwargs)
        request_kwargs.pop("extra_body", None)
        response = client.chat.completions.create(**request_kwargs)
        choice = response.choices[0]
        msg = choice.message
        raw_tool_calls = []
        for tc in getattr(msg, "tool_calls", None) or []:
            raw_tool_calls.append(tc.model_dump() if hasattr(tc, "model_dump") else tc)
        usage = getattr(response, "usage", None)
        return {
            "content": msg.content or "",
            "reasoning_content": getattr(msg, "reasoning_content", "") or "",
            "finish_reason": choice.finish_reason,
            "tool_calls_data": raw_tool_calls,
            "tool_calls": [_tool_call_obj(x) for x in raw_tool_calls],
            "total_tokens": getattr(usage, "total_tokens", None) or "",
        }

    stream_kwargs = dict(request_kwargs)
    stream_kwargs["stream"] = True
    stream_kwargs["stream_options"] = {"include_usage": True}
    content_parts: list[str] = []
    reasoning_parts: list[str] = []
    tool_call_parts: dict[int, dict] = {}
    finish_reason = None
    total_tokens = ""

    stream = client.chat.completions.create(**stream_kwargs)
    for chunk in stream:
        if getattr(chunk, "usage", None):
            total_tokens = getattr(chunk.usage, "total_tokens", None) or total_tokens
        if not getattr(chunk, "choices", None):
            continue
        choice = chunk.choices[0]
        finish_reason = choice.finish_reason or finish_reason
        delta = choice.delta
        if getattr(delta, "reasoning_content", None):
            reasoning_parts.append(delta.reasoning_content)
        if getattr(delta, "content", None):
            content_parts.append(delta.content)
        for tc in getattr(delta, "tool_calls", None) or []:
            _merge_stream_tool_call(tool_call_parts, tc)

    tool_calls_data = [tool_call_parts[i] for i in sorted(tool_call_parts)]
    return {
        "content": "".join(content_parts),
        "reasoning_content": "".join(reasoning_parts),
        "finish_reason": finish_reason,
        "tool_calls_data": tool_calls_data,
        "tool_calls": [_tool_call_obj(x) for x in tool_calls_data],
        "total_tokens": total_tokens,
    }


# ---------------------------------------------------------------------------
# Core run_task function
# ---------------------------------------------------------------------------

def run_task(
    task: dict,
    max_steps: int = MAX_STEPS,
    llm_base_url: str = LLM_BASE_URL,
    model_name: str = MODEL_NAME,
    trajectory_dir: str = "trajectories",
) -> dict:
    """
    Execute a task with the Qwen agent loop.

    Args:
        task:            Dict with keys:
                           - "instruction" (str, required): task description
                           - "id"          (str, optional): task identifier
                           - "image_b64"   (str, optional): base64 image for vision input
                           - "image_url"   (str, optional): online image url for vision input
        max_steps:       Maximum agent loop iterations.
        llm_base_url:    Sglang / OpenAI-compat endpoint.
        model_name:      Model identifier served by Sglang.
        trajectory_dir:  Directory to write JSONL trajectories.

    Returns:
        Dict with keys: task_id, answer, steps, trajectory_path, summary
    """
    task_id     = task.get("id") or str(uuid.uuid4())[:8]
    instruction = task["instruction"]
    image_b64   = task.get("image_b64")
    image_url   = task.get("image_url")
    image_path  = task.get("image_path")
    gold_answer = task.get("answer", "")
    evolved     = bool(task.get("evolved", True))

    logger.info("run_task: task_id=%s", task_id)

    overwrite_trajectory = bool(task.get("overwrite_trajectory", False))
    traj   = Trajectory(
        task_id,
        output_dir=trajectory_dir,
        reset=overwrite_trajectory,
        preserve_existing=not overwrite_trajectory,
    )
    client = OpenAI(
        base_url=llm_base_url or LLM_BASE_URL,
        api_key=LLM_API_KEY if (llm_base_url or LLM_BASE_URL).startswith("https://dashscope") else (LLM_API_KEY or "EMPTY"),
    )
    model_name = model_name or MODEL_NAME
    started_at = time.time()
    tool_call_count = 0
    repeated_tool_calls = 0
    seen_tool_calls: dict[str, int] = {}
    reached_max_steps = False

    # ------------------------------------------------------------------ step 0
    # Write system turn.  In evolved mode an LLM curator-agent reads the task,
    # chooses likely useful skill files, and writes the context for generator.
    curated = _build_curated_context(
        task,
        evolved=evolved,
        client=client,
        model_name=model_name,
    )
    system_prompt = curated.system_prompt
    traj.write(Role.SYSTEM, system_prompt, step_id=0)

    # Build user message (optionally include image)
    if image_b64:
        text = instruction
        if image_url:
            text += "\n输入图像的在线链接：" + image_url
        if image_path:
            text += "\n输入图像的本地路径 image_path：" + image_path
        user_content = [
            {"type": "text",      "text": text},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
        ]
    elif image_url:
        user_content = [
            {"type": "text", "text": instruction + "\n输入图像的在线链接：" + image_url},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]
    else:
        user_content = instruction

    traj.write(Role.USER, user_content, step_id=0)

    # ------------------------------------------------------------------ loop
    final_answer = ""

    for step in range(1, max_steps + 1):
        logger.info("--- step %d ---", step)

        messages = traj.to_messages()
        logger.info("messages count=%d, sending to LLM ...", len(messages))

        # 构造请求参数：调试模式下不注册 tools，避免协议不匹配
        request_kwargs = dict(
            model=model_name,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=1.0,
            extra_body={"enable_thinking": True},
        )
        if not DISABLE_TOOLS:
            request_kwargs["tools"] = TOOLS_SCHEMA
            request_kwargs["tool_choice"] = "auto"

        try:
            llm_output = _chat_completion(client, request_kwargs)
        except Exception as exc:
            logger.error("LLM call failed: %s", exc, exc_info=True)
            traj.write(
                Role.TOOL,
                f"[HARNESS ERROR] LLM call failed at step {step}: {exc}",
                step_id=step,
            )
            break

        content = llm_output["content"]
        reasoning_content = llm_output["reasoning_content"]
        total_tokens = llm_output["total_tokens"]
        finish_reason = llm_output["finish_reason"]

        # 调试模式下强制忽略 tool_calls（虽然不传 tools 通常不会出现）
        tool_calls = None if DISABLE_TOOLS else llm_output["tool_calls"]

        # Write assistant turn
        tool_calls_data = llm_output["tool_calls_data"] if tool_calls else []
        
        extra = {}
        
        if tool_calls_data:
            extra["tool_calls"] = tool_calls_data
        if reasoning_content:
            extra["reasoning_content"] = reasoning_content
        if total_tokens:
            extra["total_tokens"] = total_tokens
                        
        traj.write(
            Role.ASSISTANT,
            content,
            step_id=step,
            extra= extra if extra else None,
        )

        if content:
            logger.info("assistant: %s", content[:200])
        logger.info("finish_reason=%s, has_tool_calls=%s", finish_reason, bool(tool_calls))

        # Done?
        # 标准退出条件：没有 tool_calls 时就结束（finish_reason 可能是 stop / length 等）
        if not tool_calls and finish_reason and content != "":
            final_answer = content
            logger.info("Task complete at step %d", step)
            break
        
        if not tool_calls and content == "":
            continue

        # -------------------------------------------------------- tool calls
        for tc in tool_calls:
            tool_call_count += 1
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError as exc:
                fn_args = {}
                logger.warning("Bad tool args JSON: %s", exc)
            if fn_name == "search_image" and image_path:
                requested_image = str(fn_args.get("image") or fn_args.get("image_url") or "")
                if requested_image and not requested_image.startswith(("http://", "https://")):
                    requested_path = Path(requested_image).expanduser()
                    if not requested_path.exists():
                        fn_args["image_url"] = image_path
                        fn_args.pop("image", None)
                        logger.info("rewrote search_image image to task image_path=%s", image_path)

            logger.info("tool_call: %s(%s)", fn_name, fn_args)
            sig = _call_signature(fn_name, fn_args)
            seen_tool_calls[sig] = seen_tool_calls.get(sig, 0) + 1
            if seen_tool_calls[sig] > 1:
                repeated_tool_calls += 1
                if seen_tool_calls[sig] >= 3:
                    tool_result = (
                        "[HARNESS WARNING] Repeated identical tool call suppressed. "
                        "Change query/URL or answer from existing evidence."
                    )
                    traj.write(
                        Role.TOOL,
                        tool_result,
                        step_id=step,
                        tool_call_id=tc.id,
                        extra={"fn_name": fn_name, "fn_args": fn_args, "suppressed_repeat": True},
                    )
                    continue

            # Dispatch
            if fn_name not in TOOL_FN_MAP:
                tool_result = f"[ERROR] Unknown tool: {fn_name}"
            else:
                try:
                    raw = TOOL_FN_MAP[fn_name](fn_args)
                    # 工具返回结构化对象时，序列化为 JSON 字符串方便 LLM 解读
                    if isinstance(raw, (dict, list)):
                        tool_result = json.dumps(raw, ensure_ascii=False)
                    else:
                        tool_result = str(raw)
                except Exception as exc:
                    tool_result = f"[ERROR] Tool '{fn_name}' raised: {type(exc).__name__}: {exc}"
                    logger.exception("Tool error")

            logger.info("tool_result (%s): %s", fn_name, str(tool_result)[:200])

            traj.write(
                Role.TOOL,
                tool_result,
                step_id=step,
                tool_call_id=tc.id,
                extra={"fn_name": fn_name, "fn_args": fn_args},
            )
    else:
        logger.warning("Reached max_steps=%d without finish_reason=stop", max_steps)
        reached_max_steps = True
        final_answer = final_answer or "[HARNESS] Max steps reached. Last assistant message above."

    summary = traj.summary()
    pred_answer = extract_answer(final_answer)
    success = _is_success(pred_answer, str(gold_answer), reached_max_steps)
    elapsed = time.time() - started_at
    summary.update(
        {
            "instruction": instruction,
            "pred": pred_answer,
            "answer": gold_answer,
            "success": success,
            "elapsed_sec": elapsed,
            "tool_call_count": tool_call_count,
            "repeated_tool_calls": repeated_tool_calls,
            "reached_max_steps": reached_max_steps,
            "curator_family": curated.family,
            "selected_skills": [skill.skill_id for skill in curated.selected_skills],
        }
    )
    logger.info("Trajectory summary: %s", summary)

    # ---------------------------------------------------------------- reflection + skill evolution
    # Reflection is triggered on failure and can optionally record successful
    # tactics.  The durable artifact is a Markdown skill patch written to the
    # learned skill directory, keeping seed skills separate from training output.
    should_reflect = ENABLE_REFLECTION and (not success)
    record_ungraded_success = os.getenv("RECORD_UNGRADED_SUCCESS_MEMORY", "0") == "1"
    has_gold_answer = bool(str(gold_answer or "").strip())
    should_record_success = (
        ENABLE_SKILLS
        and os.getenv("RECORD_SUCCESS_MEMORY", "0") == "1"
        and success
        and (has_gold_answer or record_ungraded_success)
    )
    if ENABLE_SKILLS and (should_reflect or should_record_success):
        trajectory_rows = traj.read_all()
        skill_store = SkillStore(SKILLS_DIR, LEARNED_SKILLS_DIR)
        memory_store = MemoryStore(LEARNED_SKILLS_DIR)
        skill_manifest = skill_store.manifest_text()
        reflection_query = "\n".join(
            str(x or "")
            for x in (
                instruction,
                pred_answer,
                summary.get("curator_family", ""),
                " ".join(summary.get("selected_skills", []) or []),
            )
        )
        relevant_learned = [
            skill for skill in skill_store.retrieve(reflection_query, k=int(os.getenv("REFLECTION_SKILL_CONTEXT_K", "4")))
            if skill.source == "learned"
        ]
        learned_skill_context = [
            {
                "skill_id": skill.skill_id,
                "title": skill.title,
                "domains": skill.domains,
                "triggers": skill.triggers,
                "summary": skill.summary,
                "body_excerpt": str(skill.body or "")[:1800],
            }
            for skill in relevant_learned
        ]
        if should_reflect:
            reflection = reflect(
                instruction=instruction,
                pred=pred_answer,
                answer=str(gold_answer or ""),
                trajectory=trajectory_rows,
                trajectory_summary=summary,
                skill_manifest=skill_manifest,
                skill_context=learned_skill_context,
                model_name=os.getenv("REFLECTION_MODEL_NAME") or model_name,
                base_url=os.getenv("REFLECTION_BASE_URL") or llm_base_url,
                api_key=os.getenv("REFLECTION_API_KEY") or LLM_API_KEY,
            )
            lesson = reflection.reusable_memory or reflection.failure_reason
            strategy = reflection.corrected_strategy
            tags = reflection.tags
            traj.write(
                Role.SYSTEM,
                json.dumps(
                    {
                        "reflection": {
                            "failure_reason": reflection.failure_reason,
                            "corrected_strategy": strategy,
                            "reusable_memory": lesson,
                            "tags": tags,
                            "skill_updates": reflection.skill_updates,
                        }
                    },
                    ensure_ascii=False,
                ),
                step_id=step if "step" in locals() else None,
                extra={"event": "reflection"},
            )
            outcome = "failure"
        else:
            lesson = "该任务成功完成；后续相似问题应复用有效证据链，并保持最终答案格式简洁。"
            strategy = "先识别题目核心实体/关系，再用工具核验缺口；最终只输出 <answer>答案</answer>。"
            tags = ["evidence", "format"]
            reflection = None

        skill_updates = reflection.skill_updates if reflection is not None else [
            {
                "op": "update",
                "skill_id": "memory",
                "title": "Memory Skill",
                "domains": tags,
                "triggers": tags,
                "summary": "Reusable success patterns and compact task-solving habits.",
                "body": (
                    "Use this skill for general task-solving habits when no narrower learned skill applies.\n\n"
                    "## When to use\n"
                    "- The task requires choosing a concise answer from mixed hints, search results, or compact evidence.\n"
                    "- No specialized skill clearly covers the failure mode.\n\n"
                    "## Procedure\n"
                    "- Identify the requested answer type before using tools: entity, attribute, date, count, location, yes/no, or comparison.\n"
                    "- Extract the core entity and relation from the question, then list the exact evidence gap.\n"
                    "- Use compact dataset hints or already returned tool evidence first; call tools only for the unresolved gap.\n"
                    "- Prefer one high-signal query over several broad searches, and stop after the evidence directly resolves the answer.\n"
                    "- Preserve the answer granularity and language requested by the question.\n\n"
                    "## Stop and output\n"
                    "- If two evidence signals agree, answer instead of continuing to search.\n"
                    "- Put only the final answer body inside <answer>...</answer> unless the user explicitly asks for explanation."
                ),
                "confidence": 0.55,
            }
        ]
        applied_skill_updates = skill_store.apply_updates(skill_updates)
        if applied_skill_updates:
            traj.write(
                Role.SYSTEM,
                json.dumps({"skill_updates_applied": applied_skill_updates}, ensure_ascii=False),
                step_id=step if "step" in locals() else None,
                extra={"event": "skill_update"},
            )
            summary["skill_updates_applied"] = applied_skill_updates

        memory_store.append_short_term(
            task=task,
            summary=summary,
            lesson=lesson,
            skill_updates_applied=applied_skill_updates,
        )
    elif ENABLE_SKILLS:
        MemoryStore(LEARNED_SKILLS_DIR).append_short_term(
            task=task,
            summary=summary,
            lesson="Current run completed without reflection; keep as short-term routing evidence only.",
            skill_updates_applied=[],
        )

    return {
        "task_id":         task_id,
        "instruction":     instruction,
        "answer":          final_answer,
        "pred":            pred_answer,
        "success":         success,
        "steps":           step,
        "trajectory_path": str(traj.path),
        "summary":         summary,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Qwen Agent Harness — run a single task from the command line",
    )
    p.add_argument("--instruction", "-i", required=True, help="Task instruction text")
    p.add_argument("--task-id",     "-t", default=None,  help="Optional task ID (auto-generated if omitted)")
    p.add_argument("--max-steps",   "-s", type=int, default=MAX_STEPS, help="Max agent loop steps")
    p.add_argument("--llm-url",           default=LLM_BASE_URL, help="Sglang base URL")
    p.add_argument("--model",             default=MODEL_NAME,   help="Model name")
    p.add_argument("--traj-dir",          default="trajectories", help="Trajectory output directory")
    p.add_argument("--image",             default=None, help="Local path to input image (optional)")
    p.add_argument("--image-url",         default=None, help="Online path to input image (optional)")
    p.add_argument("--answer",            default="", help="Gold answer for evaluation/reflection (optional)")
    p.add_argument("--baseline",          action="store_true", help="Disable memory injection for baseline runs")
    p.add_argument("--overwrite-traj",    action="store_true", help="Overwrite <task-id>.jsonl instead of preserving old runs")
    return p.parse_args()


if __name__ == "__main__":
    import base64

    args = _parse_args()

    image_b64 = None
    if args.image:
        with open(args.image, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode()
    image_url = None
    if args.image_url:
        image_url = args.image_url

    task = {
        "instruction": args.instruction,
        "image_b64":   image_b64,
        "image_path":  str(Path(args.image).resolve()) if args.image else "",
        "image_url":   image_url,
        "answer":      args.answer,
        "evolved":     not args.baseline,
        "overwrite_trajectory": args.overwrite_traj,
    }
    if args.task_id:
        task["id"] = args.task_id

    result = run_task(
        task,
        max_steps=args.max_steps,
        llm_base_url=args.llm_url,
        model_name=args.model,
        trajectory_dir=args.traj_dir,
    )

    print("\n" + "=" * 60)
    print("TASK COMPLETE")
    print("=" * 60)
    print(f"Task ID:  {result['task_id']}")
    print(f"Steps:    {result['steps']}")
    print(f"Traj:     {result['trajectory_path']}")
    print(f"\nAnswer:\n{result['answer']}")
