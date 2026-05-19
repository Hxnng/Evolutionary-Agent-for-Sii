# Learned Skill Index

This is a compact routing index for long-term learned skills.

Use it to choose which skill files are worth reading. Do not paste this index or whole skill files into generator context.

## How Curator Uses This

1. Read the current question first: answer type, entities, relation, evidence already present, and the exact missing evidence.
2. Use this index only for routing. Select a skill only when its summary/triggers match the question's concrete risk.
3. Read at most the few selected skill bodies, digest them, then write a short problem-specific context for generator.
4. The generator context should contain actions, evidence gaps, tool conditions, stop rules, and answer contract. It should not contain skill names, skill prose, or system prompts.
5. If no skill strongly matches, use `general/memory.md` as a fallback process, not as a source of facts.

## How Reflector Uses This

1. Do credit assignment from the trajectory: evidence, tool, reasoning, stopping, or output-format failure.
2. Update only the skill whose trigger truly matches the reusable failure mode.
3. Create a new knowledge/task skill only when the pattern has a narrow stable trigger and a reusable procedure.
4. Do not store one-off benchmark answers, task IDs, raw trajectory text, or short-term episode facts here.

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
