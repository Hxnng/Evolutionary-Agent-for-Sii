# Evolutionary Agent for SII

本仓库用于复现三类数据集上的 agent 评测实验：

- SimpleVQA
- 2WikiMultihopQA
- benchmark.csv

推荐统一使用 `harness-sii/evaluate_runner.py`。默认 generator 使用 OpenRouter 的 `qwen/qwen3.5-9b`，curator/reflection 使用阿里百炼的 `qwen3.5-35b-a3b`。

## 0. 评分点对应说明

本项目实现了更高维度的harness engineering，让一个agent来给予问题本身为generator来组织context，同时让reflector基于结果再来优化skills。进而实现完美闭环

原始 ReAct Agent 先在 SimpleVQA / 2Wiki 上得到 baseline，失败或低效轨迹进入 Reflection，Reflection 产出的可复用经验写入 Memory / Skill，后续任务由 Curator 基于问题本身为Generator组织Context，其中包括选择相关 skill ˙知识、解题思路、题目注意事项等等注入 Generator，从而减少无效搜索、重复工具调用和格式错误。

| 评分项 | 课题要求 | 本项目对应实现与代码位置 |
| --- | --- | --- |
| 智能体搭建 10 分 | Harness 工程 + ReAct，多轮 LLM/tool 交互，直到最大轮数或最终答案。 | 主循环在 `harness-sii/task_runner.py`；统一评测入口为 `harness-sii/evaluate_runner.py`；逐题轨迹由 `harness-sii/trajectory.py` 记录。 |
| 工具搭建 5 分 | 文搜文、图搜文、浏览器访问、页面文本抽取、并发页面处理。 | 工具 schema 与调度在 **`harness-sii/task_runner.py`**；搜索工具在 **`harness-sii/tools/search_tool.py`**，支持 `search_text` / `search_image`；浏览器工具在 **`harness-sii/tools/browser_tool.py`**，支持 `browser_navigate`、`browser_get_text`、`browser_parallel` 等；浏览器沙盒在 `browser-service/`，搜索代理在 `harness-sii/search-proxy/`。 |
| 反思模块 10 分 | 失败后自动分析原因、生成修正策略，并能影响后续任务。 | **反思 Python 文件：`harness-sii/reflection.py`**。`task_runner.py` 在任务失败、达到最大步数或低效时调用 `reflect`，将 failure reason、corrected strategy 和 skill updates 写回 learned skills；无法调用外部模型时有 deterministic fallback，保证可复现。 |
| 记忆模块 10 分 | 短期/长期记忆、结构化存储、可更新、可在后续任务调用、减少重复错误。 | **Memory Python 文件：`harness-sii/memory_store.py`**。长期 memory skill 位于 `harness-sii/*_learned_skills/general/memory.md`；短期轨迹诊断位于 `harness-sii/*_learned_skills/_memory/short_term.md`，不直接作为 skill 加载，避免把一次性答案污染长期记忆。 |
| 进化效率 35 分 | 比较进化前后准确率、token、轮数、工具调用、推理时间，并看最终 200 case 排名。 | 进化前命令使用 `--reflection off`；进化后命令使用 `--test-mode learned --reflection on --learned-skills-dir ...`。指标写入各 run 的 `metrics.json`，轨迹中保留 `total_tokens`、`tool_calls`、step_id，可分析 token、轮数和工具调用。 |
| 公开打榜 20 分 | 闭源 Agent Benchmark 结果与排名。 | 打榜提交文件已放在 `打榜_group/group_11.csv` 和 `打榜_group/group_11.json`；README 下方给出文件清单。 |
| 报告演示 10 分 | PPT 结构、技术深度、实验完整性、表达清晰。 | README 将系统架构、模块创新点、复现命令、实验结果和提交材料组织成可直接转 PPT 的结构。 |
| 加分题 0-10 分 | 可尝试蒸馏/SFT，但不得直接在 200 条 SimpleVQA、2Wiki 或打榜数据上蒸馏。 | SFT 模型链接：[gaopeilin/qwen3_5_9b_mimo25_ckpt291_merged](https://huggingface.co/gaopeilin/qwen3_5_9b_mimo25_ckpt291_merged)。 |

## 0.1 核心创新点与改进

| 部分 | 创新点 / 改进 | 主要代码位置 |
| --- | --- | --- |
| 统一评测入口 | 同一套命令覆盖 SimpleVQA、2Wiki、benchmark，并显式区分 baseline、learned skill、reflection、SFT 等实验设置。 | `harness-sii/evaluate_runner.py`，模式解析在 `harness-sii/eval_modes.py` |
| 轨迹记录 | 每道题保存 system/user/assistant/tool 的逐步 JSONL 轨迹，支持合并成课程要求的 trajectory 文件。 | `harness-sii/trajectory.py`，合并逻辑在 `harness-sii/evaluate.py`、`harness-sii/evaluate_2wiki.py`、`harness-sii/evaluate_benchmark.py` |
| Memory 解耦 | 长期 memory skill 负责稳定策略，短期 memory 只保留近期诊断；Curator 检索短期 memory 只用于路由，不把它当作事实证据。 | **`harness-sii/memory_store.py`**；`harness-sii/simplevqa_learned_skills/general/memory.md`、`harness-sii/2wiki_learned_skills/general/memory.md`、对应 `_memory/short_term.md` |
| Reflection 到 Skill | 反思不是简单重试，而是从轨迹中做 credit assignment，输出可复用 skill update。 | **`harness-sii/reflection.py`**；调用入口在 `harness-sii/task_runner.py` |
| Curator 上下文压缩 | Curator 根据题型、证据形态、答案格式风险选择少量 skill，降低上下文噪声。 | `harness-sii/curator.py`、`harness-sii/skill_store.py` |
| 工具调用约束 | 对工具调用做 schema 化、重复调用拦截、最大工具次数限制，降低 Agent 死循环概率。 | **`harness-sii/task_runner.py`**、`harness-sii/tools/search_tool.py`、`harness-sii/tools/browser_tool.py` |
| 2Wiki compact context | 将 2Wiki evidence triples / supporting sentences 压缩成 context packet，并可用 `--no-fastpath` 强制走真实 generator。 | `harness-sii/dataset_context.py`、`harness-sii/dataset_fastpath.py` |
| 提交文件整理 | 自动生成课程要求的 result/trajectory 文件名，以及结果 CSV/JSON manifest。 | `harness-sii/prepare_submission_files.py` |

当前实验结果：

| 方法 | SimpleVQA | 2wiki | 打榜 |
| --- | ---: | ---: | ---: |
| baseline | 0.2121 | 0.91 | 0.01 |
| Skill | 0.4286 | 0.96 | 0.26 |
| SFT | 0.394 | 0.72 | 0.36 |

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

### 2.1 SFT 模型

本项目另提供 SFT 模型用于加分项与对比实验：

```text
https://huggingface.co/gaopeilin/qwen3_5_9b_mimo25_ckpt291_merged
```

如果将该模型部署成 OpenAI-compatible 服务，例如 SGLang/vLLM，可在 `harness-sii/.env` 中把 generator 指向该服务：

```dotenv
GENERATOR_BASE_URL=http://127.0.0.1:8000/v1
GENERATOR_MODEL_NAME=gaopeilin/qwen3_5_9b_mimo25_ckpt291_merged
```

该 SFT 模型只用于独立对比/加分实验；按课题要求，不使用 200 条 SimpleVQA、2Wiki 评测集或打榜闭源数据进行直接蒸馏。

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

当前随仓库保留的可复现小测试集规模为：`SimpleVQA.jsonl` 99 条、`2wiki.jsonl` 100 条、`benchmark.csv` 104 条任务记录加 1 行表头。若需要严格按课题“SimpleVQA + 2Wiki 共 200 条 case”的口径复跑，请从原始数据中补齐 SimpleVQA 第 100 条后再运行同样命令；脚本和输出格式不需要改。

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

## 10. 生成课程要求的提交文件

仓库已经包含一组可复现小测试集结果，目录为：

```text
harness-sii/runs/no_reflection/simplevqa/
harness-sii/runs/no_reflection/2wiki/
harness-sii/runs/with_skill_reflection/simplevqa/
harness-sii/runs/with_skill_reflection/2wiki/
```

直接从这些 run 生成 2Wiki / SimpleVQA 进化前与进化后的 result、trajectory 文件，以及实验结果汇总 CSV/JSON：

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii

python -B prepare_submission_files.py \
  --group-id 11 \
  --output-dir submissions/group_11
```

生成文件：

```text
submissions/group_11/SimpleVQA_group_11_result.jsonl
submissions/group_11/SimpleVQA_group_11_trajectory.jsonl
submissions/group_11/2Wiki_group_11_result.jsonl
submissions/group_11/2Wiki_group_11_trajectory.jsonl
submissions/group_11/evo_SimpleVQA_group_11_result.jsonl
submissions/group_11/evo_SimpleVQA_group_11_trajectory.jsonl
submissions/group_11/evo_2Wiki_group_11_result.jsonl
submissions/group_11/evo_2Wiki_group_11_trajectory.jsonl
submissions/group_11/manifest.json
```

公开打榜闭源 Benchmark 的正式提交文件已单独放在：

```text
打榜_group/group_11.csv     # 打榜最终结果文件
打榜_group/group_11.json    # 打榜轨迹文件
```

`submissions/group_11/leaderboard_results.csv` 和 `submissions/group_11/leaderboard_results.json` 是根据实验截图整理出的结果汇总表，便于报告和 PPT 引用。

如果组号不是 11，只改 `--group-id` 和 `--output-dir` 即可，例如 `--group-id 8 --output-dir submissions/group_8`。

## 11. 从零复现并同时生成合并轨迹

下面命令会重新跑小测试集，并直接生成符合命名要求的单文件 result/trajectory。若要严格复现真实 generator 流程，2Wiki 记得保留 `--no-fastpath`。

### 进化前：SimpleVQA

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii

ENABLE_THINKING=0 python -B evaluate_runner.py \
  --dataset-name simplevqa \
  --dataset data_test/SimpleVQA.jsonl \
  --image-root data/simpleVQA/simpleVQA_datasets \
  --run-mode test \
  --reflection off \
  --output submissions/group_11/SimpleVQA_group_11_result.jsonl \
  --trajectory-output submissions/group_11/SimpleVQA_group_11_trajectory.jsonl \
  --metrics-output submissions/group_11/SimpleVQA_group_11_metrics.json \
  --traj-dir runs/no_reflection/simplevqa/trajectories \
  --workers 1
```

### 进化前：2Wiki

```bash
cd /Users/a1234/sii/Evolutionary-Agent-for-Sii/harness-sii

ENABLE_THINKING=0 python -B evaluate_runner.py \
  --dataset-name 2wiki \
  --dataset data_test/2wiki.jsonl \
  --split test \
  --run-mode test \
  --reflection off \
  --no-fastpath \
  --output submissions/group_11/2Wiki_group_11_result.jsonl \
  --trajectory-output submissions/group_11/2Wiki_group_11_trajectory.jsonl \
  --metrics-output submissions/group_11/2Wiki_group_11_metrics.json \
  --traj-dir runs/no_reflection/2wiki/trajectories \
  --workers 1
```

### 进化后：SimpleVQA

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
  --output submissions/group_11/evo_SimpleVQA_group_11_result.jsonl \
  --trajectory-output submissions/group_11/evo_SimpleVQA_group_11_trajectory.jsonl \
  --metrics-output submissions/group_11/evo_SimpleVQA_group_11_metrics.json \
  --traj-dir runs/with_skill_reflection/simplevqa/trajectories \
  --workers 1
```

### 进化后：2Wiki

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
  --output submissions/group_11/evo_2Wiki_group_11_result.jsonl \
  --trajectory-output submissions/group_11/evo_2Wiki_group_11_trajectory.jsonl \
  --metrics-output submissions/group_11/evo_2Wiki_group_11_metrics.json \
  --traj-dir runs/with_skill_reflection/2wiki/trajectories \
  --workers 1
```

## 12. 常见注意事项

- 2Wiki 真实 generator 评测必须加 `--no-fastpath`。
- OpenRouter 不稳定时先用 `--workers 1`。
- `.env` 不要提交。
- train 模式必须提前下载 Hugging Face 数据。
- `data_test/` 是仓库内的小规模复现数据，不是临时文件。
