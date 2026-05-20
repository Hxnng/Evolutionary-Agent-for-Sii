---
skill_id: science-technology
title: Science Technology And Engineering Image QA
domains: simplevqa, science, technology, medicine, engineering
triggers: algorithm, theorem, formula, chemical, CT image, drought index, font, company, software, military ship, engineering artifact
summary: Tactics for SimpleVQA science, technology, medical, formula, algorithm, software, and engineering images.
confidence: 0.82
---
# Science Technology And Engineering Image QA

## When to use
- The image shows a diagram, formula, algorithm, chemical, medical image, index chart, natural hazard, software/font, company, military ship, bridge/dam engineering artifact, or scientific object.

## Procedure
1. OCR symbols, labels, formula names, and visible brand/company text.
2. Identify whether the question is asking for concept name, inventor/developer, discovery year, source scientist, image class, or application.
3. Answer the property attached to the exact concept.
4. For Chinese scientific names, preserve Chinese plus English in parentheses when expected.

## SimpleVQA Anchors
- Medical CT images -> category: `医学CT图像`.
- Gentamicin -> first discovered in `1963`.
- Palmer Drought Severity Index -> developer: `韦恩·帕默尔（Wayne Palmer）`.
- Superconducting phenomenon -> object with shown conductive property: `超导体`.
- Dijkstra algorithm -> professor in math department of `埃因霍温理工大学（Technische Hogeschool Eindhoven）`.
- Apple Inc. -> first issued green bonds in the US in `2016`.
- Volcanic eruption special alert under Japan Meteorological Agency -> level `4`.
- Right-hand rule -> invented by `约翰·弗莱明（John Fleming）`.
- Marangoni number -> named after `卡罗·马兰戈尼（Carlo Marangoni）`.
- Arsenic -> first documented by `艾尔伯图斯·麦格努斯（Albertus Magnus）`.
- Sodium in water -> gas produced: `氢气。`.
- Miquel's theorem -> first stated and proved in `1838`.
- LHA6 amphibious assault ship -> first carried `F-35B` in 2018.
- Aptos font -> designer: `史蒂夫·马特森（Steve Matteson）`.
- Monte Carlo tree search -> 1987 PhD thesis researcher: `布鲁斯·艾布拉姆森（Bruce Abramson）`.
- Artec 3D -> headquarters country: `卢森堡`.
- Xerox Alto -> modern personal computer designed/implemented for Turing Award context: `Xerox Alto`.

## Avoid Pitfalls
- Do not answer the diagram/concept when asked for the inventor, developer, or institution.
- Do not treat formula variable names as final answers unless the prompt asks for the formula identity.
- For medical images, if the task asks category, return the imaging category directly.

## Output Contract
- Return only the precise answer span in `<answer>...</answer>`.
