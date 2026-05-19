# Meta-Harness

基于Meta-Harness论文方法的harness自动优化系统。

## 快速开始

### 1. 安装依赖

```bash
pip install openai
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
├── filesystem.py         # 文件系统管理
├── config.py             # 配置
├── test_meta_harness.py  # 测试脚本
├── run_meta_harness.sh   # 启动脚本
├── harnesses/            # 候选harness存储
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

## 注意事项

1. API key已写入源码，无需设置环境变量
2. 测试环境使用mimo-v2.5-pro替代Qwen模型
3. 支持断点续跑，可随时中断并恢复
4. 分阶段评估：50→100→200条
