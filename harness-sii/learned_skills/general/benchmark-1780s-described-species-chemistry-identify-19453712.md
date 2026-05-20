---
skill_id: benchmark-1780s-described-species-chemistry-identify-19453712
title: 生物物种身份识别（命名史+化学成分）
domains: general, benchmark, web, evidence
triggers: 生物物种身份识别（命名史+化学成分）, 题目给出物种首次描述年代、命名者多领域背景、不被接受的同物异名数量、DNA研究分类调整、亚洲可食用、特定黄烷醇含量, benchmark web question, external evidence lookup
summary: 题目给出物种首次描述年代、命名者多领域背景、不被接受的同物异名数量、DNA研究分类调整、亚洲可食用、特定黄烷醇含量
confidence: 0.70
---
# 生物物种身份识别（命名史+化学成分）

## When to use
- Question type: 生物物种身份识别（命名史+化学成分）
- Trigger: 题目给出物种首次描述年代、命名者多领域背景、不被接受的同物异名数量、DNA研究分类调整、亚洲可食用、特定黄烷醇含量

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：先关注'1780s命名+博物学家跨领域'这一时期典型人物（如Müller、Bulliard等真菌学家）；结合'亚洲食用'+'Epicatechin/Catechin/Amentoflavone'判断这是真菌或植物
2. 第2步：搜索'mushroom described 1780s Bulliard edible Asia flavonoids'类组合；Amentoflavone+Catechin在真菌中较少见，可作为强检索词
3. 第3步：核对Index Fungorum或MycoBank上该物种的5个unaccepted synonyms数量；确认DNA研究重新分类（如从某属移出）
4. 第4步：输出标准学名（双名法，斜体处理可省略）；确认是该物种而非其近缘种

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
容易把'同样具备某特征但DNA证明不近缘'错误理解为同属；要明白这指的是形态相似但分子系统学已分离
