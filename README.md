# Evolutionary Agent for Sii

这是一个轻量级 harness agent 原型。当前重点不是做一个完整平台，而是保留 agent 运行时最核心、最容易迁移的部分：模型调用、工具调用、middleware、checkpoint、stream event、sandbox 和 benchmark 配置。

本仓库目前支持两种模型接入方式：

- 本地调试：通过阿里云百炼 / DashScope 的 OpenAI-compatible API 调用 Qwen。
- 未来部署：切换到本地部署的 Qwen 权重，例如由 vLLM 暴露的 OpenAI-compatible 服务。

只要服务兼容 `/chat/completions`，代码侧基本不需要改，主要改 `.env`。

## 环境配置

建议使用 Python 3.11 或更高版本。

```bash
cd /path/to/Evolutionary-Agent-for-Sii
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

复制环境变量模板：

```bash
cp .env.example .env
```

本地使用百炼时，在 `.env` 中填写：

```dotenv
MODEL_PROVIDER=dashscope
DASHSCOPE_API_KEY=你的百炼 API Key
MODEL_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=qwen3.5-35b-a3b
MODEL_API_KEY_ENV=DASHSCOPE_API_KEY
```

将来切到本地 vLLM / Qwen 服务时，改成：

```dotenv
MODEL_PROVIDER=local
MODEL_BASE_URL=http://127.0.0.1:8000/v1
MODEL_NAME=qwen3-8b
MODEL_API_KEY=EMPTY
MODEL_API_KEY_ENV=
```

运行一个不依赖网络和真实模型的 smoke test：

```bash
MODEL_PROVIDER=mock python -m examples.run_agent "hello" --thread-id smoke
```

运行真实模型：

```bash
python -m examples.run_agent "你好，简单介绍一下你自己"
```

## 数据集

后续实验会用两个 Hugging Face 数据集：

- SimpleVQA: `m-a-p/SimpleVQA`
  - 地址：https://huggingface.co/datasets/m-a-p/SimpleVQA/tree/main
  - 类型：视觉问答，包含图片和文本标注。
  - 仓库页面显示格式包含 parquet，整体约 812 MB。
- 2WikiMultihopQA: `framolfese/2WikiMultihopQA`
  - 地址：https://huggingface.co/datasets/framolfese/2WikiMultihopQA/tree/main
  - 类型：文本多跳问答。
  - 仓库页面显示格式包含 parquet，整体约 388 MB。

当前 README 只写下载和目录规范，数据集本身不提交到 git。推荐目录：

```text
datasets/
  SimpleVQA/
    README.md
    test.parquet
    view_200.parquet
    simpleVQA_final_modified.json
    simpleVQA_datasets.zip
    images/
    simpleVQA_datasets/
  2WikiMultihopQA/
    README.md
    data/
