# Evolutionary Agent Harness for SII

这是一个面向“自进化的任务求解智能体”课题的最小可运行 Harness。当前版本已经按本机调通路径收敛为：

- 模型：阿里云百炼 OpenAI-compatible API，默认 `qwen3.5-35b-a3b`，流式开启 thinking。
- 搜索：只使用 `SERPER_API_KEY` + `JINA_API_KEY` 直连。
- 浏览器：优先使用 `browser-service` 沙盒；未启动时，`browser_navigate` 会用 HTTP fallback 抓页面文本。
- 进化闭环：失败反思、长期记忆、后续任务记忆注入。
- 评测产物：预测 JSONL 与逐任务轨迹 JSONL。

## 目录

```text
harness-sii/
  task_runner.py          # ReAct 主循环、百炼调用、工具分发、轨迹、反思/记忆闭环
  tools/search_tool.py    # Serper 文搜文、Serper Lens 图搜文、Jina 正文抽取
  tools/browser_tool.py   # 浏览器沙盒工具；服务不可用时可 HTTP fallback
  trajectory.py           # JSONL 轨迹写入/读取
  reflection.py           # 失败反思模块
  memory.py               # 长期记忆 JSONL 检索与写入
  evaluate.py             # SimpleVQA / 2Wiki 风格批量评测入口
browser-service/          # 官方浏览器沙盒服务
```

## 1. 环境安装

推荐使用 miniconda：

```bash
conda create -n sii-harness python=3.11 -y
conda activate sii-harness
cd ./harness-sii
pip install -r requirements.txt
```

如果要启用浏览器沙盒，还需要安装 browser-service 依赖。第一次运行 `browser-service/run.sh` 会自动安装依赖和 Playwright Chromium。

## 2. 配置 `.env`

复制模板并填写 key：

```bash
cd ./Evolutionary-Agent-for-Sii
cp .env.example harness-sii/.env
```

编辑 `harness-sii/.env`：

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

注意：`harness-sii/.env` 含真实 key，不要提交到 Git。项目的 `.gitignore` 已忽略 `.env`。

## 3. 单工具自检

先测搜索工具，确认 Serper/Jina 可用：

```bash
cd ./Evolutionary-Agent-for-Sii/harness-sii
python -B tools/search_tool.py text "上海创智学院 谢源老师 代表作" --top-k 1 --no-fetch
```

正常输出应包含：

```text
[mode] direct
```

并返回至少一条搜索结果。

## 4. 启动浏览器沙盒

正式评测建议启动浏览器服务。另开一个终端：

```bash
conda activate sii-harness
cd ./Evolutionary-Agent-for-Sii/browser-service
bash run.sh
```

成功时会看到：

```text
Chromium runtime OK.
Starting browser service on 0.0.0.0:8080
Uvicorn running on http://0.0.0.0:8080
```

再开一个终端检查：

```bash
curl http://127.0.0.1:8080/health
```

应返回类似：

```json
{"status":"ok","browser_running":true,"sessions":0}
```

如果暂时不启动 browser-service，Agent 仍可通过 HTTP fallback 抓取普通网页文本，但点击、输入、多标签等完整浏览器能力需要服务运行。

## 5. 完整 Agent Smoke Test

```bash
cd ./Evolutionary-Agent-for-Sii/harness-sii
python -B task_runner.py \
  --instruction "请查询上海创智学院谢源老师的代表作。" \
  --task-id smoke_001 \
  --traj-dir trajectories \
  --max-steps 8
```

检查点：

- 日志出现 `tool_call: search_text(...)`。
- 搜索模式为 `search_text(direct)`。
- 如果 browser-service 已启动，浏览器工具应正常连接 `127.0.0.1:8080`。
- 最终输出包含 `<answer>...</answer>`。
- 轨迹写入 `harness-sii/trajectories/smoke_001.jsonl`；如果该文件已存在，会自动写入带时间戳的新文件以保留旧轨迹。需要强制覆盖时加 `--overwrite-traj`。

## 6. 图片任务示例

