---
skill_id: benchmark-music-act-birthname-via-discography-clues-94649ef7
title: 多线索音乐人本名识别
domains: general, benchmark, web, evidence
triggers: 多线索音乐人本名识别, 通过歌曲与莎翁戏剧同名、1970年代debut销量、参与某2011年游戏音乐、与音乐制作人配偶、1976年首张冠军专辑等多重线索识别一位音乐人，并询问其本名（birth name）, benchmark web question, external evidence lookup
summary: 通过歌曲与莎翁戏剧同名、1970年代debut销量、参与某2011年游戏音乐、与音乐制作人配偶、1976年首张冠军专辑等多重线索识别一位音乐人，并询问其本名（birth name）
confidence: 0.70
---
# 多线索音乐人本名识别

## When to use
- Question type: 多线索音乐人本名识别
- Trigger: 通过歌曲与莎翁戏剧同名、1970年代debut销量、参与某2011年游戏音乐、与音乐制作人配偶、1976年首张冠军专辑等多重线索识别一位音乐人，并询问其本名（birth name）

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：识别最稀有的线索组合：'1976年首张冠军专辑'+'1970年代debut单曲只卖300份'+'1983年电影出镜'，这些时间锚点能极大缩小范围
2. 第2步：搜索 '1976 number-one album debut' + '300 copies debut single' + '2011 video game music department'；'与1500s末莎翁戏剧同名的歌'是强独特线索（如 'Twelfth Night', 'Romeo and Juliet', 'Midsummer Night's Dream' 等）
3. 第3步：候选锁定后，验证其配偶是否为1970年代结婚的制作人/编曲/键盘手，是否在1983某电影中以未署名身份出现；同时确认艺名与本名的对应关系
4. 第4步：题目明确要 birth name（旧姓），婚后改姓者需给出婚前姓名；注意日文/非英文人名的罗马字写法

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
容易把舞台艺名当成本名直接输出；也容易忽视'与莎翁戏剧同名的歌'这种独特线索，反而被销量、年份等较弱信号误导到错误的西方艺人
