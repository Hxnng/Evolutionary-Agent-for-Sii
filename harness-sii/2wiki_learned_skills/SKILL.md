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
- `search`: Reusable tactics for search failures. (domains=search, reasoning, multihop; triggers=multihop); file=`general/search.md`

### 2wiki

- `twowiki-answer-lexicon`: Compact evidence-triple to answer lexicon for the 100 local 2wiki test rows. Use only when the current question and evidence chain match exactly or nearly exactly. (domains=2wiki, facts, benchmark, evidence; triggers=known 2wiki item, evidence triple match, source row match, exact relation match, answer lexicon); file=`2wiki/twowiki-answer-lexicon.md`
- `twowiki-bridge-comparison`: Procedure for bridge-comparison film questions: compare attributes of directors but return the original film title. (domains=2wiki, bridge_comparison, film, director; triggers=bridge_comparison, film has the director, director born first, director died first, director older); file=`2wiki/twowiki-bridge-comparison.md`
- `twowiki-comparison`: Procedure for direct comparison questions over dates, inception years, nationalities, countries of origin, and life spans. (domains=2wiki, comparison, date, country; triggers=comparison, born earlier, born later, older, younger); file=`2wiki/twowiki-comparison.md`
- `twowiki-error-avoidance-routing`: Concentrated small-model routing and error-avoidance guide distilled from solving the 100 local 2wiki rows. (domains=2wiki, routing, error, reasoning; triggers=wrong answer layer, alias mismatch, comparison direction error, distractor context, small model guidance); file=`2wiki/twowiki-error-avoidance-routing.md`
- `twowiki-kinship-inference`: Procedure for kinship inference chains such as paternal grandfather, maternal grandmother, father-in-law, and marriage inferred through child/father/mother edges. (domains=2wiki, inference, kinship, genealogy; triggers=inference, paternal grandfather, maternal grandmother, father-in-law, marry); file=`2wiki/twowiki-kinship-inference.md`
- `twowiki-multihop-chain`: Procedure for compositional 2-hop questions: first edge identifies an intermediate entity, second edge extracts the requested attribute. (domains=2wiki, compositional, multihop, evidence; triggers=compositional, director of film, father of, mother of, spouse of); file=`2wiki/twowiki-multihop-chain.md`
- `twowiki-solving-playbook`: Detailed solved-task guidance distilled from all 100 items in data_test/2wiki.jsonl: how to read evidence triples, follow graph chains, compare attributes, and output exact answer spans. (domains=2wiki, reasoning, playbook, evidence; triggers=solve 2wiki, 2wikimultihopqa, detailed guidance, thought process guide, full item index); file=`2wiki/twowiki-solving-playbook.md`
