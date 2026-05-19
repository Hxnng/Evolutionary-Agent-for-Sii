---
skill_id: simplevqa_cn_culture_heritage
title: SimpleVQA Chinese Culture, Landmark, Artifact, Poem, and Idiom Tasks
domains: image, simplevqa, chinese-culture, landmark, artifact
triggers: CCBench, CCSimpleQA, 景观, 文物, 书画, 古诗, 成语, 俗语, 所在省份, 所在城市, 朝代, 始建
summary: 当 SimpleVQA 中文文化题围绕景观、文物、书画、古诗、成语、俗语、民族建筑或历史人物进行识别和属性追问时使用。
confidence: 0.87
---
# SimpleVQA Chinese Culture, Landmark, Artifact, Poem, and Idiom Tasks

Use this skill for Chinese SimpleVQA questions where the image depicts a landmark, artifact, painting/calligraphy, poem clue, idiom/rebus, traditional residence, historic figure, or scenic place.

## When to use
- The question contains `景观`, `文物`, `书画`, `古诗`, `成语`, `俗语`, `朝代`, `所在省份`, `所在城市`, `始建`, `民族`, or `历史人物`.
- The dataset clue or `atomic_fact` identifies a landmark/artifact/work, and the user asks for a related cultural attribute.
- The answer should usually be a short Chinese span: place name, province, city, dynasty, poem line/title, idiom, artwork title, material, or person.
- Do not use this skill for English landmark recognition without Chinese cultural context.

## Diagnose / Credit Assignment
- Separate recognition from attribute lookup: first identify what the image depicts, then answer the exact cultural relation.
- If the answer gives the landmark name while the question asks city/province/dynasty/poem/person, treat it as answer-type failure.
- Watch for cultural allusions where the visible object is only a clue to a poem, idiom, proverb, or story.
- Avoid learning one-off cultural facts as rules; only the disambiguation procedure belongs in long-term memory.

## Evidence and Context Procedure
- Use `atomic_fact` as the recognized cultural object when present.
- Use `source_digest` for encyclopedia snippets, museum pages, and highlighted text before broad search.
- Determine the requested attribute class: name, province, city, dynasty/era, associated person, poem line, poem title, idiom, proverb, material, function, or origin.
- If the question asks location, answer at the requested level only.
- If the question asks dynasty/era, output the dynasty/period, not the full artifact title.
- If the image is a poem/idiom/rebus clue, map visible objects/actions to the expression and avoid explaining the metaphor.
- For museum/artifact pages, keep qualifiers such as `尊`, `鼎`, `图卷`, `像`, `灯`, `符`, or `币` when the full artifact name is requested.

## Tool Plan
- Use direct visual/context evidence first for recognition.
- Use `search_text` with `<atomic_fact> + <requested attribute>` for external attributes such as founding dynasty, province, associated person, or poem source.
- Use authoritative sources first: museum pages, encyclopedia pages, local government/tourism pages, or canonical literature references.

## Memory Layer Policy
- Short-term memory may retain recent confusing routes such as landmark-name vs province/city, artifact-name vs dynasty, or poem-line vs poem-title.
- Promote to long-term only when the update changes a reusable cultural disambiguation procedure or answer-granularity rule.
- Do not store individual poem answers, artifact facts, tourist-site facts, or row-specific cultural knowledge as long-term skill content.

## Stop / Fallback
- Stop when the evidence supports the exact cultural attribute and granularity.
- If two possible objects are visually similar, add the visible clue or source title to the query instead of guessing.
- If recognition is uncertain and no clue exists, answer from visible evidence only for simple class questions; otherwise perform one targeted search with distinctive visual descriptors.

## Output Contract
- Final answer must be one concise Chinese span inside `<answer>...</answer>`.
- Preserve book-title brackets for works if the expected answer is a named work.
- Do not add explanation, source citation, or alternate names unless the question explicitly asks for them.
