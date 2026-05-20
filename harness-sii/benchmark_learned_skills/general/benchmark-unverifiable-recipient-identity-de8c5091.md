---
skill_id: benchmark-unverifiable-recipient-identity-de8c5091
title: 私人医疗/器官捐赠匿名信息追溯
domains: general, benchmark, web, evidence
triggers: 私人医疗/器官捐赠匿名信息追溯, 需识别器官或组织捐赠的具体接收者姓名，而此类信息通常受隐私法规保护。, benchmark web question, external evidence lookup, med.donor.recipient.privacy
summary: 需识别器官或组织捐赠的具体接收者姓名，而此类信息通常受隐私法规保护。
confidence: 0.70
---
# 私人医疗/器官捐赠匿名信息追溯

## When to use
- Question type: 私人医疗/器官捐赠匿名信息追溯
- Trigger: 需识别器官或组织捐赠的具体接收者姓名，而此类信息通常受隐私法规保护。

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：先观察题中线索：青少年车祸亡者、父母决定捐赠某对器官组织、两位受捐者其中一人是孩子、该孩子后来在电视节目上致谢。
2. 第2步：用 'teen organ tissue donor car accident recipient TV show thanks family' 等关键词搜索新闻报道和电视节目片段；尝试英文与可能的地区语言。
3. 第3步：即使找到捐赠者案例，也要核对受捐者姓名是否被公开披露——很多案例只露脸不公布全名。
4. 第4步：若多次搜索后无法找到同时满足全部约束（青少年捐献者、年代窗口、电视节目致谢、儿童受捐者公开姓名）的唯一匹配，应果断给出'无法确定'，而非编造姓名。

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
最大陷阱是为了'回答'而强行匹配某个相似案例。当公开信息确实不足以唯一确认时，正确的答案就是承认无法确定。