```

下载命令：

```bash
python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='m-a-p/SimpleVQA', repo_type='dataset', local_dir='datasets/SimpleVQA')"
python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='framolfese/2WikiMultihopQA', repo_type='dataset', local_dir='datasets/2WikiMultihopQA')"
```

如果 Hugging Face 下载速度慢或 xet 大文件卡住，可以先只下载元数据和 parquet，再单独处理图片压缩包。下载后检查：

```bash
find datasets -maxdepth 3 -type f | sort | head -50
du -sh datasets/SimpleVQA datasets/2WikiMultihopQA
```

相关 `.env` 路径：

```dotenv
SIMPLEVQA_ROOT=./datasets/SimpleVQA
SIMPLEVQA_IMAGE_ROOT=./datasets/SimpleVQA/simpleVQA_datasets
SIMPLEVQA_ANNOTATION_FILE=./datasets/SimpleVQA/simpleVQA_final_modified.json
```

如果 SimpleVQA 图片仍是 zip，先解压：

```bash
python -m zipfile -e datasets/SimpleVQA/simpleVQA_datasets.zip datasets/SimpleVQA/
```

## 当前配置文件

`configs/` 下有三类配置：

- `qwen3_5_dashscope_simplevqa_mm.yaml`
  - 通过百炼 OpenAI-compatible API 跑 SimpleVQA 多模态问答。
  - 图片以本地文件 base64 data URL 传给模型。
- `qwen3_8b_simplevqa.yaml`
  - 本地 Qwen3-8B 文本模型的 SimpleVQA text-only baseline。
  - 不能看图，只适合做文本基线或链路 smoke test。
- `qwen3_5_9b_simplevqa_mm.yaml`
  - 本地多模态 Qwen 服务配置。
  - 适合未来服务器部署好本地权重后使用。

配置里使用 `${ENV_NAME:-default}` 形式表达可覆盖变量。具体解析逻辑后续可以接到统一 config loader；当前入口 `examples/run_agent.py` 主要从 `.env` 构造模型 client。

## Harness 架构

项目刻意不使用 LangGraph 的图状态机。核心是一个显式、可调试的顺序 loop：

```text
user input
  -> before_agent middleware
  -> before_model middleware
  -> model.generate(messages, tools_schema)
  -> after_model middleware
  -> execute requested tools
  -> append observations
  -> repeat until final or max_tool_iterations
  -> after_agent middleware
  -> checkpoint
```

这样做的好处是每一步都容易打印、断点、替换和迁移。当前 harness 更像“可插拔运行骨架”，而不是完整 agent 平台。

### 核心模块

```text
my_agent/
  agent/
    loop.py              # AgentLoop，顺序模型/工具循环
  harness/
    types.py             # Message、ToolCall、ToolResult、Observation、AgentState
    registry.py          # ToolRegistry，工具注册和查找
    middleware.py        # middleware 协议
  middleware/
    thread_data.py       # thread 工作目录和上下文
    tool_errors.py       # 工具错误转 observation
    loop_limit.py        # loop 限制
    sandbox.py           # sandbox 生命周期 middleware
  models/
    base.py              # ModelClient 协议
    dashscope.py         # DashScope + 通用 OpenAI-compatible client
    mock.py              # 本地 deterministic smoke test client
  runtime/
    checkpoint.py        # JSON checkpoint store
    stream.py            # stream event writer
    thread.py            # thread runtime helpers
  sandbox/
    local_executor.py    # 本地代码执行器，开发用
    docker_executor.py   # Docker 沙盒执行器，跑不可信代码时优先
  tools/
    code_execution.py    # execute_code tool
    deerflow_search.py   # DeerFlow 搜索工具适配和 DDGS fallback
  browser/
    browsergym_adapter.py # BrowserGym 薄适配
```

### Message 和 Observation

模型只直接看到 `Message` 列表。工具返回值会被转换成 `Observation`，再追加回 messages：

```text
ToolResult
  -> Observation(content, source, is_error, raw)
  -> Message(role="observation")
```

这样模型可以在下一轮看到工具成功或失败的结果。如果工具失败，错误也不会直接打断 agent，而是作为 observation 交给模型和 middleware 决定下一步。

### ModelClient

模型层只要求实现一个方法：

```python
async def generate(messages: list[Message], tools_schema: list[dict]) -> ModelOutput:
    ...
