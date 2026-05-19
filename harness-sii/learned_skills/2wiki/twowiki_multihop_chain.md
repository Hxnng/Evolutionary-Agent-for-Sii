---
skill_id: twowiki_multihop_chain
title: 2Wiki Evidence-Graph Multihop Chain
domains: 2wiki, multihop, evidence-graph, compositional
triggers: 2WikiMultihopQA, Context packet, compositional, inference, Evidence triples, --director-->, --father-->, --mother-->, --place of birth-->
summary: 当 2Wiki 问题需要沿 evidence triples 从题目实体经过桥接实体到最终属性时使用，优先基于紧凑证据图推理而不是重新搜索。
confidence: 0.90
---
# 2Wiki Evidence-Graph Multihop Chain

Use this skill when a 2WikiMultihopQA context packet provides evidence triples and the question asks for a property reached through one or more bridge entities.

## When to use
- The packet says `Question type: compositional` or `inference`.
- The question asks for a relation of an intermediate entity, such as mother/father/director/birthplace/award/date of death.
- Evidence triples form a chain like `A --relation1--> B` and `B --relation2--> C`.
- Do not use this skill for direct date/country comparisons unless the main operation is first to build a bridge entity.

## Diagnose / Credit Assignment
- Identify the start entity mentioned in the question and the final relation being asked.
- Mark the bridge entity created by the first triple; do not answer the bridge when the question asks for the bridge's attribute.
- If a prior answer used a distractor title from candidate context, treat it as evidence-selection failure.
- If a prior answer returned a supporting-fact title instead of the triple object, treat it as answer-span failure.

## Evidence and Context Procedure
- Read `Evidence triples` first. Treat them as the compact reasoning graph.
- Order triples by graph dependency, not by their printed order, when the question makes the chain direction clear.
- Use supporting sentences only to confirm ambiguous titles, date formats, aliases, or relation wording.
- Ignore candidate documents whose titles are not in the graph unless the packet lacks a needed relation.
- Preserve exact entity spelling from the triple object when it is the final answer.

## Reasoning Procedure
- Convert the question to a graph query: start entity, relation to bridge, relation from bridge to answer.
- Follow the chain step by step and keep only the active entity at each hop.
- For relation wording variants, map question phrases to predicates: `who directed` -> director, `where was born` -> place of birth, `when did die` -> date of death, `mother/father` -> parent relation.
- Return the final object of the last required triple, not the whole path.

## Tool Plan
- Do not use web search when the evidence triples already contain the full chain.
- Use search/browser only if the packet is missing a needed relation or contains conflicting triples, which should be rare in 2Wiki evaluation.
- If tools are unavailable, answer from the evidence graph rather than guessing from world knowledge.

## Memory Layer Policy
- Short-term memory may record recent chain failures, such as answering the bridge entity, reversing an edge, or using a distractor context title.
- Promote to long-term only when the update improves chain ordering, relation normalization, evidence selection, or answer-span control.
- Do not store specific 2Wiki entity facts as durable skill memory.

## Stop / Fallback
- Stop when the graph path yields a single final object matching the requested answer type.
- If multiple triples share the same predicate, choose the one whose subject matches the active entity.
- If no graph path exists, use supporting sentences to reconstruct the missing edge; otherwise answer from the best supported packet evidence.

## Output Contract
- Output exactly the final entity/date/place/name inside `<answer>...</answer>`.
- Do not include the bridge entity, relation path, citations, or explanation.
