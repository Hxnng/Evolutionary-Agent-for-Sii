---
skill_id: benchmark-stage-name-via-interview-quotes-966eec20
title: 多约束艺人艺名识别
domains: general, benchmark, web, evidence
triggers: 多约束艺人艺名识别, 题目提供1987出生、年少时跨三大洲生活、家族纹身、2017年表示想主持奥斯卡红毯等口述线索，要求识别其早期使用的艺名, benchmark web question, external evidence lookup
summary: 题目提供1987出生、年少时跨三大洲生活、家族纹身、2017年表示想主持奥斯卡红毯等口述线索，要求识别其早期使用的艺名
confidence: 0.70
---
# 多约束艺人艺名识别

## When to use
- Question type: 多约束艺人艺名识别
- Trigger: 题目提供1987出生、年少时跨三大洲生活、家族纹身、2017年表示想主持奥斯卡红毯等口述线索，要求识别其早期使用的艺名

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：抓最独特的引语类线索：'2017受访说想主持像奥斯卡这样的红毯典礼'，'印度裔前辈建议保留本来身份'，这些引语在采访稿中可被全文检索
2. 第2步：用引号包裹关键短语做精确搜索，如 "hosting red carpet" "Oscars" 2017 interview born 1987；同时尝试 '1987 born actress stage name advice Indian'
3. 第3步：候选人锁定后核验：出生年份、12岁前居住过的三个大洲、2020年代初与兄弟姐妹和表亲一起纹身的报道
4. 第4步：题目问的是'早期使用的艺名'，不是真名也不是现在的名字；要明确区分艺名时期和本名时期

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
容易误把现用名或真实姓名当作答案输出；也容易忽视'印度裔人士给的建议'这条强独特线索，把搜索范围局限在英美主流明星
