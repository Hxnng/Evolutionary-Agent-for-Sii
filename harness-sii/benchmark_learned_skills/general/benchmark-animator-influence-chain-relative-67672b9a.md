---
skill_id: benchmark-animator-influence-chain-relative-67672b9a
title: 动画家影响链（导演→母校→灵感动画家→家庭成员）
domains: general, benchmark, web, evidence
triggers: 动画家影响链（导演→母校→灵感动画家→家庭成员）, 通过1990年代某动画系列导演→其毕业的1940年代成立学校→其灵感来源的另一位动画家（童年绘画天才+两所高中之一建于1900-1910）→该动画家1960年代去世的姑姑, benchmark web question, external evidence lookup, animation.influence.aunt.1960s
summary: 通过1990年代某动画系列导演→其毕业的1940年代成立学校→其灵感来源的另一位动画家（童年绘画天才+两所高中之一建于1900-1910）→该动画家1960年代去世的姑姑
confidence: 0.70
---
# 动画家影响链（导演→母校→灵感动画家→家庭成员）

## When to use
- Question type: 动画家影响链（导演→母校→灵感动画家→家庭成员）
- Trigger: 通过1990年代某动画系列导演→其毕业的1940年代成立学校→其灵感来源的另一位动画家（童年绘画天才+两所高中之一建于1900-1910）→该动画家1960年代去世的姑姑

## Diagnostic Cues
- The task asks for a concrete answer, but direct visual/text clues are incomplete or ambiguous.
- Treat this as a reusable procedure, not as a memory of a specific benchmark answer.

## Evidence And Tool Plan

- Prefer search_text for named entities, public records, reports, captions, and page snippets.
- Use browser_navigate/browser_get_text only after a search result gives a promising source URL.
- Cross-check the final entity, number, date, or label against at least one reliable evidence source when possible.

## Procedure
1. 第1步：先锁定灵感动画家——4-5岁展现绘画天赋、有两所高中、一所建于1900-1910，强烈指向某位经典美国动画黄金时代人物
2. 第2步：通过传记资料查该动画家家族关系，找其姑姑（aunt）信息，确认1960年代去世
3. 第3步：反向验证：1990年代美国动画系列+导演毕业于1940年代成立的学校（如CalArts虽建于1961，提示要查其他动画名校），且该导演公开表示受步骤1中的动画家影响
4. 第4步：输出姑姑的全名；避免混淆母亲、阿姨与表亲的关系（aunt特指）

## Stop / Fallback
- Stop searching once the answer is directly supported by visible image evidence or reliable external evidence.
- If evidence remains weak near the step limit, synthesize the best-supported answer instead of continuing tool loops.

## Output Contract
- Return the answer itself in <answer>...</answer>.
- Do not mention this skill, training data, benchmark IDs, or internal trajectory details.

## Avoid Pitfalls
把焦点放在1990年代动画系列本身而非'灵感来源动画家'；混淆血缘关系（aunt vs great-aunt）