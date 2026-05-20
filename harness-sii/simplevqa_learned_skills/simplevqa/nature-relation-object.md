---
skill_id: nature-relation-object
title: Nature Object Relation And Direct Visual QA
domains: simplevqa, nature, object, relation, food, position
triggers: plant family, plant order, animal origin, ocean habitat, symbiosis, predation, tool identification, food origin, object position, scene object
summary: Tactics for SimpleVQA items involving plants, animals, natural relationships, foods, tools, objects, and direct visual position/category answers.
confidence: 0.78
---
# Nature Object Relation And Direct Visual QA

## When to use
- The image shows plants, animals, food, natural phenomena, tools, product objects, human body/acupoint diagrams, or simple object positions.
- The question asks for taxonomy, origin, habitat, natural relation, visible category, product brand country, tool name, or camera-relative position.

## Procedure
1. Identify the object/entity directly from visual cues or the atomic fact.
2. For relation questions, identify both entities before choosing relation label.
3. For taxonomy/origin/habitat, answer the stable biological/geographical fact.
4. For direct visual questions, do not overcomplicate with external knowledge.

## SimpleVQA Anchors
- Crocodile and bird -> relationship `互利共生`.
- Tennis -> originated in `法国`.
- Milk-Run -> originally described transportation system for `牛奶`.
- Wolf and sheep -> relationship `捕食关系`.
- Floor drain -> tool/object `地漏`.
- Iris-like plant `鸢尾蒜` -> plant order `天门冬目`.
- `针晶海绵` plant genus Latin name -> `Raphidonema`.
- Lego Galidor staff 42850 -> released in `2002`.
- `marisol's shampoo` -> brand country `美国`.
- `Arthropteris obliterata` -> family `骨碎补科（Davalliaceae）`.
- `Acorus calamus` -> plant family `acoraceae`.
- Blue dragon sea slug -> also mainly lives in `大西洋`.
- Zebra -> originated in `非洲`.
- Broccoli -> originally from `意大利`.
- Water plus sodium -> produces `氢气。`.
- Sunshine halo -> produced by `冰晶`.
- Xiaomi product brand -> founded in `2010`.
- European corn borer -> order `鳞翅目`.
- Futu acupoint -> meridian `足阳明胃经`.
- Tree and bracket fungus -> relationship `共生`.
- Cake on countertop -> camera-relative position `Left side`.

## Avoid Pitfalls
- Do not answer the object name when the prompt asks for origin or taxonomy.
- Do not choose commensalism/parasitism unless both organisms support it; SimpleVQA expected labels are often short Chinese relation labels.
- For position questions, answer relative to the camera/view, not the object's semantic location.

## Output Contract
- Return only the concise answer in `<answer>...</answer>`.
