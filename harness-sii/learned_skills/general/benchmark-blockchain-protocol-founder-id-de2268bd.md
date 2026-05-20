---
skill_id: benchmark-blockchain-protocol-founder-id-de2268bd
title: 区块链/加密项目创始人识别
domains: general, benchmark, web, evidence
triggers: 区块链/加密项目创始人识别, 题目用协会职务、平台下载量、代币流通、会议出席等多维线索定位某个区块链协议的创始人。, benchmark web question, external evidence lookup
summary: 题目用协会职务、平台下载量、代币流通、会议出席等多维线索定位某个区块链协议的创始人。
confidence: 0.70
---
# 区块链/加密项目创始人识别

## When to use
- Question type: 区块链/加密项目创始人识别
- Trigger: 题目用协会职务、平台下载量、代币流通、会议出席等多维线索定位某个区块链协议的创始人。

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：先识别'2018年90+成员公司协会的主席'——这是Blockchain Game Alliance的强指纹；同时'3百万下载量平台'指向具体游戏/NFT平台。
2. 第2步：检索两个条件交集人物，并验证其创建的协议是否有'2022年约30亿tokens'与代币2021年底ATH的特征。
3. 第3步：核对85%流通供应量（2022年）与该项目的tokenomics数据是否吻合（CoinMarketCap/CoinGecko）。
4. 第4步：注意联合创始人通常有多位，问的是'创始人'（founder），需要确认与协议直接对应的那位，且其同时满足协会主席身份。

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
容易把联合创始人混淆；协会主席与协议创始人虽是同一人但需明确锚定；不要把游戏平台与协议混为一谈。
