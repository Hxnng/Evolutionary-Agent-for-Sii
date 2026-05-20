---
skill_id: tool
title: Tool Failure Handling and Circuit Breaker
domains: tool, search, efficiency
triggers: sslerror, httpsconnectionpool, max retries exceeded, ssl: unexpected_eof, network timeout, connection refused
summary: 当搜索或浏览器工具出现SSL、连接超时或API错误时，执行熔断策略：停止重复调用，切换引擎或查询词，若仍失败则终止任务并声明无法回答。
confidence: 0.85
---
# Tool Failure Handling and Circuit Breaker

## When to use
- Trigger: 工具调用返回 SSL 错误（如 SSLError, HTTPSConnectionPool）、连接超时、最大重试次数耗尽、或网络中断。
- Context: 任何依赖外部搜索或浏览的任务阶段。

## Diagnostic Cues & Credit Assignment
- **Symptom**: 连续多次相同的工具报错（如 Max retries exceeded），或 HARNESS WARNING 提示重复调用被抑制。
- **Root Cause**: 网络环境不稳定、目标 API 暂时不可用、或查询词导致服务器拒绝连接。
- **Failure Mode**: 模型在无法获取新证据的情况下，因缺乏明确的停止信号而继续尝试相同操作，最终被迫基于猜测输出答案。

## Evidence And Tool Plan
1. **Immediate Circuit Breaker**: 一旦检测到 SSL 或连接类错误，立即停止当前查询词的重复调用。
2. **Strategy Switching**:
   - **Option A (Engine)**: 如果当前使用特定搜索引擎（如 Serper），尝试切换到备用引擎（如有）或通用搜索模式。
   - **Option B (Query Refinement)**: 简化查询词，移除可能导致过滤的复杂修饰符，或使用更通用的实体名称。
3. **Fallback Limit**: 允许最多 1 次策略切换尝试。如果再次失败，视为证据不可达。
4. **Graceful Termination**: 若所有尝试均失败，明确输出“无法回答”或“证据不足”，禁止基于假设生成答案。

## Procedure
1. **Detect Error**: 捕获工具返回中的 `SSLError`, `Max retries`, `Timeout` 等关键词。
2. **Abort Loop**: 立即停止当前的 `search_text` 或 `browser_navigate` 循环。
3. **Execute Fallback**: 
   - 尝试一次不同的搜索策略（更换引擎或重写查询）。 
   - 如果无备用引擎或策略，直接判定为证据缺失。
4. **Final Decision**: 
   - 若获得有效结果 -> 继续推理。
   - 若仍无结果 -> 输出 `<answer>Unable to determine due to network/tool failure</answer>` 或类似声明，结束任务。

## Output Format Risk
- **Critical**: 严禁在没有任何有效搜索结果的情况下，通过内部知识或猜测来填充答案。这会导致严重的幻觉和事实错误。
- **Style**: 保持冷静，清晰说明失败原因，不要试图掩盖工具故障。
