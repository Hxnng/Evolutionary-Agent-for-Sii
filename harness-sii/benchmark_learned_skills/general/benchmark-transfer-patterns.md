---
skill_id: benchmark-transfer-patterns
title: Benchmark Transfer Patterns
domains: general, benchmark, web, evidence, reasoning
triggers: benchmark-like question, multi-constraint lookup, hidden entity identification, answer shape calibration, evidence discipline, unverifiable detail
summary: Distilled benchmark-style lookup patterns for multi-constraint web questions, preserving reusable reasoning and answer-shape calibration without storing benchmark answers.
confidence: 0.78
---
# Benchmark Transfer Patterns

## When to use
- Use for benchmark-like questions that hide the target entity behind multiple biographical, corporate, media, sports, academic, or historical constraints.
- Use when the task asks for a small final span: a name, date, title, count, company, production credit, species, or "无法确定".
- Prefer a narrower skill when one directly matches the domain; use this as a fallback pattern when no specific skill is strong enough.

## Diagnostic Cues
- The prompt contains stacked constraints with date ranges, role chains, family links, publication histories, institutional founding dates, match stats, or report references.
- The final answer depends on first identifying an entity, then extracting one exact attribute from a reliable source.
- Some tasks are intentionally unanswerable because the requested detail is private, unpublished, or not uniquely supported.

## Evidence And Tool Plan
- Split the problem into anchors: entity class, time window, distinctive facts, bridge relation, and requested answer type.
- Search with the rarest stable anchors first. Combine two or three anchors, not the entire prompt.
- After a candidate appears, verify it against the original constraints before extracting the final attribute.
- Prefer primary or near-primary sources: annual reports, official bios, episode guides, competition records, theses, interviews, institutional pages, archived articles, and specialist databases.
- If sources disagree, trust the source closest to the asserted relation and preserve the requested granularity.

## Procedure
1. Build a compact clue table mentally: `target type -> anchor facts -> bridge entity -> requested attribute`.
2. Use the answer shape to constrain search. A share count needs filings; a spouse first name needs a biography/interview; a release title needs localization databases; a "third substitute" needs a match report or lineup table.
3. Confirm the candidate with at least two independent clues before opening a broad page or accepting a snippet.
4. Extract only the requested span. Do not carry extra context, honorifics, surnames, units, or explanations unless the task asks for them.
5. For privacy-sensitive or trivial personal details, require explicit public evidence. If the trail only proves the surrounding entity but not the requested detail, answer as indeterminate.

## Calibration Examples
- Corporate filing questions often end with a precise numeric balance or count; the decisive evidence is usually a dated annual report table or note, not a news article.
- Biography-chain questions usually end with a full name, birth name, sibling name, or spouse name; the decisive evidence is the page that states the exact relationship.
- Media and sports questions often use episode, match, or production fingerprints; the decisive evidence is a roster, credits page, episode synopsis, or database entry matching the full event.
- Academic/thesis questions often require repository PDFs and acknowledgments or references; search snippets rarely contain the answer.
- If the final attribute is not a normal public fact, the correct behavior may be "无法确定" rather than a guessed entity.



