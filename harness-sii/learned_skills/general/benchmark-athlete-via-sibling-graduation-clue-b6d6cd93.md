---
skill_id: benchmark-athlete-via-sibling-graduation-clue-b6d6cd93
title: 多约束运动员识别
domains: general, benchmark, web, evidence
triggers: 多约束运动员识别, 题目通过出生月份+年份区间、儿时游泳梦、首枚国际奖牌年份、东京是第三次奥运、兄弟工业工程毕业等线索锁定一名运动员, benchmark web question, external evidence lookup
summary: 题目通过出生月份+年份区间、儿时游泳梦、首枚国际奖牌年份、东京是第三次奥运、兄弟工业工程毕业等线索锁定一名运动员
confidence: 0.70
---
# 多约束运动员识别

## When to use
- Question type: 多约束运动员识别
- Trigger: 题目通过出生月份+年份区间、儿时游泳梦、首枚国际奖牌年份、东京是第三次奥运、兄弟工业工程毕业等线索锁定一名运动员

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：东京奥运是其第三次奥运 → 出生1993-1996的运动员要在年轻时就连参三届奥运，强烈指向游泳/体操等少年成名项目；结合'幼时梦想当游泳运动员'其本身大概率就是游泳运动员
2. 第2步：搜索 'female swimmer born January 1993-1996' + 'first international medal 2009-2012' + 'three Olympics Tokyo'；对小国家的国家队明星运动员要特别关注
3. 第3步：候选人锁定后核验：1月出生且年份在区间内、首枚国际奖牌年份匹配、东京是否确为第三届奥运、是否有兄弟在2011-2014年5月获工业工程学位
4. 第4步：注意题目并未指明性别和国籍，不要默认西方主流泳将；非洲/中东等地区运动员可能因首位身份连续参加多届奥运

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
容易把搜索范围局限在欧美知名游泳明星而忽略中东/非洲先驱型运动员；也容易忽视'兄弟工业工程毕业'这种家庭线索来交叉验证身份
