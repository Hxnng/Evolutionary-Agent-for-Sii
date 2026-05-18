# Harness SII

本目录是考核主体实现。推荐从仓库根目录 README 开始阅读；这里保留最短测试流程。

## 配置

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii
cp .env.example harness-sii/.env
```

编辑 `harness-sii/.env`，填写：

```dotenv
DASHSCOPE_API_KEY=你的百炼key
SERPER_API_KEY=你的serper key
JINA_API_KEY=你的jina key
MODEL_NAME=qwen3.5-35b-a3b
```

## 搜索自检

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii
python -B tools/search_tool.py text "上海创智学院 谢源老师 代表作" --top-k 1 --no-fetch
```

## 启动浏览器服务

另开终端：

```bash
conda activate sii-harness
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/browser-service
bash run.sh
```

健康检查：

```bash
curl http://127.0.0.1:8080/health
```

## Agent Smoke Test

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii
python -B task_runner.py \
  --instruction "请查询上海创智学院谢源老师的代表作。" \
  --task-id smoke_001 \
  --traj-dir trajectories \
  --max-steps 8
```

轨迹文件按 `--task-id` 命名，并默认保留历史运行。若
`trajectories/smoke_001.jsonl` 已存在，新运行会自动写入类似
`trajectories/smoke_001_20260519_001234.jsonl` 的文件。只有显式加
`--overwrite-traj` 时才会覆盖 `<task-id>.jsonl`。

## Benchmark 输出

```bash
python -B evaluate.py \
  --dataset ../datasets/simplevqa_100.jsonl \
  --output runs/evolved/simplevqa_predictions.jsonl \
  --metrics-output runs/evolved/simplevqa_metrics.json \
  --traj-dir runs/evolved/simplevqa_trajectories \
  --split-name simplevqa
```

预测 JSONL 每行包含：

```json
{"index": 0, "task_id": "simplevqa_0", "instruction": "...", "image": "", "answer": "...", "pred": "...", "success": true, "steps": 4, "trajectory_path": "..."}
```

## 主要文件

- `task_runner.py`：ReAct 主循环、百炼流式调用、工具分发、轨迹、反思/记忆闭环。
- `tools/search_tool.py`：Serper 文搜文、Serper Lens 图搜文、Jina 正文抽取。
- `tools/browser_tool.py`：浏览器沙盒工具；服务不可用时有 HTTP fallback。
- `reflection.py`：失败反思。
- `memory.py`：长期记忆 JSONL。
- `evaluate.py`：SimpleVQA / 2Wiki 风格批量评测。
