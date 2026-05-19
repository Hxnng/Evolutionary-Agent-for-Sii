# Harness SII Quickstart

主说明见仓库根目录 [README.md](../README.md)。本文件只保留最常用命令。

## 配置

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii
cp .env.example harness-sii/.env
```

填写 `harness-sii/.env`：

```dotenv
DASHSCOPE_API_KEY=你的百炼key
MODEL_NAME=qwen3.5-35b-a3b
SERPER_API_KEY=你的serper key
JINA_API_KEY=你的jina key
SANDBOX_BASE_URL=http://127.0.0.1:8080
```

如需搜索代理：

```dotenv
SEARCH_PROXY_URL=http://127.0.0.1:8090
SEARCH_PROXY_TOKEN=
SEARCH_PROXY_FALLBACK=1
```

## 自检

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii
python -B tools/search_tool.py text "上海创智学院 谢源老师 代表作" --top-k 1 --no-fetch
```

输出 `[mode] direct` 表示直连；输出 `[mode] proxy` 表示正在走 `search-proxy`。

## 浏览器服务

另开终端：

```bash
conda activate sii-harness
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/browser-service
bash run.sh
```

检查：

```bash
curl http://127.0.0.1:8080/health
```

## 单任务

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii
python -B task_runner.py \
  --instruction "请查询上海创智学院谢源老师的代表作。" \
  --task-id smoke_001 \
  --traj-dir trajectories \
  --max-steps 8
```

轨迹默认保留历史运行；重复 `task-id` 会生成带时间戳的新 JSONL。需要覆盖时加 `--overwrite-traj`。

## SimpleVQA

```bash
python -B evaluate.py \
  --dataset data/simpleVQA/simpleVQA_final_modified.json \
  --image-root data/simpleVQA/simpleVQA_datasets \
  --output runs/evolved/simplevqa_predictions.jsonl \
  --metrics-output runs/evolved/simplevqa_metrics.json \
  --traj-dir runs/evolved/simplevqa_trajectories \
  --split-name simplevqa \
  --limit 20
```

## 2Wiki

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

## benchmark.csv

```bash
python -B evaluate_benchmark.py \
  --dataset data/benchmark.csv \
  --output runs/evolved/benchmark_predictions.jsonl \
  --metrics-output runs/evolved/benchmark_metrics.json \
  --traj-dir runs/evolved/benchmark_trajectories \
  --split-name benchmark
```

## Metrics

```bash
python -B metris.py \
  --pred runs/evolved/simplevqa_predictions.jsonl \
  --traj-dir runs/evolved/simplevqa_trajectories \
  --output runs/evolved/simplevqa_report.json
```