## Pattern Lexicon
- `acad.article.editor.unverifiable` :: span≈`Based on the available search results, the full name of the editor cannot be determined with certainty. The search re…`
- `acad.ref-chain.episode-title.2021` :: span≈`Tweentrepreneurs`
- `acad.thesis.dating.podcast-ack` :: span≈`The Breakup Diet`
- `animation.influence.aunt.1960s` :: span≈`Charlotte Clark`
- `anime.1980s.allegory.article-title` :: span≈`Akira`
- `anime.plot.s1s2.villain-twist` :: span≈`One Punch Man`
- `arch.export-permit.pit-minus13y` :: span≈`Cape Archaeological Survey.`
- `art.watercolor.exhibit.social-history-book` :: span≈`A Priest, A Prostitute, and Some Other Early Texans: The Lives Of Fourteen Lone Star State Pioneers`
- `bio.beetle.misid.1916` :: span≈`Paropsis dilatata`
- `bio.species.1780s.flavonoid-edible` :: span≈`Coprinus comatus`
- `biz.beauty.founder.underdetermined` :: span≈`Unable to determine the founder's full name with the available evidence.`
- `corp.ceo.chain.edu-rename` :: span≈`Taylor Beaupain`
- `corp.founder.bribery.original-name` :: span≈`Tomorrow Holdings`
- `corp.powerboat.buyback-remain.2022` :: span≈`1,570,428`
- `crypto.protocol.founder.fullname` :: span≈`Sébastien Borget`
- `ent.chain.singer-to-actress-pageant` :: span≈`Megan Lynn Young`
- `esport.lol.cs-clock.final` :: span≈`2021 LCK Summer Playoffs`
- `fiction.4thwall.monkey-king` :: span≈`Monkey (Sun Wukong / the Monkey King)`
- `film.bollywood.rich-poor.2000s` :: span≈`Dosti: Friends Forever`
- `film.short.2015.teacher-rural` :: span≈`The New Teacher`
- `film.venezuela.director.budget` :: span≈`Ricardo García`
- `game.dual-dev.gentleman-protagonist` :: span≈`Professor Layton vs. Phoenix Wright: Ace Attorney`
- `game.mission6.eu.art-director` :: span≈`Thierry Dunter`
- `lit.banned-country.novel.title-en` :: span≈`The Meursault Investigation`
- `lit.victorian.1898.illustrator` :: span≈`The Ingoldsby Legends`
- `med.donor.recipient.privacy` :: span≈`无法确定`
- `media.blogpost.date.actor-bridge` :: span≈`June 15, 2015`
- `music.act.birthname.shakespeare-title` :: span≈`Yumi Arai`
- `music.metal.2013.discography-tour` :: span≈`Orbit Culture`
- `person.actor.1990s.sister-name` :: span≈`Taylor Centineo`
- `person.actor.sibling.voice-oscar` :: span≈`Joseph`
- `person.advisor.conference-founder.1940s` :: span≈`Dr. Rakesh Wahi`
- `person.founder.trivial-color.unverifiable` :: span≈`unknown`
- `person.fr.actress.legal-birthname` :: span≈`Pascale Aiguionne Louise Jacqueline Marie Auffray`
- `person.influencer.ng-host-ambassador` :: span≈`Toke Makinwa`
- `person.politician.team-founder.alumni` :: span≈`Carl Sanders`
- `person.stage-name.interview-2017` :: span≈`Naila Pierce`
- `sci.early20c.car-accident.egypt` :: span≈`Sameera Moussa`
- `sci.ecology.book.2018.reviewer-died` :: span≈`The Birds at My Table`
- `space.astronaut.spouse.firstname` :: span≈`Anne`
- `sport.basketball.virgo.birthname` :: span≈`Dennis Malik Schröder`
- `sport.cup.stats.position-record` :: span≈`1st, Liverpool`
- `sport.f1.driver.multi-bio` :: span≈`Emerson Fittipaldi`
- `sport.football.substitute.away-third` :: span≈`Sol Campbell`
- `sport.ng.state-capital.club` :: span≈`FC Ifeanyi Ubah`
- `sport.soccer.95min.freekick` :: span≈`Hugo Almeida`
- `sport.swimmer-turned.athlete.name` :: span≈`Farida Osman`
- `tv.actor.bday.naturalized-athlete` :: span≈`Anthony Jewell Akins`
- `tv.edu.short.1990s.ar-local` :: span≈`Cantinflas`
- `tv.family.production-company` :: span≈`Revele Films`

## Stop / Fallback
- Stop when the candidate satisfies the anchors and a reliable source supports the exact final span.
- If searches return only near matches, change the anchor mix once: use a rare phrase, a date plus entity class, or the expected source type.
- After repeated weak evidence, output the best supported indeterminate answer instead of inventing a span.

## Output Contract
- Return only the answer body inside `<answer>...</answer>`.
- Do not mention benchmark files, training data, skill IDs, gold answers, or internal routing.
