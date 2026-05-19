---
skill_id: init_skill
title: Initial Task Solving Skill
domains: general, simplevqa, 2wiki
triggers: task, answer, tool, evidence, format, skill
summary: General startup guidance for generator before specialized learned skills exist.
confidence: 1.00
---
# Initial Task Solving Skill

## 适用触发
- No narrower learned skill matches.

## 做法
- Identify answer type and the single missing evidence point.
- Use compact evidence first; call a tool only for that gap.

## 停止/回退
- Stop after direct evidence or repeated low-signal results.

## 输出格式
- Output the requested span only, wrapped in `<answer>...</answer>`.
