# my-agent

`my-agent` 是一个轻量 agent harness 骨架，组合了三个项目中最适合保留的部分：

- DeerFlow：harness 分层、middleware 生命周期、thread/checkpoint、stream event、搜索工具配置方式。
- AutoGen：Docker 沙盒执行、工作区绑定、超时、取消、输出截获、error observation。
- BrowserGym：浏览器环境作为独立 tool/environment，不混进核心模型-工具循环。

本项目刻意不使用 LangGraph 的图状态机来驱动工具调用链。核心执行器是一个显式的顺序 loop：

```text
user input
  -> before_agent middleware
  -> before_model middleware
  -> model.generate()
  -> after_model middleware
  -> execute requested tools
  -> append observations
  -> repeat until final or max_tool_iterations
  -> after_agent middleware
  -> checkpoint
```

## 设计边界

保留 DeerFlow 从 LangGraph 生态继承下来的结构性能力：

- thread_id 会话隔离
- checkpoint 持久化
- stream event
- middleware 钩子
- ToolMessage / Observation 风格错误反馈
- sandbox 生命周期
- 搜索工具分组和配置

不迁移：

- LangGraph `StateGraph` / `CompiledStateGraph`
- LangGraph ToolNode 工具链状态机
- DeerFlow 的完整 Gateway、前端、IM channels、skills、memory、subagents

## 目录

```text
my_agent/
  agent/              # 顺序 agent loop
  harness/            # types、tool registry、middleware base
  middleware/         # thread/sandbox/tool-error/loop-limit
  runtime/            # checkpoint、stream、thread context
  sandbox/            # AutoGen-style Docker/local code executor
  tools/              # DeerFlow search adapters + sandbox tools
  browser/            # BrowserGym adapter
  models/             # LLM client protocol + mock client
```

## 快速运行

```bash
cd /root/autodl-tmp/auto_agent/my-agent
python -m examples.run_mock
```

如需 Docker 沙盒，确保 Docker daemon 可用，然后在代码中使用：

```python
from my_agent.sandbox import DockerSandboxExecutor
```

## 搜索工具

`my_agent.tools.deerflow_search` 会优先尝试加载 DeerFlow 原项目中的搜索工具模块，例如：

- `deerflow.community.tavily.tools`
- `deerflow.community.ddg_search.tools`
- `deerflow.community.serper.tools`
- `deerflow.community.jina_ai.tools`
- `deerflow.community.infoquest.tools`
- `deerflow.community.firecrawl.tools`
- `deerflow.community.exa.tools`
- `deerflow.community.image_search.tools`

如果没有把 DeerFlow harness 加入 `PYTHONPATH`，适配器会返回可读的错误 observation，而不是让 agent 崩溃。

## BrowserGym

`my_agent.browser.BrowserGymSession` 是薄适配层。它保持 BrowserGym 的 `gymnasium` 环境模型：

```text
reset -> observation
step(action) -> observation/reward/done/info
close
```

浏览器操作被建模为普通 tool，便于后续把 WebArena、MiniWoB、openended browser task 接入 agent。

