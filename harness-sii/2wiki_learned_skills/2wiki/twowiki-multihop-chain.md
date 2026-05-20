---
skill_id: twowiki-multihop-chain
title: 2Wiki Compositional Two-Hop Chain
domains: 2wiki, compositional, multihop, evidence, reasoning
triggers: compositional, director of film, father of, mother of, spouse of, composer of, performer of, place of birth, place of death, date of death, nationality, country of citizenship
summary: Procedure for compositional 2-hop questions: first edge identifies an intermediate entity, second edge extracts the requested attribute.
confidence: 0.90
---
# 2Wiki Compositional Two-Hop Chain

## When to use
- Use for `type=compositional` rows or questions that ask an attribute of a related entity: director, father, mother, spouse, composer, performer, child, place of burial.
- Common shapes: "Where was the director of film X born?", "What nationality is X's husband?", "When did X's father die?"
- Use when evidence triples usually have exactly two edges and the final answer is the object of the second edge.

## Diagnostic Cues
- The question contains a nested noun phrase: `director of film`, `father of`, `mother of`, `spouse of`, `composer of song`, `performer of song`.
- The first evidence triple maps the named question entity to an intermediate person.
- The second evidence triple maps that intermediate person to the requested answer attribute.

## Evidence And Tool Plan
- Prefer `Evidence triples` if present. They are already the distilled graph path.
- If using raw candidate context, read the supporting title for the named entity first, then the supporting title for the intermediate entity.
- Do not search outside the context unless the supplied context is truncated before the second edge.

## Procedure
1. Mark the named start entity exactly as it appears in the question.
2. Extract the first relation from the noun phrase: film -> director, person -> father/mother/spouse, song -> composer/performer.
3. Bind the intermediate entity from the first triple.
4. Extract the second relation from the wh-word phrase: where born -> place of birth; where died -> place of death; when died -> date of death; nationality/from -> country of citizenship; spouse/mother/father/award/cause -> that exact relation.
5. Return the object of the second triple, not the intermediate entity.

## Small-Model Thought Guide
- Before answering, write an internal three-slot path: `start entity | intermediate entity | requested attribute`.
- If the current candidate answer equals the intermediate entity, it is probably wrong unless the question explicitly asks "who is the director/father/mother/spouse".
- Translate common question phrases:
  - `Where was X born?` -> `place of birth`.
  - `Where did X die?` / `place of death of X` -> `place of death`.
  - `When did X die?` / `date of death of X` -> `date of death`.
  - `What nationality is X?` / `Which country X is from?` -> use `country of citizenship` object as written.
  - `What is the award that X won?` -> `award received`.
  - `cause of death of director/person` -> `cause of death`.
- Use exact granularity. If evidence says `April 21, 1997`, do not shorten to `1997`; if evidence says `American`, do not rewrite to `United States`.

## Worked Reasoning Sketches
- Film director birthplace: identify film title -> director -> director place of birth -> output place.
- Person father birthplace: identify person -> father -> father's place of birth -> output place.
- Song performer birthplace: identify song -> performer -> performer's place of birth -> output place.
- Film director spouse/mother/father: identify film -> director -> requested relative -> output relative name.

## Solved Pattern Examples
- `Annakutty Kodambakkam Vilikkunnu --director--> Jagathy Sreekumar --place of birth--> Trivandrum`, answer `Trivandrum`.
- `Henry of Blois --father--> Stephen --country of citizenship--> French`, answer `French`.
- `Coffee, Tea or Me? --director--> Norman Panama --cause of death--> Parkinson`, answer `Parkinson`.
- `Did It On'em --performer--> Nicki Minaj --place of birth--> Port of Spain`, answer `Port of Spain`.

## Stop / Fallback
- Stop as soon as the second edge object is found.
- If the second edge subject is an alias of the intermediate entity, accept it when the context clearly links them.
- If the model is tempted to answer the first-hop entity, re-read the wh-word phrase before finalizing.

## Output Contract
- Output only `<answer>second-edge object</answer>`.
- Preserve punctuation/diacritics from the evidence or question title.
