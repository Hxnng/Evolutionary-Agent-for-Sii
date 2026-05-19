# Meta-Harness 设计文档

## 1. 项目概述

基于Meta-Harness论文方法，为现有harness系统添加外循环搜索优化能力，自动发现更优的harness配置。

### 1.1 优化目标
- **数据集**：SimpleVQA（100条）+ 2WikiMultihopQA（100条）
- **评分标准**：按课程评分权重（准确率权重略提高）
- **搜索维度**：全部开放（系统提示词、反思策略、记忆检索、工具调用逻辑、上下文管理）

### 1.2 模型配置
- **Generator**：Qwen3.5-9B（基座模型，不可更改）
- **Reflector**：Qwen3-32B（反思模型）
- **Proposer**：mimo V2.5 pro（搜索优化代理）

## 2. 系统架构

### 2.1 目录结构
```
Evolutionary-Agent-for-Sii/
├── harness-sii/              # 原始harness（保持不变，作为稳定baseline）
├── meta-harness-sii/         # 新增：Meta-Harness搜索系统（harness-sii的完整副本+优化代码）
│   ├── [harness-sii的完整副本]
│   ├── meta_loop.py          # 外循环主逻辑
│   ├── proposer.py           # 提案代理（mimo V2.5 pro）
│   ├── evaluator.py          # 评估器
│   ├── filesystem.py         # 文件系统管理
│   ├── config.py             # 配置
│   ├── search_state.json     # 搜索状态（支持断点续跑）
│   ├── pareto_front.json     # 当前Pareto前沿
│   └── harnesses/            # 候选harness存储目录
│       ├── 000_baseline/
│       ├── 001_variant_1/
│       └── ...
└── browser-service/          # 现有（保持不变）
```

### 2.2 核心组件

**meta_loop.py - 外循环主逻辑**
- 管理搜索迭代（可配置上限，默认30轮，支持动态调整）
- 协调proposer和evaluator
- 实现分阶段评估策略（50→100→200条）
- 维护Pareto前沿
- 支持优雅中断和断点续跑

**proposer.py - 提案代理**
- 调用mimo V2.5 pro API（1M上下文窗口）
- 读取文件系统中的所有先前候选（代码、轨迹、分数）
- 理解失败原因，提出新harness变体
- 输出：完整的harness代码文件 + 推理过程

**evaluator.py - 评估器**
- 包装现有task_runner.py的调用接口
- 执行agent loop，收集轨迹和指标
- 计算多维度分数（准确率、token、推理轮数、工具调用、时间）
- 支持10线程并行评估

**filesystem.py - 文件系统管理**
- 每个候选harness一个目录，包含：
  - `harness.py` - harness代码
  - `scores.json` - 评估分数
  - `trajectories/` - 执行轨迹
  - `reasoning.txt` - proposer的推理过程
- 提供查询接口供proposer浏览

## 3. 数据流和反馈机制

### 3.1 反馈通道
```
Proposer读取的内容：
├── 所有候选的harness代码（完整源码）
├── 所有候选的评估分数（多维度）
├── 所有候选的执行轨迹（完整JSONL）
└── proposer自己的推理历史
```

关键设计：
- 不压缩反馈：保留完整轨迹，不做摘要
- proposer可以对比不同候选的轨迹，理解"为什么A比B好"
- 上下文管理：1M窗口足够，proposer可以选择性读取关键部分

### 3.2 初始种群生成
- 让proposer基于现有harness生成10个变体
- 变体维度：不同prompt风格、不同反思策略、不同记忆检索逻辑等
- 确保初始种群有多样性

## 4. 评估策略

### 4.1 分阶段评估

| 阶段 | 迭代范围 | 评估条数 | 目的 |
|------|----------|----------|------|
| 探索期 | 1-10轮 | 50条 | 快速筛选，广度搜索 |
| 收敛期 | 11-20轮 | 100条 | 中等精度，验证趋势 |
| 精调期 | 21-30轮 | 200条（全量） | 最终验证，精确排名 |

### 4.2 多维度评分

