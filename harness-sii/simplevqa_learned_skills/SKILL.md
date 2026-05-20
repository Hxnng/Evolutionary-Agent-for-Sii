# Learned Skill Index

This is a compact routing index for long-term learned skills.

Use it to choose which skill files are worth reading. When a skill strongly matches, lock its compact procedure into generator context.

## How Curator Uses This

1. Read the current question first: answer type, entities, relation, evidence already present, and the exact missing evidence.
2. Use this index only for routing. Select a skill only when its summary/triggers match the question's concrete risk.
3. Read at most the few selected skill bodies, digest them, then write a short problem-specific context for generator.
4. The generator context should contain actions, evidence gaps, tool conditions, stop rules, answer contract, and a compact locked-skill procedure when a skill matches.
5. If no skill strongly matches, use `general/memory.md` as a fallback process, not as a source of facts.

## How Reflector Uses This

1. Do credit assignment from the trajectory: evidence, tool, reasoning, stopping, or output-format failure.
2. Update only the skill whose trigger truly matches the reusable failure mode.
3. Create a new knowledge/task skill only when the pattern has a narrow stable trigger and a reusable procedure.
4. Benchmark skills may keep distilled trajectory/search steps; avoid only raw task IDs, noisy logs, and unsupported one-off facts.

## Memory Boundary

- `general/memory.md` is the long-term fallback memory skill for durable evidence/tool/format procedure.
- `_memory/short_term.md` is short-term trajectory diagnostics. It is not a skill and must not be loaded into generator context.
- Current-task evidence always overrides learned memory.

## Directory Routing

- `simplevqa/`: visual QA, OCR, image-entity and image-to-attribute skills.
- `2wiki/`: 2WikiMultihopQA evidence-graph and comparison skills.
- `general/`: cross-dataset fallback, tool, evidence, format, and other generic procedures.

## Seed Skill

- `init_skill`: seed startup guidance in `../skills/init_skill.md`; use only when no learned skill clearly applies.

## Learned Skill Catalog


### general

- `memory`: High-quality fallback procedure for evidence selection, tool discipline, stopping, and answer control when no narrower skill applies. (domains=general, memory, evidence, format; triggers=fallback, context selection, evidence gap, stop tool use); file=`general/memory.md`

### simplevqa

- `book-art-media`: Tactics for SimpleVQA items involving books, artworks, films, posters, albums, newspapers, and cultural media. (domains=simplevqa, books, art, film; triggers=book cover, artwork, movie poster, album, newspaper); file=`simplevqa/book-art-media.md`
- `landmark-building-place`: Tactics for SimpleVQA items involving landmarks, buildings, bridges, churches, forts, scenic places, maps, and generic scenes. (domains=simplevqa, landmark, building, place; triggers=bridge, church, fortress, landmark, scenic view); file=`simplevqa/landmark-building-place.md`
- `nature-relation-object`: Tactics for SimpleVQA items involving plants, animals, natural relationships, foods, tools, objects, and direct visual position/category answers. (domains=simplevqa, nature, object, relation; triggers=plant family, plant order, animal origin, ocean habitat, symbiosis); file=`simplevqa/nature-relation-object.md`
- `ocr-and-language`: OCR-first strategy for SimpleVQA items where visible text, symbols, formulas, maps, posters, or covers identify the entity. (domains=image, ocr, text, language; triggers=visible text, title, poster, book cover, map label); file=`general/ocr-and-language.md`
- `person-biography`: Tactics for SimpleVQA portrait items and downstream biographical questions. (domains=simplevqa, person, portrait, biography; triggers=person image, celebrity recognition, scientist, politician, author); file=`simplevqa/person-biography.md`
- `science-technology`: Tactics for SimpleVQA science, technology, medical, formula, algorithm, software, and engineering images. (domains=simplevqa, science, technology, medicine; triggers=algorithm, theorem, formula, chemical, ct image); file=`simplevqa/science-technology.md`
- `simplevqa-fact-lexicon`: Entity-to-answer lexicon distilled from all 99 items in data_test/SimpleVQA.jsonl. Use only when entity and requested relation match. (domains=simplevqa, facts, image, benchmark; triggers=known simplevqa entity, known data_id, atomic_fact match, exact relation match, visual entity attribute lookup); file=`simplevqa/simplevqa-fact-lexicon.md`
- `simplevqa-solving-playbook`: Detailed solved-task guidance distilled from the SimpleVQA test items: how to identify the visual entity, bridge to the asked attribute, avoid common errors, and output the exact answer span. (domains=simplevqa, image, reasoning, playbook; triggers=solve simplevqa, detailed guidance, thought process guide, visual reasoning chain, small model guidance); file=`simplevqa/simplevqa-solving-playbook.md`
- `simplevqa-transfer-patterns`: Dataset-level rules for SimpleVQA visual entity recognition and attribute answering. (domains=simplevqa, image, reasoning, evidence; triggers=simplevqa question, image-grounded entity recognition, visual-plus-knowledge qa, atomic_fact, vqa_category); file=`simplevqa/simplevqa-transfer-patterns.md`
- `visual-entity-attribute`: General pipeline for SimpleVQA questions that first require identifying the image entity, then answering a stable attribute about it. (domains=image, simplevqa, entity, attribute; triggers=image entity plus external attribute, atomic_fact available, ocr plus lookup, named landmark, portrait); file=`general/visual-entity-attribute.md`
