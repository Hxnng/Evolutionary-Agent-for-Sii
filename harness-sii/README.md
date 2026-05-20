# Harness SII Quickstart

主说明见仓库根目录 [README.md](../README.md)。本文件保留最常用的本地运行命令。

## 1. 配置

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii
cp .env.example harness-sii/.env
```

填写 `harness-sii/.env`：

```dotenv
# Curator / reflector：百炼 35B。
DASHSCOPE_API_KEY=你的百炼key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=qwen3.5-35b-a3b

# Generator：OpenRouter qwen3.5-9b。
OPENROUTER_API_KEY=你的openrouter key
GENERATOR_BASE_URL=https://openrouter.ai/api/v1
GENERATOR_MODEL_NAME=qwen/qwen3.5-9b

SERPER_API_KEY=你的serper key
JINA_API_KEY=你的jina key
SANDBOX_BASE_URL=http://127.0.0.1:8080
ENABLE_SKILLS=1
ENABLE_REFLECTION=1
DISABLE_TOOLS=0
```

## 2. 先下载 Hugging Face 数据

train 模式不会自动下载数据。必须先把数据放到本地 `data/`。

### 2Wiki

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii
mkdir -p data/2wiki
huggingface-cli download framolfese/2WikiMultihopQA \
  --repo-type dataset \
  --local-dir data/2wiki \
  --include "*.parquet"
```

期望有：

```text
data/2wiki/train-*.parquet
data/2wiki/validation-*.parquet
data/2wiki/test-*.parquet
```

### SimpleVQA

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii
mkdir -p data/simpleVQA_raw data/simpleVQA/simpleVQA_datasets
huggingface-cli download ohjoonhee/SimpleVQA \
  --repo-type dataset \
  --local-dir data/simpleVQA_raw
```

然后整理成评测脚本需要的格式：

```text
data/simpleVQA/simpleVQA_train.json
data/simpleVQA/simpleVQA_test.json
data/simpleVQA/simpleVQA_datasets/...
```

SimpleVQA JSON 每条至少包含 `question`、`answer`、`image`。图片路径相对于 `--image-root`。

## 3. 自检

```bash
python -B tools/search_tool.py text "上海创智学院 谢源老师 代表作" --top-k 1 --no-fetch
```

输出 `[mode] direct` 表示直连；输出 `[mode] proxy` 表示正在走 `search-proxy`。

浏览器服务另开终端：

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/browser-service
bash run.sh
```

检查：

```bash
curl http://127.0.0.1:8080/health
```

## 4. 运行模式

推荐统一用：

```bash
python -B evaluate_runner.py ...
```

三种主要模式：

```text
train:
  --run-mode train --reflection on
  从训练集开始跑，失败时写 skill。

test learned:
  --run-mode test --test-mode learned --reflection on
  加载训练好的 skill，在 test 集上跑完整方法。

test no-reflection:
  --run-mode test --reflection off
  不读取训练好的 skill，也不写反思，只跑 curator + generator。
```

如果 train 得到的 skill 要给 test learned 使用，请两次都传同一个 `--learned-skills-dir`。

## 5. SimpleVQA 三种实验

### train

```bash
python -B evaluate_runner.py \
  --dataset-name simplevqa \
  --dataset data/simpleVQA/simpleVQA_train.json \
  --image-root data/simpleVQA/simpleVQA_datasets \
  --run-mode train \
  --reflection on \
  --learned-skills-dir runs/simplevqa/train_skills \
  --output runs/simplevqa/train/predictions.jsonl \
  --metrics-output runs/simplevqa/train/metrics.json \
  --traj-dir runs/simplevqa/train/trajectories \
  --limit 100 \
  --workers 4
```

### test learned

```bash
python -B evaluate_runner.py \
  --dataset-name simplevqa \
  --dataset data/simpleVQA/simpleVQA_test.json \
  --image-root data/simpleVQA/simpleVQA_datasets \
  --run-mode test \
  --test-mode learned \
  --reflection on \
  --learned-skills-dir runs/simplevqa/train_skills \
  --output runs/simplevqa/test_learned/predictions.jsonl \
  --metrics-output runs/simplevqa/test_learned/metrics.json \
  --traj-dir runs/simplevqa/test_learned/trajectories \
  --limit 100 \
  --workers 4
```

### test no-reflection

```bash
python -B evaluate_runner.py \
  --dataset-name simplevqa \
  --dataset data/simpleVQA/simpleVQA_test.json \
  --image-root data/simpleVQA/simpleVQA_datasets \
  --run-mode test \
  --reflection off \
  --output runs/simplevqa/test_no_reflection/predictions.jsonl \
  --metrics-output runs/simplevqa/test_no_reflection/metrics.json \
  --traj-dir runs/simplevqa/test_no_reflection/trajectories \
  --limit 100 \
  --workers 4
```

如果你只有 `simpleVQA_final_modified.json`，可以临时用 `--offset` 和 `--limit` 切片调试；正式结果建议使用固定的 train/test 文件。

## 6. 2Wiki 三种实验

### train

```bash
python -B evaluate_runner.py \
  --dataset-name 2wiki \
  --dataset data/2wiki \
  --split train \
  --run-mode train \
  --reflection on \
  --learned-skills-dir runs/2wiki/train_skills \
  --output runs/2wiki/train/predictions.jsonl \
  --metrics-output runs/2wiki/train/metrics.json \
  --traj-dir runs/2wiki/train/trajectories \
  --limit 100 \
  --workers 4
```

### test learned

```bash
python -B evaluate_runner.py \
  --dataset-name 2wiki \
  --dataset data/2wiki \
  --split test \
  --run-mode test \
  --test-mode learned \
  --reflection on \
  --learned-skills-dir runs/2wiki/train_skills \
  --output runs/2wiki/test_learned/predictions.jsonl \
  --metrics-output runs/2wiki/test_learned/metrics.json \
  --traj-dir runs/2wiki/test_learned/trajectories \
  --limit 100 \
  --workers 4
```

### test no-reflection

```bash
python -B evaluate_runner.py \
  --dataset-name 2wiki \
  --dataset data/2wiki \
  --split test \
  --run-mode test \
  --reflection off \
  --output runs/2wiki/test_no_reflection/predictions.jsonl \
  --metrics-output runs/2wiki/test_no_reflection/metrics.json \
  --traj-dir runs/2wiki/test_no_reflection/trajectories \
  --limit 100 \
  --workers 4
```

本地调试时可以把 `--split test` 改成 `--split validation`。

## 7. 指标汇总

```bash
python -B metris.py \
  --pred runs/simplevqa/test_learned/predictions.jsonl \
  --traj-dir runs/simplevqa/test_learned/trajectories \
  --output runs/simplevqa/test_learned/report.json
```

对比 learned 和 no-reflection：

```bash
python -B metris.py \
  --baseline-pred runs/simplevqa/test_no_reflection/predictions.jsonl \
  --baseline-traj runs/simplevqa/test_no_reflection/trajectories \
  --evolved-pred runs/simplevqa/test_learned/predictions.jsonl \
  --evolved-traj runs/simplevqa/test_learned/trajectories \
  --output runs/simplevqa/compare_report.json
```
