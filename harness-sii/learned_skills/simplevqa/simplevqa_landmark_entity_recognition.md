---
skill_id: simplevqa_landmark_entity_recognition
title: SimpleVQA Landmark, Celebrity, Artwork, Product, and Entity Recognition
domains: image, simplevqa, entity-recognition, landmark, celebrity
triggers: landmark, celebrity, artwork, building name, church, castle, museum, person in the image, logo, brand, name of this place, who is the person
summary: 当 SimpleVQA 题目要求从图像识别地标、建筑、人物、艺术品、品牌、产品或菜品本体名称时使用，强调先视觉识别再最小核验。
confidence: 0.85
---
# SimpleVQA Landmark, Celebrity, Artwork, Product, and Entity Recognition

Use this skill when the primary task is to identify the entity depicted in the image: a landmark, building, church, castle, museum, celebrity, artwork, logo, product, dish, vehicle, software screen, or named object.

## When to use
- The question asks `What is the name`, `Who is the person`, `Which landmark`, `图中人物是谁`, `名称为`, `这是什么`, `logo`, `brand`, or similar recognition wording.
- The answer is the entity name itself, not a second-hop property of that entity.
- The image belongs to landmark, celebrity, artwork, posters, food, product, or object-recognition style SimpleVQA tasks.
- Do not use this skill when `atomic_fact` already identifies the entity and the question asks for an external attribute.

## Diagnose / Credit Assignment
- Confirm the requested answer type: person, place/building, artwork/work title, product/brand, food, animal/plant, vehicle/model, or software/interface.
- If the answer is generic class such as `church` instead of a proper name, treat it as under-specific recognition.
- If the answer gives a related city/country instead of the place name, treat it as answer-type confusion.
- If direct recognition is uncertain, escalate evidence once rather than guessing a famous lookalike.

## Recognition Procedure
- Inspect distinctive visual cues: architecture style, inscriptions, skyline, monument shape, clothing/uniform, logo text, packaging, artwork composition, or dish ingredients.
- Use visible text as a strong cue, but verify whether it is a brand, title, location label, or unrelated sign.
- For landmarks/buildings, distinguish object name from location.
- For people, use inscriptions, context clues, or source digest when direct face recognition is weak.
- For artworks and cultural objects, preserve official title formatting and do not shorten named works into generic descriptions.

## Tool Plan
- If an http(s) image URL is available and direct recognition is uncertain, one `search_image` call may be useful.
- If only a local image path is available, do not loop on `search_image`; use visual reasoning, OCR text, and provided dataset clues.
- Use `search_text` with visible inscriptions or distinctive labels only when OCR/text clues exist.

## Memory Layer Policy
- Short-term memory may record recent recognition confusions such as generic class vs proper name, city vs landmark, or lookalike person/artwork.
- Promote to long-term only when the update adds a reusable recognition cue, evidence-escalation rule, or answer-type distinction.
- Do not store a specific landmark/person/artwork identity as a permanent skill fact.

## Stop / Fallback
- Stop when the entity name is confidently identified and matches the requested type.
- If recognition remains uncertain after one targeted evidence step, answer the most specific supported name rather than a broad category.
- If the question asks for a property after identification, switch to the atomic bridge/search skill once the entity is known.

## Output Contract
- Output only the proper entity name inside `<answer>...</answer>`.
- Match the question language when possible; keep official English names for English landmark/person/product questions and Chinese names for Chinese cultural questions.
- Do not include city, country, description, or confidence unless explicitly requested.
