# Meta-Harness

基于Meta-Harness论文方法的harness自动优化系统。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行Meta-Harness

```bash
./run_meta_harness.sh
```

或者直接运行Python脚本：

```bash
python meta_loop.py
```

### 3. 查看结果

搜索完成后，结果保存在：
- `harnesses/` - 所有候选harness
- `pareto_front.json` - Pareto前沿
- `search_state.json` - 搜索状态

## 配置

配置在 `config.py` 中，包括：
- API配置（mimo V2.5 pro）
- 搜索参数（迭代次数、评估规模等）
- 数据集路径
- 评分权重

## 目录结构

```
meta-harness-sii/
├── meta_loop.py          # 外循环主逻辑
├── proposer.py           # 提案代理
├── evaluator.py          # 评估器
├── evaluate.py           # 评估脚本
├── evaluate_2wiki.py     # 2Wiki评估脚本
├── evaluate_benchmark.py # 基准评估脚本
├── filesystem.py         # 文件系统管理
├── config.py             # 配置
├── task_runner.py        # 任务运行器
├── requirements.txt      # 依赖列表
├── test_meta_harness.py  # 测试脚本
├── run_meta_harness.sh   # 启动脚本
├── harnesses/            # 候选harness存储
├── test_harnesses/       # 测试harness存储
├── trajectories/         # 轨迹存储
├── search_state.json     # 搜索状态
└── pareto_front.json     # Pareto前沿
```

## 评分标准

按课程评分权重：
- 准确率提升（权重最高）
- Token优化
- 推理轮数优化
- 工具调用优化
- 推理时间优化

## 打榜提交

### 生成提交文件

```bash
# 运行benchmark评估并生成提交文件（组号为11）
python evaluate_benchmark.py \
    --dataset /inspire/qb-ilm2/project/26summer-camp-01/public/benchmark.csv \
    --output benchmark_output.jsonl \
    --traj-dir trajectories/ \
    --workers 4 \
    --group-number 11 \
    --submission-dir submission/
```

### 提交文件格式

生成的文件在 `submission/` 目录：
- `group_11.json` - 轨迹文件（包含每个问题的完整推理轨迹）
- `group_11.csv` - 答案文件（包含index, problem, image, answer列）
- `group_11.zip` - 压缩文件（提交此文件）

### CSV格式说明

`group_11.csv` 格式：
```csv
index,problem,image,answer
0,问题内容,图片路径,Agent的答案
1,问题内容,图片路径,Agent的答案
...
```

## 网络配置（GPU节点无法上网）

由于GPU节点无法上网，需要通过CPU节点代理访问mimo API：

### 1. 在CPU节点上启动mimo-proxy

```bash
cd harness-sii/mimo-proxy
bash run.sh
```

### 2. 在GPU节点上设置SSH端口转发

```bash
ssh -L 8080:localhost:8080 cpu-node
```

### 3. 测试连接

```bash
curl http://localhost:8080/health
```

### 4. 运行Meta-Harness

config.py已配置为使用mimo-proxy（`http://localhost:8080/v1`），直接运行即可。

## 注意事项

1. 测试环境使用mimo-v2.5-pro替代Qwen模型
2. 支持断点续跑，可随时中断并恢复
3. 分阶段评估：50→100→200条
4. 打榜数据路径：`/inspire/qb-ilm2/project/26summer-camp-01/public/benchmark.csv`
