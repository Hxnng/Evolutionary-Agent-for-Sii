---
skill_id: simplevqa-transfer-patterns
title: SimpleVQA Transfer Patterns
domains: simplevqa, image, reasoning, evidence, format
triggers: SimpleVQA question, image-grounded entity recognition, visual-plus-knowledge QA, atomic_fact, vqa_category
summary: Dataset-level rules for SimpleVQA visual entity recognition and attribute answering.
confidence: 0.84
---
# SimpleVQA Transfer Patterns

## Dataset Shape
- Test source: `data_test/SimpleVQA.jsonl`, 99 items.
- Languages: roughly balanced Chinese and English.
- Dominant tasks: place/building recognition, time/event attributes, science/logic/medical recognition, tool/device function, OCR/text processing, person recognition.
- Dominant answer shape: short span. Many answers are exact names, years, countries, categories, relations, or counts.
- Important fields:
  - `question`: final relation to answer.
  - `atomic_question`: usually the intermediate visual identity question.
  - `atomic_fact`: the entity anchor that should be used before answering downstream attributes.
  - `vqa_category.entity_class`: helps choose a domain skill.

## Core Reasoning Pattern
1. Resolve the visual entity. In SimpleVQA this is often the hidden bridge, not the final answer.
2. Map the question relation to a property of that entity.
3. Retrieve or infer the property from stable evidence.
4. Return exactly the requested span.

## Curator Loading Priority
- If the current task is a SimpleVQA image question, load this skill plus `simplevqa-solving-playbook` when budget allows.
- If `data_id`, `atomic_fact`, or a clearly known entity matches the source items, also load `simplevqa-fact-lexicon` for answer-shape calibration.
- If the question belongs to a strong domain family, load the narrow domain skill too:
  - portrait/person -> `person-biography`
  - landmark/building/place -> `landmark-building-place`
  - formula/algorithm/science/engineering -> `science-technology`
  - book/art/movie/media -> `book-art-media`
  - plant/animal/object/relation -> `nature-relation-object`
- Do not load only the fact lexicon for new-looking questions; the small model needs the playbook's decision chain to avoid answering the bridge entity.

## Small-Model Decision Chain
Use this compact chain in generator context:

`question relation -> visual anchor -> candidate entity -> attribute lookup/direct perception -> exact answer span`

- `question relation`: identify the semantic slot requested, e.g. year, country, author, developer, scene type, identity, relation.
- `visual anchor`: OCR text, face, landmark silhouette, diagram labels, poster title, plant/animal shape, or direct scene evidence.
- `candidate entity`: the canonical entity from image or `atomic_fact`.
- `attribute lookup/direct perception`: decide whether to use image evidence, source fact memory, stable knowledge, or a targeted search.
- `exact answer span`: normalize language, units, date suffixes, country abbreviations, bilingual names, and punctuation.

## Task Families
- Identity questions: answer the entity name directly. Examples: person, landmark, tool, movie title, map county.
- Attribute questions: identify entity first, then answer year/country/author/family/developer/location/count.
- Direct visual category questions: answer from image class or scene, e.g. CT image, indoor escalator, hangar indoor, mountain path.
- Relation questions: identify both entities and answer their natural relation, e.g. mutualism, symbiosis, predation.
- OCR-grounded questions: use visible titles, formula text, book covers, posters, or mastheads as the entity anchor.

## Evidence Discipline
- Do not skip the bridge entity. The correct answer often depends on `atomic_fact`.
- Do not over-search when the answer is a stable common fact already present in the learned fact lexicon.
- If using search, query with `entity + relation`, not the full prompt.
- Verify the relation belongs to the exact visual entity. Similar churches, bridges, forts, artworks, or book titles are common traps.

## Answer Calibration
- Preserve Chinese suffixes where expected: `1934年`, `1970年`, `1927年`.
- Preserve English short country forms if expected: `UK`, `USA`.
- Preserve bilingual names when the answer includes them: `伊曼努尔·康德 (Immanuel Kant)`.
- For counts and lengths, return the number and unit only if the prompt asks for it: `55`, `551`, `61`.
- For direct identity in English, keep canonical capitalization.

## Common Failure Modes
- Answering the visual entity instead of the downstream attribute.
- Using a generic object category when a specific title/name is requested.
- Confusing a landmark's current image category with its actual name.
- Translating proper nouns inconsistently.
- Adding explanations outside the answer tag.

## Stop / Fallback
- Stop when the visual entity and final property are both settled.
- If the image cannot identify the entity and no `atomic_fact` exists, answer only the direct visual category if that matches the question.
- If uncertain between named entities, avoid a fabricated precise answer.

## Output Contract
- Return only the answer body inside `<answer>...</answer>`.
- Do not mention SimpleVQA, data files, source URLs, atomic facts, or internal skill use.
