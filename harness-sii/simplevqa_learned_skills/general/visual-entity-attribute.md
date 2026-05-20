---
skill_id: visual-entity-attribute
title: Visual Entity To Attribute Answering
domains: image, simplevqa, entity, attribute, evidence
triggers: image entity plus external attribute, atomic_fact available, OCR plus lookup, named landmark, portrait, poster, book, diagram
summary: General pipeline for SimpleVQA questions that first require identifying the image entity, then answering a stable attribute about it.
confidence: 0.82
---
# Visual Entity To Attribute Answering

## When to use
- The image shows a recognizable entity and the question asks for an attribute that is not necessarily visible.
- The task provides or implies an `atomic_fact` such as a person name, landmark, book title, film title, plant, algorithm, company, or treaty.
- The answer should be a compact span, not a description of the image.

## Diagnostic Cues
- "图中人物/图中这本书/this movie/this bridge/this church/the algorithm shown/the plant in the picture".
- The question asks for a date, discoverer, author, country, family, place, award, designer, disease, origin, or count.
- Wrong answers usually come from answering the category instead of the requested relation.

## Evidence And Tool Plan
- Direct image evidence: use for entity name when text/logo/landmark is visible, and for simple position or scene category.
- Dataset anchor: if `atomic_fact` is present, use `atomic_fact + relation` as the search/lookup key.
- Search: use only when the fact lexicon or stable knowledge is insufficient. Query pattern: `"entity" + "requested relation"`.
- Verification: make sure the found fact belongs to the exact entity, not a broader category or a similarly named item.

## Procedure
1. Build a compact table: `image entity`, `entity class`, `question relation`, `answer unit`.
2. Decide whether the question is asking for identity itself or a downstream property.
3. If identity itself: answer the canonical name from the strongest visual/OCR cue.
4. If downstream property: lock the entity first, then retrieve only the requested property.
5. Apply answer normalization:
   - Chinese year questions often require `1934年`, `1970年`, or bare `1998` depending on the gold style.
   - English location/country questions may expect short forms like `UK` or `USA`.
   - Names may require bilingual aliases when the dataset answer includes them.

## Avoid Pitfalls
- Do not answer "tennis" when asked where tennis originated.
- Do not answer a movie title when asked its country of origin.
- Do not answer a broad landmark type when asked for a specific landmark name.
- Do not translate away proper nouns if the expected answer preserves English.
- Do not add explanations after the answer span.

## Output Contract
- Final answer must be only `<answer>ANSWER</answer>`.