```bash
python -B task_runner.py \
  --instruction "请识别图中的城市，并查询该城市所在国家的首都名称。" \
  --image ./123.jpg \
  --image-url "https://example.com/123.jpg" \
  --task-id simplevqa_001 \
  --traj-dir trajectories \
  --max-steps 8
```

本地图像会以 base64 传给多模态模型；图搜文工具需要公网图片 URL 或可上传的本地图片。

## 7. 批量评测

批量入口：`harness-sii/evaluate.py`。

支持字段名：

- 问题：`instruction`、`question`、`query`、`input`、`prompt`
- 答案：`answer`、`gold`、`label`、`target`
- 图片：`image`、`image_path`、`image_url`、`img`

无进化基线：

```bash
cd ./Evolutionary-Agent-for-Sii/harness-sii
python -B evaluate.py \
  --dataset ../datasets/simplevqa_100.jsonl \
  --output runs/baseline/simplevqa_predictions.jsonl \
  --metrics-output runs/baseline/simplevqa_metrics.json \
  --traj-dir runs/baseline/simplevqa_trajectories \
  --split-name simplevqa \
  --baseline
```

带反思和记忆的最终版：

```bash
python -B evaluate.py \
  --dataset ../datasets/simplevqa_100.jsonl \
  --output runs/evolved/simplevqa_predictions.jsonl \
  --metrics-output runs/evolved/simplevqa_metrics.json \
  --traj-dir runs/evolved/simplevqa_trajectories \
  --split-name simplevqa
```

2Wiki 同理替换 `--dataset`、`--output`、`--traj-dir`。

输出预测 JSONL 格式：

```json
{"index": 0, "task_id": "simplevqa_0", "instruction": "...", "image": "", "answer": "...", "pred": "...", "success": true, "steps": 4, "trajectory_path": "..."}
```

每个任务的完整轨迹单独保存为 JSONL，包含 system/user/assistant/tool/reflection 等记录。`--metrics-output` 会额外写出总样本数、正确数、准确率、耗时和运行模式，方便 baseline/evolved 对比。

## 8. 反思与记忆

默认开启：

```dotenv
ENABLE_REFLECTION=1
ENABLE_MEMORY=1
MEMORY_PATH=memory/long_term_memory.jsonl
RECORD_SUCCESS_MEMORY=1
```

机制：

1. 每个任务先运行 ReAct 工具循环。
2. 若失败，`reflection.py` 分析失败原因和修正策略。
3. `memory.py` 将经验写入长期 JSONL。
4. 后续任务会检索相关记忆并注入 system prompt。

如只想记录失败经验：

```dotenv
RECORD_SUCCESS_MEMORY=0
```

## 9. 提交材料对应关系

课题要求的材料可以从以下位置生成：

- 原始结果 JSONL：`runs/baseline/*_predictions.jsonl`
- 最终结果 JSONL：`runs/evolved/*_predictions.jsonl`
- 所有轨迹 JSONL：`runs/*/*_trajectories/*.jsonl`
- 系统整体代码：本仓库
- 打榜结果 JSONL：使用同一 `evaluate.py` 入口替换为闭源 benchmark 数据

正式提交前建议检查：

```bash
find runs -name '*predictions.jsonl' -print
find runs -name '*.jsonl' | head
python -B -m py_compile harness-sii/*.py harness-sii/tools/*.py
```

## 10. 常见问题

### `SERPER_API_KEY not set`

确认 `harness-sii/.env` 中填写了 `SERPER_API_KEY`，并从 `harness-sii` 目录运行命令。`tools/search_tool.py` 会自动读取该文件。

### `browser-service health check failed`

说明浏览器服务没有启动。运行：

```bash
cd ./Evolutionary-Agent-for-Sii/browser-service
bash run.sh
```

### `permission denied: ./run.sh`

脚本没有执行权限时使用：

```bash
bash run.sh
```

### Playwright Chromium 启动失败

重新安装浏览器：

```bash
conda activate sii-harness
python -m playwright install chromium
```

### 百炼报 `enable_thinking only support stream call`

当前 `task_runner.py` 已使用 `stream=True` 聚合百炼输出。不要关闭 `ENABLE_THINKING=1`，除非你切到不支持 thinking 的模型；需要关闭时设置：

```dotenv
ENABLE_THINKING=0
```
