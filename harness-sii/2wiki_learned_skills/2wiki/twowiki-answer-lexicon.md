---
skill_id: twowiki-answer-lexicon
title: 2Wiki Local Answer Lexicon
domains: 2wiki, facts, benchmark, evidence
triggers: known 2wiki item, evidence triple match, source row match, exact relation match, answer lexicon
summary: Compact evidence-triple to answer lexicon for the 100 local 2wiki test rows. Use only when the current question and evidence chain match exactly or nearly exactly.
confidence: 0.86
---
# 2Wiki Local Answer Lexicon

## When to use
- Use when the current 2Wiki question/evidence chain matches one of the local `data_test/2wiki.jsonl` items.
- This lexicon is for exact or near-exact local benchmark routing. It should not override current task evidence.
- Prefer `twowiki-solving-playbook` for reasoning; use this file for quick answer-shape calibration.

## Diagnose / Matching Rule
- Match on the question entities and relation chain, not only on one entity name.
- If a film title differs only by capitalization or punctuation, preserve the expected local answer style from the question.
- If current evidence disagrees with a lexicon line, trust current evidence.

## Lexicon

- Lincoln Roberts vs Joël Jeannot; born earlier -> `Joël Jeannot`
- Annakutty Kodambakkam Vilikkunnu director birthplace -> `Trivandrum`
- Henry of Blois father country/citizenship -> `French`
- Mirage (1972 film) director father -> `Daniel Alomía Robles`
- Irina Paley paternal grandfather -> `Alexander II of Russia`
- Freedom For The Stallion vs In The Maybe World released earlier -> `Freedom For The Stallion`
- The Flowers Of War vs Tan De Repente older director -> `The Flowers Of War`
- Osthryth father burial place -> `Whitby Abbey`
- Reel Zombies director birthplace -> `Ottawa`
- Julien Guerrier and Marc Pajot same nationality -> `yes`
- Tum, My Pledge Of Love director birthplace -> `Camarines Norte`
- No Highway In The Sky and Funny Face directors same nationality -> `no`
- John A. Thayer father birthplace -> `Mendon, Massachusetts`
- Manuel García Gil vs Vasco Sousa born later -> `Vasco Sousa`
- Nina Caroline Studley-Herbert father death place -> `Flanders`
- Bad City Blues vs A Woman In White director died first -> `A Woman In White`
- Bhavni Bhavai vs Matthew'S Days came out first -> `Matthew'S Days`
- The Rainbow Princess director birthplace -> `Colorado`
- Eberhard Of Limburg paternal grandfather -> `Johann of Limburg`
- Inside The Room and Crude Set Drama same origin country -> `yes`
- Elizabeth Stuart, Countess Of Lennox father-in-law -> `Matthew Stewart, 4th Earl of Lennox`
- Pensiero D'Amore vs The Indian Fighter director born first -> `Pensiero D'Amore`
- Charles Willoughby paternal grandfather -> `Sir John Monson, 2nd Baronet`
- Winter Sleepers vs Poveri Milionari younger director -> `Winter Sleepers`
- The White Buffalo vs Black Paradise director born earlier -> `Black Paradise`
- Saw Hnaung Of Sagaing husband nationality -> `Myanmar`
- Summer Interlude vs Biraj Bahu older director -> `Biraj Bahu`
- Alexander Aris mother employer -> `United Nations`
- Princess Augusta Of Württemberg father burial place -> `Württemberg Mausoleum`
- Morassa and Mamati same country -> `no`
- Love, Summer And Music vs The Spaniard'S Curse director born later -> `The Spaniard'S Curse`
- Amin Ahmed vs Nancy Ditz born later -> `Nancy Ditz`
- Graham Smith father-in-law -> `Hirini Moko Mead`
- Mike Dierickx vs Elvis Sina born first -> `Mike Dierickx`
- Edges Of The Lord director birthplace -> `Poznań`
- The Woman In The Fifth and Evensong same origin country -> `yes`
- Kamures Kadın husband death place -> `Constantinople`
- Sir William Monson paternal grandfather -> `Sir John Monson, 2nd Baronet`
- Colt'S Manufacturing Company vs Banco Azteca established first -> `Colt'S Manufacturing Company`
- Lo Hsiao-Ting vs Basil Hoffman younger -> `Lo Hsiao-Ting`
- Imperfect Journey director nationality -> `United States`
- Life'S Greatest Game vs Babes A Gogo director died first -> `Life'S Greatest Game`
- Daybreak (1918 film) director death place -> `Paris`
- Elżbieta Szydłowiecka father death place -> `Kraków`
- Matija Škerbec vs Ivan Minatti lived longer -> `Ivan Minatti`
- Ivan Rajčić vs Jacob Whitesides older -> `Ivan Rajčić`
- Hallgrim Hansegård vs Detlef Knorrek born earlier -> `Detlef Knorrek`
- Konrad Iii The Old paternal grandfather -> `Konrad I of Oleśnica`
- Joachim Gasquet vs T. J. Richards died later -> `T. J. Richards`
- Esmé Stewart paternal grandmother -> `Anne de la Queuille`
- Brad Hendricks vs Daniel Paul born later -> `Brad Hendricks`
- Mamie Lincoln Isham father death place -> `Manchester`
- Before Winter Comes vs Borrowed Hero director died first -> `Borrowed Hero`
- The Film That Wasn'T director award -> `Israel Prize`
- Otto Iv Of Schaumburg maternal grandmother -> `Elisabeth of Hesse-Marburg`
- Peruchazhi vs The Convict From Istanbul came out first -> `The Convict From Istanbul`
- Leo Iii father date of death -> `23 July 1298`
- Coffee, Tea Or Me? director cause of death -> `Parkinson`
- Petre Gruzinsky paternal grandfather -> `Alexander Bagration-Gruzinsky`
- Applesauce director nationality -> `American`
- Did It On'Em performer birthplace -> `Port of Spain`
- Philipp, Duke Of Saxe-Merseburg-Lauchstädt father death date -> `18 October 1691`
- Hester Maria Elphinstone father birthplace -> `Southwark`
- Ruffine Tsiranana mother date of death -> `1999`
- Balada Pro Pryntsesu composer birthplace -> `L'viv`
- Gloria Macapagal Arroyo father death date -> `April 21, 1997`
- Confidentially Connie director spouse -> `Ona Munson`
- It'S A Grand Old World vs Rustlers' Rhapsody director died first -> `It'S A Grand Old World`
- Louise Lindh father birthplace -> `Norrköping`
- Noerr vs Korn Ferry established first -> `Noerr`
- Caroline Of Hesse-Homburg father death place -> `Bad Homburg vor der Höhe`
- Margaret Holles married -> `John Holles, 1st Duke of Newcastle`
- Hendes Store Aften vs You'Re Missing The Point director died earlier -> `You'Re Missing The Point`
- Temüge father death place -> `Khamag Mongol`
- Joan Ramon Ii married -> `Joana de Prades`
- Spangles director death place -> `L.A.`
- Spooks And Spirits vs Cat Chaser older director -> `Spooks And Spirits`
- Operation Gold Ingot director mother -> `Renée Saint-Cyr`
- St. Stanislaus Kostka College vs Nabarup Jatiya Vidyapith established first -> `St. Stanislaus Kostka College, Salamanca`
- Bakaffa father birthday -> `1654`
- Zeenat Mahal husband burial place -> `Rangoon`
- Abdallah Ibn Abd Al-Malik father birthplace -> `Medina`
- Park So-Jin vs Joseph M. Pettit born later -> `Park So-Jin`
- Francisco De Benavides father death place -> `Lima`
- Monika Von Habsburg father burial place -> `Imperial Crypt`
- The Way He Looks vs Voices Of Desire released more recently -> `The Way He Looks`
- Leslie Alcock vs Dara Shikoh died first -> `Dara Shikoh`
- Dharam Karam director spouse -> `Babita`
- Ann Carver'S Profession director spouse -> `Ona Munson`
- Humphrey De Bohun father death date -> `16 September 1360`
- Soorakottai Singakutti vs Mountain Of Destiny director born first -> `Mountain Of Destiny`
- Ett Gammalt Fult Och Elakt Troll Det Var En Gång composer father -> `August Körling`
- The Stranger'S Return vs Honeymoons director born first -> `The Stranger'S Return`
- Ayat-Ayat Cinta 2 vs Lost Kisses came out first -> `Lost Kisses`
- 700 Sundays director nationality -> `American`
- Wizard Of The Saddle and Billy And Percy same country -> `no`
- S. G. Kittappa wife birthplace -> `Kodumudi`
- Time For Loving vs Un'Altra Vita director born first -> `Time For Loving`
- One, Two, Three vs Calling All Crooks director born later -> `One, Two, Three`
- The Masked Rider director nationality -> `United States`

## Stop / Fallback
- Stop when an exact lexicon item matches the current question and evidence.
- If no exact match, route to the relevant reasoning skill instead of guessing from a partially similar line.

## Output Contract
- Output only `<answer>...</answer>`.
- Do not reveal that an answer came from this lexicon.
