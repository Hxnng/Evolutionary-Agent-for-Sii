# Evolutionary Agent Harness for SII

这是面向“自进化的任务求解智能体”课题的 harness 实现。当前版本已经接入百炼 Qwen、Serper/Jina 搜索、可选 search-proxy、浏览器沙盒、轨迹记录、失败反思、长期记忆、SimpleVQA/2Wiki/benchmark 批量评测与 metrics 汇总。

## 目录结构

```text
browser-service/             # Playwright 浏览器沙盒服务
harness-sii/
  task_runner.py             # 单任务 ReAct 主循环
  trajectory.py              # JSONL 轨迹记录与回放
  memory.py                  # 长期记忆检索与写入
  reflection.py              # 失败反思
  evaluate.py                # SimpleVQA JSON/JSONL 评测
  evaluate_2wiki.py          # 2Wiki parquet/JSON/JSONL 评测
  evaluate_benchmark.py      # benchmark.csv 评测
  metris.py                  # 预测与轨迹指标汇总、baseline/evolved 对比
  tools/search_tool.py       # Serper/Jina 搜索，支持 direct/proxy
  tools/browser_tool.py      # 浏览器工具，支持 HTTP fallback
  data/                      # 本地数据集，已被 .gitignore 忽略
```

## 环境安装

推荐使用 miniconda：

```bash
conda create -n sii-harness python=3.11 -y
conda activate sii-harness
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii
pip install -r requirements.txt
```

浏览器服务第一次运行会自动安装自己的依赖和 Playwright Chromium：

```bash
conda activate sii-harness
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/browser-service
bash run.sh
```

## 配置

复制模板：

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii
cp .env.example harness-sii/.env
```

最小配置：

```dotenv
DASHSCOPE_API_KEY=你的百炼key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=qwen3.5-35b-a3b

SERPER_API_KEY=你的serper key
JINA_API_KEY=你的jina key

SANDBOX_BASE_URL=http://127.0.0.1:8080
ENABLE_THINKING=1
DISABLE_TOOLS=0
ENABLE_REFLECTION=1
ENABLE_MEMORY=1
```

`harness-sii/.env` 含真实 key，不要提交。项目已通过 `.gitignore` 忽略 `.env`、`data/`、`runs/`、`trajectories/`、checkpoint 等运行产物。

## 搜索模式

### Direct 模式，默认推荐

Direct 模式由 `harness-sii/tools/search_tool.py` 直接访问 Serper 和 Jina：

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii
python -B tools/search_tool.py text "上海创智学院 谢源老师 代表作" --top-k 1 --no-fetch
```

正常会看到：

```text
[mode] direct
```

### Proxy 模式，可选

`search-proxy` 适合“跑 agent 的机器不能直连公网，但另一台 CPU 机器能访问公网”的场景。代理服务本身是可用的，当前 harness 已恢复可选接入：只要设置 `SEARCH_PROXY_URL`，搜索工具就会优先走代理。

在有公网的机器上启动代理：

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii/search-proxy
export SERPER_API_KEY=你的serper key
export JINA_API_KEY=你的jina key
export PROXY_API_TOKEN=一个随机token   # 可选但推荐
bash run.sh
```

健康检查：

```bash
curl http://127.0.0.1:8090/health
```

在 agent 运行环境的 `harness-sii/.env` 中设置：

```dotenv
SEARCH_PROXY_URL=http://127.0.0.1:8090
SEARCH_PROXY_TOKEN=一个随机token
SEARCH_PROXY_FALLBACK=1
```

再测：

```bash
python -B tools/search_tool.py text "上海创智学院 谢源老师 代表作" --top-k 1 --no-fetch
```

正常会看到：

```text
[mode] proxy
```

如果 proxy 配错或暂时不可用，默认 `SEARCH_PROXY_FALLBACK=1` 会回退 direct 模式，避免整批评测直接中断。若希望代理失败立即报错，可设为 `SEARCH_PROXY_FALLBACK=0`。

## 浏览器服务

另开终端启动：

```bash
conda activate sii-harness
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/browser-service
bash run.sh
```

检查：

```bash
curl http://127.0.0.1:8080/health
```

如果 `www.sii.edu.cn` 等域名 DNS 失败，`browser_navigate` 会返回结构化失败，harness 会继续用搜索、Jina 或其他来源完成任务，不会再把服务端打成 500。

## 单任务运行

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii
python -B task_runner.py \
  --instruction "请查询上海创智学院谢源老师的代表作。" \
  --task-id smoke_001 \
  --traj-dir trajectories \
  --max-steps 8
```

轨迹默认保留历史运行。同一个 `--task-id` 第一次写：

```text
trajectories/smoke_001.jsonl
```

再次运行会写：

```text
trajectories/smoke_001_YYYYMMDD_HHMMSS.jsonl
```

只有显式加 `--overwrite-traj` 才会覆盖 `<task-id>.jsonl`。

## 数据集评测

### SimpleVQA

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii
python -B evaluate.py \
  --dataset data/simpleVQA/simpleVQA_final_modified.json \
  --image-root data/simpleVQA/simpleVQA_datasets \
  --output runs/evolved/simplevqa_predictions.jsonl \
  --metrics-output runs/evolved/simplevqa_metrics.json \
  --traj-dir runs/evolved/simplevqa_trajectories \
  --split-name simplevqa \
  --limit 20
```

全量并行可以去掉 `--limit`，并设置 `--workers`。建议先从 4 或 8 开始，稳定后再加大：

```bash
python -B evaluate.py \
  --dataset data/simpleVQA/simpleVQA_final_modified.json \
  --image-root data/simpleVQA/simpleVQA_datasets \
  --output runs/evolved/simplevqa_full_predictions.jsonl \
  --metrics-output runs/evolved/simplevqa_full_metrics.json \
  --traj-dir runs/evolved/simplevqa_full_trajectories \
  --split-name simplevqa \
  --workers 8
