# Evolutionary Agent for SII

本仓库用于复现三类数据集上的 agent 评测实验：

- SimpleVQA
- 2WikiMultihopQA
- benchmark.csv

推荐统一使用 `harness-sii/evaluate_runner.py`。默认 generator 使用 OpenRouter 的 `qwen/qwen3.5-9b`，curator/reflection 使用阿里百炼的 `qwen3.5-35b-a3b`。

## 1. 创建环境

```bash
conda create -n sii-harness python=3.11 -y
conda activate sii-harness

cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii
pip install -r requirements.txt
```

## 2. 配置密钥

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii
cp .env.example harness-sii/.env
```

编辑 `harness-sii/.env`，至少填写：

```dotenv
DASHSCOPE_API_KEY=你的百炼key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=qwen3.5-35b-a3b

OPENROUTER_API_KEY=你的OpenRouter key
GENERATOR_BASE_URL=https://openrouter.ai/api/v1
GENERATOR_MODEL_NAME=qwen/qwen3.5-9b

SERPER_API_KEY=你的Serper key
JINA_API_KEY=你的Jina key

SANDBOX_BASE_URL=http://127.0.0.1:8080
DISABLE_TOOLS=0
ENABLE_SKILLS=1
ENABLE_REFLECTION=1
```

运行 OpenRouter generator 时建议在命令前加 `ENABLE_THINKING=0`，避免 OpenRouter 流式返回不稳定。

## 3. 启动浏览器服务

需要浏览器工具时，另开一个终端：

```bash
conda activate sii-harness
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/browser-service
bash run.sh
```

检查服务：

```bash
curl http://127.0.0.1:8080/health
```

## 4. 准备数据

### 4.1 已随仓库保留的小测试集

用于快速复现的测试文件在：

```text
harness-sii/data_test/SimpleVQA.jsonl
harness-sii/data_test/2wiki.jsonl
harness-sii/data_test/benchmark.csv
```

下面的 test 命令默认使用这三个文件。

### 4.2 train 模式必须先下载 Hugging Face 数据

train 不会自动下载数据。运行 train 前，先把 Hugging Face 数据下载到 `harness-sii/data/`。

2Wiki：

```bash
conda activate sii-harness
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii
mkdir -p data/2wiki
huggingface-cli download framolfese/2WikiMultihopQA \
  --repo-type dataset \
  --local-dir data/2wiki \
  --include "*.parquet"
```

期望文件：

```text
data/2wiki/train-*.parquet
data/2wiki/validation-*.parquet
data/2wiki/test-*.parquet
```

SimpleVQA：

```bash
conda activate sii-harness
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii
mkdir -p data/simpleVQA_raw data/simpleVQA/simpleVQA_datasets
huggingface-cli download ohjoonhee/SimpleVQA \
  --repo-type dataset \
  --local-dir data/simpleVQA_raw
```

整理后建议固定为：

```text
data/simpleVQA/simpleVQA_train.json
data/simpleVQA/simpleVQA_test.json
data/simpleVQA/simpleVQA_datasets/
```

SimpleVQA 每条记录至少包含：

```json
{"question": "...", "answer": "...", "image": "relative/path.jpg"}
```

`image` 路径相对于命令中的 `--image-root`。

## 5. 评测口径

当前 accuracy 使用严格匹配：

```text
normalize(pred) == normalize(answer)
```

归一化只做大小写、空白、标点、HTML tag 和中文年份后缀等基础清理；不会把语义近似答案自动判为正确。

## 6. 测试：无 learned skill、无 reflection

### SimpleVQA

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii

ENABLE_THINKING=0 python -B evaluate_runner.py \
  --dataset-name simplevqa \
  --dataset data_test/SimpleVQA.jsonl \
  --image-root data/simpleVQA/simpleVQA_datasets \
  --run-mode test \
  --reflection off \
  --output runs/no_reflection/simplevqa/predictions.jsonl \
  --metrics-output runs/no_reflection/simplevqa/metrics.json \
  --traj-dir runs/no_reflection/simplevqa/trajectories \
  --workers 1
```

### 2Wiki

必须加 `--no-fastpath`，否则会从数据中的 evidence 直接规则解答，不能复现真实 generator 流程。

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii

ENABLE_THINKING=0 python -B evaluate_runner.py \
  --dataset-name 2wiki \
  --dataset data_test/2wiki.jsonl \
  --split test \
  --run-mode test \
  --reflection off \
  --no-fastpath \
  --output runs/no_reflection/2wiki/predictions.jsonl \
  --metrics-output runs/no_reflection/2wiki/metrics.json \
  --traj-dir runs/no_reflection/2wiki/trajectories \
  --workers 1