```

当前有三个实现：

- `MockModelClient`：无需网络，用于 smoke test。
- `DashScopeAgentModelClient`：百炼 / DashScope 便捷封装。
- `OpenAICompatibleAgentModelClient`：通用 OpenAI-compatible client，可接本地 vLLM。

工具调用协议目前是 prompt-level JSON，而不是 OpenAI function calling。模型如果需要工具，应输出：

```json
{"tool_calls":[{"name":"web_search","arguments":{"query":"...","max_results":3}}]}
```

最终答案输出：

```json
{"final":"short final answer"}
```

这让工具协议在不同模型服务之间更稳定，尤其适合先快速验证 harness 行为。

### ToolRegistry 和工具

工具只需要有：

```python
name: str
description: str
async def __call__(...) -> ToolResult
```

`ToolRegistry` 负责注册工具，`AgentLoop` 在模型请求工具时查找并执行。当前工具包括：

- 搜索工具适配：`build_deerflow_search_tools()`
- 代码执行工具：`CodeExecutionTool`
- 未来可以继续接 browser、OCR、dataset lookup、evaluation 等工具。

### Middleware

middleware 是 harness 的扩展点，用来在不污染主 loop 的情况下处理横切逻辑：

- `before_agent`
- `before_model`
- `after_model`
- `wrap_tool_call`
- `after_tool`
- `after_agent`

适合放：

- loop 次数限制
- thread 目录准备
- sandbox 启停
- 工具错误规范化
- 日志、监控、审计
- benchmark metadata 注入

### Checkpoint 和 Stream

`JsonCheckpointStore` 会按 `thread_id` 保存 agent state，方便调试长任务和复现中间状态。`StreamWriter` 会发出事件：

- `model_start`
- `model_end`
- `tool_start`
- `tool_end`
- `agent_final`
- `agent_halted`

这些事件目前打印到 stdout，将来可以接 UI、日志系统或评测记录器。

## 沙盒和工具安全

本地开发可以用 `LocalSandboxExecutor`，它会在本地工作目录执行代码。这个方式只适合可信代码。

如果要让模型执行不可信代码，建议使用 Docker：

```python
from my_agent.sandbox import DockerSandboxExecutor
```

并确保 Docker daemon 可用。未来部署时，也建议把代码执行工具默认切到 Docker 或其他隔离环境。

## 搜索工具

`my_agent.tools.deerflow_search` 会尝试加载 DeerFlow 原项目中的搜索工具。如果你本地有 DeerFlow harness，可以在 `.env` 设置：

```dotenv
DEERFLOW_HARNESS=/path/to/deer-flow/backend/packages/harness
ENABLE_SEARCH_TOOLS=true
```

如果没有 DeerFlow，它会尝试 DDGS fallback。缺少依赖或 API key 时，工具会返回可读的 error observation，而不是让 agent 直接崩溃。

## BrowserGym

`my_agent.browser.BrowserGymSession` 是薄适配层，保持 BrowserGym 的环境模型：

```text
reset -> observation
step(action) -> observation/reward/done/info
close
```

浏览器操作会被建模为普通 tool/environment，不和核心模型循环耦合。这样后续接 WebArena、MiniWoB 或 open-ended browser task 时，核心 harness 不需要大改。

## 推荐开发流程

1. 用 `MODEL_PROVIDER=mock` 跑 smoke test，确认 harness loop 没坏。
2. 用 `MODEL_PROVIDER=dashscope` 调百炼，快速验证 prompt、工具协议和 benchmark 输入输出。
3. 准备本地服务器上的 Qwen 权重，用 vLLM 暴露 `/v1/chat/completions`。
4. 改 `.env` 到 `MODEL_PROVIDER=local`，保持上层 harness 不变。
5. 将 benchmark loader / evaluator 接到当前 `configs/` 和 `datasets/` 目录规范上。

## 常见问题

### Missing API key

确认 `.env` 中有：

```dotenv
DASHSCOPE_API_KEY=...
MODEL_API_KEY_ENV=DASHSCOPE_API_KEY
```

### 本地 vLLM 连接失败

确认服务已启动，并且模型名和 `.env` 一致：

```bash
curl http://127.0.0.1:8000/v1/models
```

### SimpleVQA 图片找不到

确认：

```dotenv
SIMPLEVQA_IMAGE_ROOT=./datasets/SimpleVQA/simpleVQA_datasets
```

并检查图片 zip 是否已解压。

### 搜索工具失败

如果没有配置 DeerFlow 或搜索 API key，这是正常的。先关闭：

```dotenv
ENABLE_SEARCH_TOOLS=false
```

需要搜索时再安装 `ddgs` 或配置 DeerFlow provider。
