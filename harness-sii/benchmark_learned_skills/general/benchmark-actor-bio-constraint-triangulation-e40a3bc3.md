---
skill_id: benchmark-actor-bio-constraint-triangulation-e40a3bc3
title: 多约束演员识别+亲属信息
domains: general, benchmark, web, evidence
triggers: 多约束演员识别+亲属信息, 通过出生年代、毕业院校创立年份、首部主演电影年代、首次出演剧集及具体客串年份等多重约束识别一位演员，并询问其家庭成员姓名, benchmark web question, external evidence lookup, person.actor.1990s.sister-name
summary: 通过出生年代、毕业院校创立年份、首部主演电影年代、首次出演剧集及具体客串年份等多重约束识别一位演员，并询问其家庭成员姓名
confidence: 0.70
---
# 多约束演员识别+亲属信息

## When to use
- Question type: 多约束演员识别+亲属信息
- Trigger: 通过出生年代、毕业院校创立年份、首部主演电影年代、首次出演剧集及具体客串年份等多重约束识别一位演员，并询问其家庭成员姓名

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：把约束条件转换成可查询的过滤器：出生年代(1990s)、就读机构(1975-1980年间成立)、首个主演电影(2010s)、首次专业出演电视剧(2010-2015首播)、2012年客串某集
2. 第2步：用关键约束的交集做搜索，例如 '1990s born American actor first leading role' + '2012 guest appearance' + 'New York Film Academy(等候选机构)'；优先用最具辨识度的'2012年客串某剧'做反向定位
3. 第3步：找到候选人后，在维基百科、IMDb、采访报道中交叉验证其出生年份、毕业院校创立时间、家庭构成（兄弟姐妹数量、姓名）
4. 第4步：注意询问的是'姐妹'而非任意兄弟姐妹；如果有多个 sibling，需要确认性别匹配；同时注意姓名拼写（可能与艺名不同）

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
容易仅凭'1990s出生的男演员'这一条就跳到知名人物，忽视'就读机构创立于1975-1980'这种关键定位线索；也容易混淆兄弟姐妹的性别和顺序