---
skill_id: simplevqa_direct_perception
title: SimpleVQA Direct Visual Perception, Counting, Spatial, and Attribute Tasks
domains: image, simplevqa, direct-perception, count, spatial
triggers: how many, count, 多少, 几个, left, right, 左侧, 右侧, 亮度, color, position, in front of, behind, yes or no
summary: 当 SimpleVQA 题目只需观察图像中的数量、颜色、位置、左右、前后、大小、亮度、存在性或简单属性时使用，避免无谓联网搜索。
confidence: 0.88
---
# SimpleVQA Direct Visual Perception, Counting, Spatial, and Attribute Tasks

Use this skill when the answer is directly visible in the image and does not require external factual lookup.

## When to use
- The question asks for count, color, brightness, left/right, top/bottom, front/behind, relative size, shape, object existence, object category, or yes/no spatial relation.
- The dataset category resembles `图像中的数量、方向和位置关系`, `color`, `count`, `position`, `existence`, `scene`, or direct perception.
- The answer should be a short number, side, object, color, shape, yes/no, or relation phrase.
- Do not use this skill when the question asks for a hidden external attribute such as first release year, author, dynasty, or award.

## Diagnose / Credit Assignment
- Identify whether the failure risk is perception, perspective, counting scope, or output wording.
- Check whether the question uses viewer perspective or object-intrinsic direction.
- Decide the exact count target: people visible, objects of a type, letters in text, fruit types, shapes, or items on one side.
- If a prior run searched the web for a direct visual question, treat it as context-selection failure.

## Visual Procedure
- Locate the target objects, then define the comparison frame: whole image, left/right panel, row/column order, labeled regions, or viewer perspective.
- For counts, scan left-to-right and top-to-bottom; include partially visible items only if the question says visible/pictured.
- For letter or digit counts, read the text first, normalize case only if the question does not distinguish case, then count the exact requested character.
- For spatial relations, answer relative to the viewer unless the prompt specifies the object's own left/right.
- For brightness/size comparisons, compare the requested panels or objects only; ignore unrelated background exposure.
- For yes/no, answer directly in the language of the question.

## Tool Plan
- Do not call web search for direct visual perception.
- Do not call image search unless the question asks for an unknown landmark/person/artwork and direct perception is insufficient.
- If OCR is needed for dense visible text, switch to the OCR/table/chart skill.

## Memory Layer Policy
- Short-term memory may record immediate perception failure modes such as wrong perspective, wrong counting scope, or repeated search on a direct visual task.
- Promote to long-term only when the update adds a reusable scan order, perspective convention, counting inclusion rule, or answer-format rule.
- Do not store the count, color, side, or object answer from a specific image as long-term memory.

## Stop / Fallback
- Stop as soon as the visual evidence supports the requested short answer.
- If the image is ambiguous, use the most visible interpretation and keep the answer concise.
- If a local image fails to load and no `atomic_fact` or text clue exists, state inability only when the harness cannot access the image; do not invent visual content.

## Output Contract
- Output only the visual answer inside `<answer>...</answer>`.
- Match the prompt language: Chinese side words like `左侧`/`右侧`, English words like `left`/`right`, or numeric digits when asked for counts.
- Do not include reasoning, uncertainty, or visual descriptions in the final answer.
