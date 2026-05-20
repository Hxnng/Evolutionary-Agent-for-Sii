---
skill_id: benchmark-foreign-series-plot-sequence-identify-aa56d388
title: 动漫/剧集剧情序列识别
domains: general, benchmark, web, evidence
triggers: 动漫/剧集剧情序列识别, 用户描述某外语剧（动漫）特定情节序列：S1主角击败配角对手、揭示力量秘密、S2伪装好人变反派, benchmark web question, external evidence lookup
summary: 用户描述某外语剧（动漫）特定情节序列：S1主角击败配角对手、揭示力量秘密、S2伪装好人变反派
confidence: 0.70
---
# 动漫/剧集剧情序列识别

## When to use
- Question type: 动漫/剧集剧情序列识别
- Trigger: 用户描述某外语剧（动漫）特定情节序列：S1主角击败配角对手、揭示力量秘密、S2伪装好人变反派

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：识别'外国系列剧2020年8月前播出'+'主角向配角揭示力量来源秘密'这一极具标志性情节，强烈暗示某热门日本动漫
2. 第2步：用'main character reveals secret of his strength to supporting character anime'+'season 2 villain pretended to be ally'组合搜索
3. 第3步：根据'S1主角替配角击败女反派'+'S2伪装好人的角色变反派'匹配具体作品；通过粉丝Wiki核实季节剧情
4. 第4步：注意输出剧名的常见英文写法；不要把漫画原作和动画版混淆——题目指aired，所以是动画

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
外语剧不一定是韩剧/日剧真人剧，要意识到anime也算'foreign series'；'力量的秘密'是极强锚点不要忽略
