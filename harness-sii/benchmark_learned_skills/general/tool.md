---
skill_id: tool
title: Tool Failure Handling and Budget Management
domains: tool, search, efficiency
triggers: sslerror, httpsconnectionpool, max retries exceeded, network timeout, browser unavailable, 403 forbidden, budget exhausted
summary: Protocol for handling tool failures (SSL, timeouts, 403s) and managing tool budget to prevent premature task termination.
confidence: 0.65
---
# Tool Failure Handling and Budget Management

## When to use
- Any situation where a tool call (`search_text`, `browser_navigate`) returns an error, times out, or the system warns about budget exhaustion.
- Trigger: Specific error messages (SSL, 403, 502, Timeout) or explicit budget warnings.

## Diagnostic Cues & Credit Assignment
- **Failure Mode**: Repeatedly calling a failing tool (e.g., navigating to a blocked URL) consumes budget without progress.
- **Root Cause**: Lack of a "circuit breaker" strategy that switches tactics upon the first failure signal.
- **Correction**: Implement immediate fallback logic: Stop the failing tool, switch query engine/source, or accept partial evidence from snippets.

## Evidence And Tool Plan
1. **Error Classification**:
   - **Network/Access Errors (403, 502, SSL)**: Indicates the target resource is blocked or unreachable via current method. **Action**: Do NOT retry the same URL. Switch to alternative sources or rely on cached snippets.
   - **Timeouts**: Indicates slow response. **Action**: Reduce complexity of query or switch to a faster search engine.
   - **Budget Exhaustion**: **Action**: Immediately cease new tool calls. Synthesize answer from existing evidence or declare inability to answer if critical data is missing.

## Procedure
1. **Step 1**: Detect error. If `browser_navigate` fails (403/502/Timeout), mark the source as "unavailable".
2. **Step 2**: **Circuit Breaker**: Do not retry the same URL more than once. Switch strategy:
   - If using `browser_navigate` on SEC.gov fails, stop trying to access SEC directly.
   - Fall back to `search_text` results that might have cached the content in snippets.
3. **Step 3**: **Snippet Priority**: If the answer is likely in a document but the document is inaccessible, prioritize finding the answer in search snippets. Snippets often contain the exact sentence needed.
4. **Step 4**: **Budget Check**: Before every tool call, estimate cost. If budget < threshold, skip tool call and attempt reasoning based on current context.
5. **Step 5**: **Graceful Degradation**: If no tool can retrieve the data, output the best estimate based on available snippets or explicitly state "Unable to determine" if the data is strictly hidden behind a paywall/login.

## Output Format Risk
- Do not output a guess if the evidence is insufficient. It is better to fail gracefully than to provide a hallucinated number.
- Ensure the final answer format matches the request even when derived from partial evidence.
