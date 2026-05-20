---
skill_id: benchmark-unanswerable-trivial-detail-guard-8e820b38
title: 多约束人物识别+不可考据细节
domains: general, benchmark, web, evidence
triggers: 多约束人物识别+不可考据细节, 题目通过多层约束锁定一个具体人物后，再询问一个高度私人化、琐碎且通常未被任何公开来源记录的细节（如某物的颜色、某顿饭的菜单等）, benchmark web question, external evidence lookup
summary: 题目通过多层约束锁定一个具体人物后，再询问一个高度私人化、琐碎且通常未被任何公开来源记录的细节（如某物的颜色、某顿饭的菜单等）
confidence: 0.70
---
# 多约束人物识别+不可考据细节

## When to use
- Question type: 多约束人物识别+不可考据细节
- Trigger: 题目通过多层约束锁定一个具体人物后，再询问一个高度私人化、琐碎且通常未被任何公开来源记录的细节（如某物的颜色、某顿饭的菜单等）

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：先解构题面，区分哪些是用于识别人物的约束条件，哪些是最终被问的细节；评估最终问题的可考据性（公共记录中是否会保留这种细节）
2. 第2步：即使能通过多重约束锁定人物身份，也要先用针对性搜索词（人名 + 'college' + 'suitcase'/'luggage'/具体物件）验证该细节是否曾被公开报道或本人提及
3. 第3步：若多渠道（新闻、采访、回忆录、社交媒体、维基）均无该细节的可信来源，应判定该信息不可考据，而不是基于人物画像去猜测
4. 第4步：避免为了完成回答而编造合理但无来源的答案；对此类琐碎私人细节，明确回复 'unknown' 或 '无法确定' 才是正确做法

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
最容易犯的错误是被前置的复杂线索吸引，花大量精力锁定人物后，凭直觉或常识(如'蓝色行李箱很常见')编造一个看似合理的答案，而忽略了最终问题本身根本不可被公开来源证实