```

### Benchmark

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii

ENABLE_THINKING=0 python -B evaluate_runner.py \
  --dataset-name benchmark \
  --dataset data_test/benchmark.csv \
  --run-mode test \
  --reflection off \
  --output runs/no_reflection/benchmark/predictions.jsonl \
  --metrics-output runs/no_reflection/benchmark/metrics.json \
  --traj-dir runs/no_reflection/benchmark/trajectories \
  --workers 1
```

## 7. 测试：加载 learned skill、开启 reflection

### SimpleVQA

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii

ENABLE_THINKING=0 python -B evaluate_runner.py \
  --dataset-name simplevqa \
  --dataset data_test/SimpleVQA.jsonl \
  --image-root data/simpleVQA/simpleVQA_datasets \
  --run-mode test \
  --test-mode learned \
  --reflection on \
  --learned-skills-dir simplevqa_learned_skills \
  --output runs/with_skill_reflection/simplevqa/predictions.jsonl \
  --metrics-output runs/with_skill_reflection/simplevqa/metrics.json \
  --traj-dir runs/with_skill_reflection/simplevqa/trajectories \
  --workers 1
```

### 2Wiki

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii

ENABLE_THINKING=0 python -B evaluate_runner.py \
  --dataset-name 2wiki \
  --dataset data_test/2wiki.jsonl \
  --split test \
  --run-mode test \
  --test-mode learned \
  --reflection on \
  --learned-skills-dir 2wiki_learned_skills \
  --no-fastpath \
  --output runs/with_skill_reflection/2wiki/predictions.jsonl \
  --metrics-output runs/with_skill_reflection/2wiki/metrics.json \
  --traj-dir runs/with_skill_reflection/2wiki/trajectories \
  --workers 1
```

### Benchmark

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii

ENABLE_THINKING=0 python -B evaluate_runner.py \
  --dataset-name benchmark \
  --dataset data_test/benchmark.csv \
  --run-mode test \
  --test-mode learned \
  --reflection on \
  --learned-skills-dir benchmark_learned_skills \
  --output runs/with_skill_reflection/benchmark/predictions.jsonl \
  --metrics-output runs/with_skill_reflection/benchmark/metrics.json \
  --traj-dir runs/with_skill_reflection/benchmark/trajectories \
  --workers 1
```

## 8. 训练 skill

训练会在失败样本上触发 reflection，并把经验写入 `--learned-skills-dir`。

### SimpleVQA train

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii

ENABLE_THINKING=0 python -B evaluate_runner.py \
  --dataset-name simplevqa \
  --dataset data/simpleVQA/simpleVQA_train.json \
  --image-root data/simpleVQA/simpleVQA_datasets \
  --run-mode train \
  --reflection on \
  --learned-skills-dir runs/train_skills/simplevqa \
  --output runs/train/simplevqa/predictions.jsonl \
  --metrics-output runs/train/simplevqa/metrics.json \
  --traj-dir runs/train/simplevqa/trajectories \
  --workers 1
```

### 2Wiki train

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii

ENABLE_THINKING=0 python -B evaluate_runner.py \
  --dataset-name 2wiki \
  --dataset data/2wiki \
  --split train \
  --run-mode train \
  --reflection on \
  --learned-skills-dir runs/train_skills/2wiki \
  --no-fastpath \
  --output runs/train/2wiki/predictions.jsonl \
  --metrics-output runs/train/2wiki/metrics.json \
  --traj-dir runs/train/2wiki/trajectories \
  --workers 1
```

test 使用训练得到的 skill 时，传同一个目录：

```bash
--learned-skills-dir runs/train_skills/2wiki
```

## 9. 输出文件

每次运行都会生成：

```text
predictions.jsonl   # 每条样本的 pred/answer
metrics.json        # total/correct/accuracy/elapsed_sec
trajectories/       # 每条样本的交互轨迹
```

重新复现实验时建议删除旧输出目录，避免混淆：

```bash
rm -rf runs/no_reflection/2wiki
```

## 10. 常见注意事项

- 2Wiki 真实 generator 评测必须加 `--no-fastpath`。
- OpenRouter 不稳定时先用 `--workers 1`。
- `.env` 不要提交。
- train 模式必须提前下载 Hugging Face 数据。
- `data_test/` 是仓库内的小规模复现数据，不是临时文件。
