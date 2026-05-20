# Evolutionary Agent Harness for SII

这是一个用于“自进化任务求解智能体”的实验 harness。当前系统包含：

- `generator-agent`：真正作答，固定推荐使用 OpenRouter 的 `qwen/qwen3.5-9b`。
- `curator-agent`：为每道题选择工具、context 和 skill，可继续使用百炼 `qwen3.5-35b-a3b`。
- `reflector-agent`：失败后写反思并更新 learned skills，可继续使用百炼 `qwen3.5-35b-a3b`。
- `skill_store`：把训练得到的经验保存为 Markdown skill，并在 test 时由 curator 检索。
- `evaluate_runner.py`：统一入口，用来选择数据集、train/test 模式和 reflection 模式。

本文档重点说明 SimpleVQA 和 2Wiki 的 train/test 实验流程。

## 目录结构

```text
browser-service/                  # Playwright 浏览器沙盒服务
harness-sii/
  task_runner.py                  # 单任务 ReAct 主循环
  evaluate_runner.py              # 推荐使用的统一评测入口
  evaluate.py                     # SimpleVQA 专用评测脚本
  evaluate_2wiki.py               # 2Wiki 专用评测脚本
  evaluate_benchmark.py           # benchmark.csv 专用评测脚本
  curator.py                      # curator-agent
  reflection.py                   # reflector-agent
  skill_store.py                  # Markdown skill 读写/检索
  skills/init_skill.md            # 初始 seed skill
  simplevqa_learned_skills/       # SimpleVQA 已训练 skill，可用于 test learned
  2wiki_learned_skills/           # 2Wiki 已训练 skill，可用于 test learned
  data/                           # 本地 Hugging Face 数据，已被 .gitignore 忽略
  runs/                           # 实验输出，已被 .gitignore 忽略
```

## 环境安装

```bash
conda create -n sii-harness python=3.11 -y
conda activate sii-harness
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii
pip install -r requirements.txt
```

如果要使用浏览器工具，另开一个终端启动浏览器沙盒：

```bash
conda activate sii-harness
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/browser-service
bash run.sh
```

检查浏览器服务：

```bash
curl http://127.0.0.1:8080/health
```

## 配置模型和工具

复制配置模板：

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii
cp .env.example harness-sii/.env
```

填写 `harness-sii/.env`。最小配置如下：

```dotenv
# Curator / reflector：可以继续走阿里百炼 35B。
DASHSCOPE_API_KEY=你的百炼key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=qwen3.5-35b-a3b

# Generator：只能用 qwen3.5-9b，因此走 OpenRouter。
OPENROUTER_API_KEY=你的openrouter key
GENERATOR_BASE_URL=https://openrouter.ai/api/v1
GENERATOR_MODEL_NAME=qwen/qwen3.5-9b

# 搜索工具。
SERPER_API_KEY=你的serper key
JINA_API_KEY=你的jina key

# 浏览器工具。
SANDBOX_BASE_URL=http://127.0.0.1:8080

ENABLE_SKILLS=1
ENABLE_REFLECTION=1
DISABLE_TOOLS=0
```

说明：

- `MODEL_NAME` 是 curator/reflector 默认模型，不再控制 generator。
- `GENERATOR_MODEL_NAME` 是 generator 模型，默认应为 `qwen/qwen3.5-9b`。
- `--model` 和 `--llm-url` 命令行参数现在只覆盖 generator。
- `.env` 不要提交到 git。

## 先下载 Hugging Face 数据

train 模式不会自动下载数据。运行 train 前，必须先把 Hugging Face 数据集下载到本地，并整理成本项目评测脚本需要的路径。

### 2Wiki

2Wiki 推荐直接下载 parquet 文件到 `harness-sii/data/2wiki/`：

```bash
conda activate sii-harness
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii
mkdir -p data/2wiki
huggingface-cli download framolfese/2WikiMultihopQA \
  --repo-type dataset \
  --local-dir data/2wiki \
  --include "*.parquet"
