---
skill_id: benchmark-2000s-bollywood-rich-poor-friendship-movie-d77e3ca0
title: 电影识别（贫富主题+导演演员家族纠纷）
domains: general, benchmark, web, evidence
triggers: 电影识别（贫富主题+导演演员家族纠纷）, 2000年代电影、两位1960年代生主演分别饰演贫富角色、导演与某主演的兄弟有公开纠纷（截至2023年11月）, benchmark web question, external evidence lookup
summary: 2000年代电影、两位1960年代生主演分别饰演贫富角色、导演与某主演的兄弟有公开纠纷（截至2023年11月）
confidence: 0.70
---
# 电影识别（贫富主题+导演演员家族纠纷）

## When to use
- Question type: 电影识别（贫富主题+导演演员家族纠纷）
- Trigger: 2000年代电影、两位1960年代生主演分别饰演贫富角色、导演与某主演的兄弟有公开纠纷（截至2023年11月）

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：'两男主一富一贫'+'2000年代'+'演员均1960s生'是典型宝莱坞双雄片配置；考虑Akshay Kumar、Salman Khan、Bobby Deol、Sunny Deol等组合
2. 第2步：搜索'2000s Bollywood movie rich poor two friends'+'director feud actor brother'缩小范围；导演与演员兄弟的纠纷是稀有线索
3. 第3步：核对两位主演的具体出生年份均在1960年代；确认导演与某主演兄弟（如Sunny Deol或Salman Khan的兄弟）公开冲突的报道
4. 第4步：电影名可能带副标题（如'XXX: Friends Forever'），输出时要完整；不要混淆同名翻拍作

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
容易把贫富主题套到《Dostana》《Partner》等明显不符的片子；导演纠纷是2023年11月之前已公开的新闻，要确认时间窗