```

如果百炼或搜索服务出现限流、超时、429，先降到 `--workers 4`；如果稳定且机器/接口额度允许，可以试 `--workers 12` 或 `--workers 16`。

### 2WikiMultihopQA

```bash
python -B evaluate_2wiki.py \
  --dataset data/2wiki \
  --split validation \
  --output runs/evolved/2wiki_predictions.jsonl \
  --metrics-output runs/evolved/2wiki_metrics.json \
  --traj-dir runs/evolved/2wiki_trajectories \
  --split-name 2wiki \
  --limit 20
```

说明：本地 `2wiki` 的 validation/test parquet 可读；train shard 中若有不可读文件，脚本默认会跳过。需要严格失败则加 `--strict`。

### benchmark.csv

闭源 benchmark 若为 CSV，请使用列名：

```text
problem,image,answer
```

运行：

```bash
python -B evaluate_benchmark.py \
  --dataset data/benchmark.csv \
  --output runs/evolved/benchmark_predictions.jsonl \
  --metrics-output runs/evolved/benchmark_metrics.json \
  --traj-dir runs/evolved/benchmark_trajectories \
  --split-name benchmark
```

## 输出格式

预测 JSONL 每行包含核心字段：

```json
{
  "index": 0,
  "task_id": "simplevqa_0",
  "instruction": "...",
  "image": "CCSimpleQA/0.jpg",
  "answer": "...",
  "pred": "...",
  "success": true,
  "steps": 4,
  "trajectory_path": "runs/evolved/simplevqa_trajectories/simplevqa_0.jsonl"
}
```

轨迹 JSONL 保存完整 system/user/assistant/tool/reflection 过程，可用于复盘和评分。

## Baseline 与 Evolved 对比

无记忆/反思注入 baseline：

```bash
python -B evaluate.py \
  --dataset data/simpleVQA/simpleVQA_final_modified.json \
  --image-root data/simpleVQA/simpleVQA_datasets \
  --output runs/baseline/simplevqa_predictions.jsonl \
  --metrics-output runs/baseline/simplevqa_metrics.json \
  --traj-dir runs/baseline/simplevqa_trajectories \
  --split-name simplevqa \
  --baseline \
  --limit 50
```

带反思/记忆 evolved：

```bash
python -B evaluate.py \
  --dataset data/simpleVQA/simpleVQA_final_modified.json \
  --image-root data/simpleVQA/simpleVQA_datasets \
  --output runs/evolved/simplevqa_predictions.jsonl \
  --metrics-output runs/evolved/simplevqa_metrics.json \
  --traj-dir runs/evolved/simplevqa_trajectories \
  --split-name simplevqa \
  --limit 50
```

汇总单次结果：

```bash
python -B metris.py \
  --pred runs/evolved/simplevqa_predictions.jsonl \
  --traj-dir runs/evolved/simplevqa_trajectories \
  --output runs/evolved/simplevqa_report.json
```

对比 baseline/evolved：

```bash
python -B metris.py \
  --baseline-pred runs/baseline/simplevqa_predictions.jsonl \
  --baseline-traj runs/baseline/simplevqa_trajectories \
  --evolved-pred runs/evolved/simplevqa_predictions.jsonl \
  --evolved-traj runs/evolved/simplevqa_trajectories \
  --output runs/simplevqa_compare_report.json
```

## 自进化机制

默认开启：

```dotenv
ENABLE_REFLECTION=1
ENABLE_MEMORY=1
MEMORY_PATH=memory/long_term_memory.jsonl
RECORD_SUCCESS_MEMORY=1
RECORD_UNGRADED_SUCCESS_MEMORY=0
```

流程：

1. `task_runner.py` 执行 ReAct 工具循环。
2. 失败时 `reflection.py` 生成失败原因、修正策略、可复用经验。
3. `memory.py` 写入长期记忆。
4. 后续任务检索相关记忆注入 prompt，但记忆只作为策略建议，不作为事实证据。

## 提交材料建议

建议保留以下产物：

```text
runs/baseline/*_predictions.jsonl
runs/baseline/*_metrics.json
runs/baseline/*_trajectories/*.jsonl
runs/evolved/*_predictions.jsonl
runs/evolved/*_metrics.json
runs/evolved/*_trajectories/*.jsonl
runs/*_compare_report.json
```

代码提交只包含 harness 和服务代码，不提交 `.env`、`data/`、`runs/`、`trajectories/`。

## 常见问题

### `SERPER_API_KEY not set`

确认 `harness-sii/.env` 中填写了 `SERPER_API_KEY`，并从 `harness-sii` 目录运行。

### `parameter.enable_thinking only support stream call`

DashScope 开启 `enable_thinking` 时必须 `stream=True`。当前 `task_runner.py` 已做流式聚合，不需要手动改。

### `Invalid type for messages.[0].content`

通常是旧轨迹污染或 message content 不是字符串/list。当前轨迹读取会序列化 dict，并且同 task-id 默认保留新文件，减少污染。

### `browser-service health check failed`

浏览器服务没启动。运行：

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/browser-service
bash run.sh
```

### `net::ERR_NAME_NOT_RESOLVED`

目标域名 DNS 解析失败，不代表 harness 崩了。浏览器工具会返回 `ok=false`，agent 会换搜索或其他证据来源。

### 2Wiki parquet 有 warning

macOS sandbox 下 pyarrow 可能打印 `sysctlbyname failed`，通常不影响读取。若 train shard 损坏，默认会跳过；validation/test 已验证可读。