```

期望目录类似：

```text
data/2wiki/
  train-00000-of-00002.parquet
  train-00001-of-00002.parquet
  validation-00000-of-00001.parquet
  test-00000-of-00001.parquet
```

`evaluate_2wiki.py` 支持 `--split train|validation|test|all`。train shard 如果有不可读文件，默认跳过；想严格失败可加 `--strict`。

### SimpleVQA

SimpleVQA 需要先从 Hugging Face 下载原始数据，然后整理成项目使用的格式：

```text
data/simpleVQA/
  simpleVQA_train.json            # 训练用，建议自己从 HF train/validation 切分生成
  simpleVQA_test.json             # 测试用，建议固定不参与训练
  simpleVQA_final_modified.json   # 如果只有一个总文件，也可以用 limit/offset 做实验切片
  simpleVQA_datasets/
    CCSimpleQA/0.jpg
    ...
```

下载示例：

```bash
conda activate sii-harness
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii
mkdir -p data/simpleVQA_raw data/simpleVQA/simpleVQA_datasets
huggingface-cli download ohjoonhee/SimpleVQA \
  --repo-type dataset \
  --local-dir data/simpleVQA_raw
```

整理后的 JSON 每条记录至少要包含：

```json
{
  "data_id": 0,
  "question": "图中所示穴位所属的经脉是什么？",
  "answer": "足阳明胃经",
  "image": "CCSimpleQA/0.jpg"
}
```

可选字段如 `image_description`、`source`、`atomic_question`、`atomic_fact`、`vqa_category` 会被 evolved/train 模式用作非答案线索，推荐保留。图片路径相对于 `--image-root`。

如果你暂时只有 `simpleVQA_final_modified.json`，也可以先用 `--limit` 和 `--offset` 切出小规模 train/test 实验，但正式结果建议固定 train/test 文件，避免数据泄漏。

## 运行模式

统一入口是：

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii
python -B evaluate_runner.py ...
```

核心参数：

```text
--dataset-name simplevqa | 2wiki | benchmark
--run-mode train | test
--test-mode learned | from-scratch
--reflection on | off
--learned-skills-dir <dir>
```

三种主要实验模式：

| 模式 | 命令参数 | 行为 |
| --- | --- | --- |
| train | `--run-mode train --reflection on` | 从指定训练集运行，失败时 reflector 写 skill。必须先下载本地数据。 |
| test learned | `--run-mode test --test-mode learned --reflection on` | 加载训练好的 skill，在 test 集上跑当前完整方法。 |
| test no-reflection | `--run-mode test --reflection off` | 不读取训练好的 learned skill，也不写反思；只用 curator + generator。 |

重要建议：

- 如果你要训练一套新的 skill，给 `--learned-skills-dir` 指定一个新的目录，例如 `runs/simplevqa/train_skills`。
- 用训练出来的 skill 做 test learned 时，必须传同一个 `--learned-skills-dir`。
- 不传 `--learned-skills-dir` 时，test learned 会默认读取 `simplevqa_learned_skills/` 或 `2wiki_learned_skills/`。
- test no-reflection 会自动使用空的 fresh skill 目录，不会读取训练好的 skill。

## SimpleVQA 实验命令

下面假设你已经准备好：

```text
data/simpleVQA/simpleVQA_train.json
data/simpleVQA/simpleVQA_test.json
data/simpleVQA/simpleVQA_datasets/
```

### 1. train 模式

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

### 2. test learned：加载训练好的 skill

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

### 3. test no-reflection：不看 trained skill

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

如果你暂时只有总文件，可以先这样小跑：