```python
def calculate_score(results):
    # 进化效率（35分）
    accuracy_score = ...      # 准确率提升（权重最高，略提高）
    token_score = ...         # Token优化
    reasoning_score = ...     # 推理轮数优化
    tool_score = ...          # 工具调用优化
    time_score = ...          # 推理时间优化
    
    # 最终结果（10分）
    final_accuracy = ...      # 最终准确率
    
    return weighted_sum
```

### 4.3 并行评估
- 10线程并行运行agent loop
- 浏览器API并发限制已考虑
- 每个线程独立的trajectory文件

## 5. 搜索算法

### 5.1 外循环伪代码

```python
for iteration in range(N):
    # 1. 确定当前评估规模
    eval_size = get_eval_size(iteration)  # 50→100→200
    
    # 2. Proposer读取文件系统
    context = filesystem.read_all_candidates()
    
    # 3. Proposer提出k个新候选
    new_candidates = proposer.propose(context, k=2)
    
    # 4. 并行评估
    scores = evaluator.evaluate_parallel(new_candidates, eval_size, threads=10)
    
    # 5. 存储结果到文件系统
    filesystem.store(new_candidates, scores)
    
    # 6. 更新Pareto前沿
    pareto_front.update(new_candidates, scores)
    
    # 7. 保存搜索状态（支持断点续跑）
    save_search_state(iteration, pareto_front)
```

### 5.2 迭代控制
- 迭代上限可配置（默认30，可随时修改）
- 支持优雅中断：收到终止信号时，保存当前状态，返回Pareto最优
- 支持断点续跑：从上次中断处继续搜索
- 实时输出当前最优harness（每轮迭代后）

### 5.3 Proposer提示词设计
- 角色：harness优化专家
- 输入：文件系统路径、评分标准、优化目标
- 输出：完整的harness代码 + 推理过程

## 6. API配置

### 6.1 mimo V2.5 pro API（Proposer + 临时测试用）
```python
from openai import OpenAI

# Proposer配置
proposer_client = OpenAI(
    api_key="tp-cjeqnl3h4ekv8c1oot1s6pzp0x20yq886hs5d6x6e94f83qb",
    base_url="https://token-plan-cn.xiaomimimo.com/v1"
)

# Generator/Reflector临时配置（本地无法调用Qwen时使用mimo替代）
generator_client = OpenAI(
    api_key="tp-cjeqnl3h4ekv8c1oot1s6pzp0x20yq886hs5d6x6e94f83qb",
    base_url="https://token-plan-cn.xiaomimimo.com/v1"
)
```

### 6.2 模型配置
| 角色 | 生产环境 | 测试环境（临时） |
|------|----------|------------------|
| Generator | Qwen3.5-9B | mimo-v2.5-pro |
| Reflector | Qwen3-32B | mimo-v2.5-pro |
| Proposer | mimo-v2.5-pro | mimo-v2.5-pro |

### 6.3 注意事项
- API key直接写入源码，不使用环境变量（本地开发方便）
- 测试完成后，生产环境需替换为Qwen模型配置
- 所有模型调用使用OpenAI兼容接口

## 7. 实现计划

### 7.1 第一阶段：基础框架
1. 复制harness-sii到meta-harness-sii
2. 实现filesystem.py（文件系统管理）
3. 实现config.py（配置管理）
4. 实现evaluator.py（评估器包装）

### 7.2 第二阶段：核心搜索
1. 实现proposer.py（提案代理）
2. 实现meta_loop.py（外循环主逻辑）
3. 实现初始种群生成

### 7.3 第三阶段：优化完善
1. 实现分阶段评估策略
2. 实现断点续跑功能
3. 实现Pareto前沿维护
4. 测试和调试

## 8. 风险和缓解

| 风险 | 缓解措施 |
|------|----------|
| mimo API调用失败 | 重试机制 + 备用模型 |
| 评估时间过长 | 分阶段评估 + 并行执行 |
| 搜索不收敛 | 设置最大迭代 + 早停策略 |
| 浏览器并发限制 | 限制并行线程数（10线程） |
