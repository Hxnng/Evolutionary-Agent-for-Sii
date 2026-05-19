---
skill_id: simplevqa_ocr_table_chart
title: SimpleVQA OCR, Table, Chart, Formula, Menu, and Diagram Reasoning
domains: image, simplevqa, ocr, table, chart
triggers: extract text, 从图片中提取文本, table, chart, graph, formula, equation, menu, price, average, total, percentage, flowchart, 表格, 图表, 公式
summary: 当 SimpleVQA/mm-vet/MMBench 题目需要读取图片文字、表格、图表、菜单价格、流程图、公式或数学题并进行轻量计算时使用。
confidence: 0.89
---
# SimpleVQA OCR, Table, Chart, Formula, Menu, and Diagram Reasoning

Use this skill when the answer depends on visible text, numbers, labels, chart axes, tables, menus, formulas, flowcharts, schedules, or simple arithmetic from an image.

## When to use
- The question asks to extract text, read a label, solve an equation, compute a total/difference/average/percentage, identify a table row/column, follow a flowchart, or interpret a chart.
- The image resembles menus, gas prices, schedules, tables, charts, formulas, maps, diagrams, or worksheets.
- The answer may contain multiple values, a computed numeric value, a label from a table, a year/month, or a step instruction.
- Do not use this skill for pure landmark/person recognition or simple object counting unless visible text is central evidence.

## Diagnose / Credit Assignment
- Determine whether the risk is OCR misread, row/column mismatch, axis-unit mismatch, arithmetic error, or answer-format leakage.
- Identify all required fields before computing: target row, column, legend, unit, time period, category, and operation.
- Decide whether the answer is copied from the image or derived by calculation.
- If a failure compresses the image into vague text, preserve enough local structure for row/column/axis credit assignment.

## OCR and Reasoning Procedure
- Read relevant text exactly, including capitalization, punctuation, currency signs, decimal points, units, and labels.
- For tables, locate the header row first, then trace the requested row and column intersection.
- For charts, read the title, axis labels, legend, units, and tick scale before extracting values.
- For menus/prices, align item names with prices; avoid pairing a price with the neighboring item.
- For formulas/equations, transcribe each visible equation before solving; preserve variables and signs.
- For flowcharts or step diagrams, follow arrows and decision branches in order.
- For maps or labeled diagrams, use the letter/number label exactly as printed when the question asks for a marked region.
- Perform arithmetic explicitly from visible numbers; round only if the question requests rounding or the visual value is approximate.

## Tool Plan
- Use image understanding/OCR from the model first; external web search is normally irrelevant.
- Use `search_text` only if visible text names an external entity and the question asks a factual property not present in the image.
- Do not use `search_image` for local chart/menu/formula images.

## Memory Layer Policy
- Short-term memory may store recent OCR/table/chart mistakes such as row-column mismatch, unit loss, decimal misread, or wrong arithmetic operation.
- Promote to long-term only when the update improves the general reading order, validation check, calculation rule, or output contract.
- Do not store specific table values, menu prices, chart answers, or equation solutions as durable skill facts.

## Stop / Fallback
- Stop once the copied or computed value is supported by visible image evidence.
- If OCR is uncertain, cross-check surrounding labels, units, and arithmetic consistency.
- If the image is too blurry to read, answer from any provided text clue; otherwise report inability only after no readable evidence remains.

## Output Contract
- Output only the final copied/computed value inside `<answer>...</answer>`.
- Preserve units and symbols if the question asks for them, such as `%`, dollars, gallons, years, months, or formula notation.
- Do not output alternative-answer syntax such as `<OR>` or `<AND>`; give the natural answer requested by the question.