```bash
# 前 100 条当训练切片。
python -B evaluate_runner.py \
  --dataset-name simplevqa \
  --dataset data/simpleVQA/simpleVQA_final_modified.json \
  --image-root data/simpleVQA/simpleVQA_datasets \
  --run-mode train \
  --reflection on \
  --learned-skills-dir runs/simplevqa/slice_train_skills \
  --output runs/simplevqa/slice_train/predictions.jsonl \
  --metrics-output runs/simplevqa/slice_train/metrics.json \
  --traj-dir runs/simplevqa/slice_train/trajectories \
  --limit 100 \
  --offset 0 \
  --workers 4

# 从第 1000 条开始取 100 条当测试切片。
python -B evaluate_runner.py \
  --dataset-name simplevqa \
  --dataset data/simpleVQA/simpleVQA_final_modified.json \
  --image-root data/simpleVQA/simpleVQA_datasets \
  --run-mode test \
  --test-mode learned \
  --reflection on \
  --learned-skills-dir runs/simplevqa/slice_train_skills \
  --output runs/simplevqa/slice_test_learned/predictions.jsonl \
  --metrics-output runs/simplevqa/slice_test_learned/metrics.json \
  --traj-dir runs/simplevqa/slice_test_learned/trajectories \
  --limit 100 \
  --offset 1000 \
  --workers 4
```

## 2Wiki 实验命令

下面假设你已经准备好：

```text
data/2wiki/train-*.parquet
data/2wiki/validation-*.parquet
data/2wiki/test-*.parquet
```

### 1. train 模式

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

### 2. test learned：加载训练好的 skill

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

如果你想先用 validation 代替 test 做本地调试，把 `--split test` 改成 `--split validation`。

### 3. test no-reflection：不看 trained skill

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

## 输出文件

每次运行会产生：

```text
runs/.../predictions.jsonl       # 每行一个预测
runs/.../metrics.json            # accuracy、耗时、模式、skill 目录等
runs/.../trajectories/*.jsonl    # 每道题的 system/user/assistant/tool/reflection 轨迹
```

预测 JSONL 的核心字段：

```json
{
  "index": 0,
  "instruction": "...",
  "image": "...",
  "answer": "...",
  "pred": "..."
}
```

如果要把所有单题轨迹合并成一个 JSONL，加：

```bash
--trajectory-output runs/.../trajectories.jsonl
```

## 指标汇总

单次结果汇总：

```bash
python -B metris.py \
  --pred runs/simplevqa/test_learned/predictions.jsonl \
  --traj-dir runs/simplevqa/test_learned/trajectories \
  --output runs/simplevqa/test_learned/report.json
```

对比两个模式：

```bash
python -B metris.py \
  --baseline-pred runs/simplevqa/test_no_reflection/predictions.jsonl \
  --baseline-traj runs/simplevqa/test_no_reflection/trajectories \
  --evolved-pred runs/simplevqa/test_learned/predictions.jsonl \
  --evolved-traj runs/simplevqa/test_learned/trajectories \
  --output runs/simplevqa/compare_report.json
```

## 常见问题

### train 之前必须做什么？

先从 Hugging Face 下载数据，并确认本地路径存在。train 命令只读取本地 `data/...`，不会联网自动拉数据集。

### train 出来的 skill 在哪里？

看你传的 `--learned-skills-dir`。例如：

```text
runs/simplevqa/train_skills/
  SKILL.md
  general/memory.md
  ...
```

test learned 必须传同一个目录，才能评估这次训练得到的 skill。

### test no-reflection 到底关了什么？

它会关闭 reflector 写反思，也不会读取训练好的 learned skill。generator 仍然会通过 curator 获得当前题目的结构化 context 和工具计划。

### 2Wiki parquet 报 pyarrow warning 怎么办？

macOS 下可能看到 `sysctlbyname failed`，通常不影响读取。如果缺 pyarrow：

```bash
pip install -r requirements.txt
```

### OpenRouter generator 调不通怎么办？

检查：

```dotenv
OPENROUTER_API_KEY=...
GENERATOR_BASE_URL=https://openrouter.ai/api/v1
GENERATOR_MODEL_NAME=qwen/qwen3.5-9b
```

并确认没有在命令行里误传 `--model qwen3.5-35b-a3b`。

### 搜索不可用怎么办？

先测试：

```bash
python -B tools/search_tool.py text "上海创智学院 谢源老师 代表作" --top-k 1 --no-fetch
```

如果缺 key，补 `SERPER_API_KEY` 和 `JINA_API_KEY`。
