---
skill_id: benchmark-founder-company-original-name-f031987e
title: 多约束公司原名识别
domains: general, benchmark, web, evidence
triggers: 多约束公司原名识别, 题目描述创始人出生于1970-1990、辍学创业、公司在1990-2010年间成立、后改名、结构复杂债务缠身、创始人2023前因行贿被定罪，要求给出公司原英文名, benchmark web question, external evidence lookup
summary: 题目描述创始人出生于1970-1990、辍学创业、公司在1990-2010年间成立、后改名、结构复杂债务缠身、创始人2023前因行贿被定罪，要求给出公司原英文名
confidence: 0.70
---
# 多约束公司原名识别

## When to use
- Question type: 多约束公司原名识别
- Trigger: 题目描述创始人出生于1970-1990、辍学创业、公司在1990-2010年间成立、后改名、结构复杂债务缠身、创始人2023前因行贿被定罪，要求给出公司原英文名

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：组合最稀有的线索：辍学创始人 + 行贿定罪 + 高负债 + 改过名的庞大企业；这强烈指向中国/亚洲某些大型民营集团（如海航、明天系等）
2. 第2步：用英文搜索 'dropped out' + 'founder' + 'bribery conviction' + 'debt-ridden conglomerate' + 'renamed'；并查Wikipedia对应公司的'前身/原名'字段
3. 第3步：候选锁定后核验创始人出生年份、辍学经历、创业年份是否落入1990-2010、行贿定罪时间是否2023前；并确认改名前后的英文译名
4. 第4步：题目要求英文写法，注意中文公司原名要给出官方英文译名而非拼音；区分'品牌名'与'公司法人名'，给出最常用的英文形式

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
容易把改名后的现用名当成原名输出；也容易在中文公司名英译时拼写错误或给出非官方译法
