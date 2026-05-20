---
skill_id: twowiki-kinship-inference
title: 2Wiki Kinship Inference Chains
domains: 2wiki, inference, kinship, genealogy, reasoning
triggers: inference, paternal grandfather, maternal grandmother, father-in-law, marry, father, mother, spouse, child
summary: Procedure for kinship inference chains such as paternal grandfather, maternal grandmother, father-in-law, and marriage inferred through child/father/mother edges.
confidence: 0.88
---
# 2Wiki Kinship Inference Chains

## When to use
- Use for `type=inference` rows and any question asking paternal/maternal grandparent, father-in-law, or who someone married.
- These questions often require following two family edges and translating a relationship phrase into graph direction.

## Diagnostic Cues
- Phrases include `paternal grandfather`, `maternal grandmother`, `father-in-law`, `Who did X marry?`.
- Evidence triples are family relations: father, mother, spouse, child.
- The final answer is usually the object of the second family edge.

## Evidence And Tool Plan
- Prefer evidence triples. Genealogy candidate pages contain many relatives and are easy to misread.
- Normalize titles carefully: noble titles and ordinal suffixes are part of the expected answer.
- Do not use broad web knowledge for royal/noble families unless local context is incomplete.

## Procedure
1. Translate the kinship phrase:
   - paternal grandfather -> `person --father--> father --father--> answer`.
   - maternal grandmother -> `person --mother--> mother --mother--> answer`.
   - father-in-law -> `person --spouse--> spouse --father--> answer`.
   - who did X marry, when evidence starts from a child -> `X --child--> child --father/mother--> spouse`, then return the other parent named in the second edge.
2. Follow the evidence in order and ignore distractor relatives in candidate context.
3. Return the exact person title/name from the second edge object.

## Small-Model Thought Guide
- Convert the English kinship phrase into edge operations before reading long context.
- For grandfather/grandmother questions, the first edge decides paternal vs maternal:
  - paternal uses father first.
  - maternal uses mother first.
- For father-in-law, do not look for the target person's father; look for the spouse's father.
- For marry questions, 2Wiki may encode marriage indirectly through a child. If `X --child--> C` and `C --father/mother--> Y`, then Y can be X's spouse when Y is the other parent.
- Noble titles are part of the name. Do not shorten `John Holles, 1st Duke of Newcastle` to `John Holles`.

## Solved Pattern Examples
- Irina Paley -> father Grand Duke Paul Alexandrovich -> father Alexander II of Russia; answer `Alexander II of Russia`.
- Otto IV of Schaumburg -> mother Maria of Nassau -> mother Elisabeth of Hesse-Marburg; answer `Elisabeth of Hesse-Marburg`.
- Elizabeth Stuart -> spouse Charles Stuart -> father Matthew Stewart; answer `Matthew Stewart, 4th Earl of Lennox`.
- Margaret Holles -> child Lady Henrietta -> father John Holles; answer `John Holles, 1st Duke of Newcastle`.

## Stop / Fallback
- Stop after the second family edge. Do not continue to grandparents unless the question asks for them.
- If the first edge says `child`, infer marriage only when the second edge identifies the child's other parent.
- Preserve diacritics, ordinals, and titles.

## Output Contract
- Output only `<answer>person name/title</answer>`.
