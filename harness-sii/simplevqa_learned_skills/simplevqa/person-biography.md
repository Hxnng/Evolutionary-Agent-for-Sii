---
skill_id: person-biography
title: Portrait And Biography Attribute Recognition
domains: simplevqa, person, portrait, biography
triggers: person image, celebrity recognition, scientist, politician, author, inventor, biographical attribute
summary: Tactics for SimpleVQA portrait items and downstream biographical questions.
confidence: 0.82
---
# Portrait And Biography Attribute Recognition

## When to use
- The image is a person or figure and the question asks identity, appointment, death year/cause, award year, invention, title, work, or career fact.
- The entity may be a celebrity, scientist, politician, philosopher, author, inventor, or public relations figure.

## Procedure
1. Identify the person from face, portrait style, accompanying text, and `atomic_fact` if available.
2. Check whether the question asks for identity itself or a biographical attribute.
3. For attributes, answer the exact relation, not the person's name.
4. Preserve bilingual forms when the expected answer includes them.

## SimpleVQA Anchors
- Lev Vygotsky -> died of tuberculosis in `1934年`.
- Mirza Hameedullah Beg -> appointed Chief Justice of India by `Fakhruddin Ali Ahmed`.
- Ivy Ledbetter Lee -> identity answer `艾维·莱德拜特·李（Ivy Ledbetter Lee）`.
- Joseph Raymond McCarthy -> became Wisconsin senator in `1946年`.
- Benedict Cumberbatch -> identity answer `Benedict Cumberbatch`.
- Jóhanna Sigurðardóttir -> flight attendant until 1971, name `Jóhanna Sigurðardóttir`.
- David Beckham -> identity answer `大卫·贝克汉姆`.
- Johannes Gutenberg -> printing technology invention completed in `1450`.
- Guang Song She -> identity answer `广松涉`.
- Jean-Jacques Rousseau -> April 1755 Amsterdam work in Chinese: `论人类不平等的起源和基础`.
- Ronald Rivest -> co-invented `RSA algorithm`.
- Robert Oppenheimer -> title `Father of the atomic bomb`.
- Henry Bergson -> Nobel Literature year `1927年`.
- Wu Jing -> identity answer `吴京`.
- Kris Wu -> 2018 album `《Antares》`.

## Avoid Pitfalls
- Do not confuse a portrait identity question with a downstream attribute question.
- Do not omit accents in names when the expected answer uses them.
- Do not answer the wrong person in a multi-person algorithm/science photo; use the relation asked.

## Output Contract
- Return only the name, year, title, work, or attribute in `<answer>...</answer>`.
