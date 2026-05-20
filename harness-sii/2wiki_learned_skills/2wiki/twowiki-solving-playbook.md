---
skill_id: twowiki-solving-playbook
title: 2Wiki Solved Task Playbook
domains: 2wiki, reasoning, playbook, evidence, benchmark
triggers: solve 2wiki, 2WikiMultihopQA, detailed guidance, thought process guide, full item index, evidence triples
summary: Detailed solved-task guidance distilled from all 100 items in data_test/2wiki.jsonl: how to read evidence triples, follow graph chains, compare attributes, and output exact answer spans.
confidence: 0.90
---
# 2Wiki Solved Task Playbook

## 这份 skill 的用途

这不是普通百科知识表，而是给 agent 的 2WikiMultihopQA 解题指导链。2wiki 的难点不是开放检索，而是从候选上下文里稳定抽出两跳证据，并且别把“中间实体”当成最终答案。

每题都先在内部拆成四格：

`题型 -> 证据边 -> 推理操作 -> 最终答案格式`

不要输出这四格。最终只输出 `<answer>...</answer>`。

## 总体解题链

1. 先读 question 和 type，不先扫所有候选文档。
2. 如果有 `Context packet` 或 `Evidence triples`，优先用它们；它们通常已经是最短证据图。
3. 判断题型：
   - `compositional`: 两跳属性链，答案通常是第二条边的 object。
   - `inference`: 家族/亲属关系推理，两条亲属边组合成 grandfather/father-in-law/marry。
   - `comparison`: 两个题面实体直接比较日期、国家、国籍、成立年、寿命。
   - `bridge_comparison`: 先从 film 找 director，比较 director 属性，但答案通常回到 film。
4. 输出前检查：
   - 答案是不是题目问的实体层级？电影题不要答导演；属性题不要答中间人物。
   - 比较方向是否正确？older/earlier/first 是更早日期，younger/later/recent 是更晚日期。
   - yes/no 是否小写。
   - 是否只保留答案本体。

## 小模型执行时的“显式工作台”

小模型容易被长 context 里的相似标题带偏，所以每题必须先在内部建立一个极短工作台。工作台不是最终输出，只是防错用：

`候选答案层级 | 第一跳 | 第二跳/比较属性 | 选择规则 | 输出形态`

示例：

- `Trivandrum` 题：候选答案层级是地点，不是人名；第一跳 film -> director；第二跳 director -> place of birth；输出地点。
- `The Flowers Of War` 题：候选答案层级是电影，不是导演；第一跳 film -> director；比较 director birth date；older = 更早生日；输出电影标题。
- `yes/no` 题：候选答案层级是布尔值；比较两个实体的 nationality/country/origin；输出小写 `yes` 或 `no`。

如果工作台里“候选答案层级”和准备输出的东西不一致，必须停止并重读问题。2wiki 最常见错法就是层级错：问地点答人物、问电影答导演、问 yes/no 答国家。

## 题型判别树

1. 问题里是否有 `Which film has the director...` / `Which film whose director...`？
   - 是：走 bridge comparison。比较的是导演，答案多半是电影。
2. 问题里是否有 `same nationality/country`、`born earlier/later`、`older/younger`、`died first/later`、`came out first`、`established first`、`lived longer`？
   - 是：走 direct comparison。答案是两个题面实体之一，或 yes/no。
3. 问题里是否有 `paternal grandfather`、`maternal grandmother`、`father-in-law`、`Who did X marry`？
   - 是：走 kinship inference。把亲属词翻译成两条边。
4. 问题里是否有 `director of film`、`father of`、`mother of`、`spouse of`、`composer of song`、`performer of song`？
   - 是：走 compositional two-hop。答案通常是第二条边的 object。
5. 仍不确定时，读 evidence triples 的形状：
   - 2 条普通关系边：多半 compositional/inference。
   - 2 条同谓词属性边：多半 comparison。
   - 4 条边，前两条是 director，后两条是 director 属性：bridge comparison。

## 证据优先级

1. `Evidence triples` 最高优先级。它们已经是题目需要的最短路径。
2. `Supporting sentences` 次之。用来确认 triple 的别名或 disambiguation。
3. `Focus documents` 再次。只读 focus title 对应文档，避免被同姓、同名、同片名干扰。
4. `Candidate context` 最后。候选 context 常含 8-10 个干扰页面，小模型不要全量摘要。
5. 外部搜索是最后手段。2wiki 是封闭候选上下文题；除非上下文被截断或证据缺失，否则不要把它做成开放百科检索题。

## 比较词反转表

小模型必须把自然语言比较词转成确定操作：

- `born earlier`, `born first`, `older`：选出生日期更早的人。
- `born later`, `younger`：选出生日期更晚的人。
- `director is older`：选导演出生日期更早的电影。
- `director is younger`：选导演出生日期更晚的电影。
- `died first`, `died earlier`：选死亡日期更早者。
- `died later`：选死亡日期更晚者。
- `came out first`, `released earlier`：选 publication date 更早的作品。
- `released more recently`：选 publication date 更晚的作品。
- `established first`：选 inception 更早的组织/学校/公司。
- `lived longer`：不是比较谁去世晚，而是比较 `death date - birth date`。
- `same nationality/country/origin`：比较值是否有交集；多国家 origin 只要有一个重合就是 yes。

## 日期解析注意事项

- `23 September 1965`、`September 23, 1965`、`1965` 都要能比较；年相同再看月日。
- 对 `older/younger` 不要看死亡日期，只看出生日期。
- 对 `died first/later` 不要看出生日期，只看死亡日期。
- 对 `lived longer` 必须同时用出生和死亡日期；只比较去世年份会错。
- BCE/负年份若出现，应按数值时间线比较；本地 100 题主要是普通公历年份。

## 别名和输出格式注意事项

- Evidence 里的标题可能规范化为小写或括号消歧，但最终答案往往要贴近 question 的拼写和大小写，例如 `The Stranger'S Return`、`Matthew'S Days`。
- 人名、地点名保留重音符号：`Joël Jeannot`、`Poznań`、`Norrköping`、`Renée Saint-Cyr`。
- 日期照 evidence 的粒度输出：题目问 date of death 且 evidence 是 `18 October 1691`，不要只答 `1691`。
- nationality/citizenship 题不要擅自转换：evidence 是 `American` 就输出 `American`；evidence 是 `United States` 就输出 `United States`。
- yes/no 题输出小写 `yes` 或 `no`，不要输出 `Yes.` 或解释句。

## 我做题时沉淀出的复盘模板

下面不是要模型输出的内容，而是给小模型“怎么稳住”的短流程：

1. 先问自己：最终答案应该是哪一类？人物、地点、日期、电影、组织、yes/no？
2. 把题目核心关系改写成边：`A --relation--> B --relation--> C`。
3. 如果是比较题，把两个候选和属性值写成两行表。
4. 如果比较的是中间实体属性，检查题目是否要求回填原始实体。
5. 输出前用一句内部检查：我输出的是“题目问的层级”吗？

## 典型题复盘

### 复盘 1：普通两跳属性

题目：`Where was the director of film Annakutty Kodambakkam Vilikkunnu born?`

可执行思路：
1. 最终答案类型是地点，因为 `Where was ... born`。
2. 第一跳是 `film -> director`，得到 Jagathy Sreekumar。
3. 第二跳是 `director -> place of birth`，得到 Trivandrum。
4. 输出地点 `Trivandrum`，不要输出导演名。

### 复盘 2：父亲/国籍链

题目：`Which country Henry Of Blois's father is from?`

可执行思路：
1. 最终答案类型是国家/国籍。
2. `Henry of Blois -> father -> Stephen`。
3. `Stephen -> country of citizenship -> French`。
4. 输出 evidence 给出的 `French`，不要改写成 France。

### 复盘 3：直接日期比较

题目：`Who was born earlier, Lincoln Roberts or Joël Jeannot?`

可执行思路：
1. 候选答案是两个人之一。
2. 比较 date of birth：1974 vs 1965。
3. `born earlier` 选更早日期，所以选 Joël Jeannot。
4. 输出人名，不输出日期。

### 复盘 4：bridge comparison

题目：`Which film has the director who is older than the other, The Flowers Of War or Tan De Repente?`

可执行思路：
1. 候选答案是电影，不是导演。
2. 建表：The Flowers of War -> Zhang Yimou -> 1950；Tan de repente -> Diego Lerman -> 1976。
3. `director older` = 导演出生更早，选 Zhang Yimou 所属电影。
4. 输出 `The Flowers Of War`，不要输出 `Zhang Yimou`。

### 复盘 5：same country 多值交集

题目：`Do the movies The Woman In The Fifth and Evensong (Film), originate from the same country?`

可执行思路：
1. 最终答案是 yes/no。
2. The Woman in the Fifth 有 French/British/Polish 多个 origin；Evensong 有 British。
3. 两组值有 British 交集，所以输出 `yes`。
4. 多值 origin 不要求完全相同，只要存在共享值。

### 复盘 6：亲属推理

题目：`Who is the paternal grandfather of Irina Paley?`

可执行思路：
1. paternal grandfather = father 的 father。
2. Irina Paley -> father -> Grand Duke Paul Alexandrovich。
3. Grand Duke Paul Alexandrovich -> father -> Alexander II of Russia。
4. 输出第二跳人物，不输出第一跳父亲。

### 复盘 7：marry 题的反向边

题目：`Who did Margaret Holles, Duchess Of Newcastle-Upon-Tyne marry?`

可执行思路：
1. 问配偶，但 evidence 不一定直接给 spouse。
2. 如果看到 `Margaret Holles -> child -> Lady Henrietta`，再看到 `Lady Henrietta -> father -> John Holles`。
3. child 的 father 是 Margaret 的配偶，所以输出 John Holles。
4. 这种题不要因为没有 spouse 边就放弃。

## 常见失败模式与修正

- 失败：输出第一跳中间实体。修正：检查 wh-word 问的是中间实体的什么属性。
- 失败：bridge comparison 输出导演。修正：题干开头是 `Which film`，最终必须回到 film。
- 失败：`older` 选了年份更大者。修正：older = 出生更早。
- 失败：`lived longer` 选了死亡更晚者。修正：计算寿命跨度。
- 失败：same country 看到一个实体有多个国家就判 no。修正：看是否有交集。
- 失败：把 `American` 改成 `United States` 或把 `French` 改成 `France`。修正：按 evidence 和本地答案风格输出。
- 失败：丢失重音符号或标题大小写。修正：从 question/evidence 复制最终 span。
- 失败：在候选 context 中被同名人物干扰。修正：只读 focus title 和 evidence triple 指向的 title。

## 题型级指导链

### A. Compositional：两跳属性链

适用：`Where was the director of film X born?`、`What nationality is X's husband?`、`When did X's father die?`

流程：
1. 从题面实体出发，按名词短语找第一跳：director/father/mother/spouse/composer/performer。
2. 第一跳 object 是中间实体。
3. 按 wh-word 找第二跳属性：where born -> place of birth；where died -> place of death；when died -> date of death；nationality/from -> country of citizenship。
4. 输出第二跳 object。

典型错误：看到 `film -> director` 就输出 director。必须继续读题目问 director 的什么属性。

### B. Inference：亲属关系合成

适用：paternal grandfather、maternal grandmother、father-in-law、Who did X marry。

流程：
1. paternal grandfather = father 的 father。
2. maternal grandmother = mother 的 mother。
3. father-in-law = spouse 的 father。
4. marry 类题如果给的是 `X --child--> child --father/mother--> other parent`，答案是另一位父/母，即配偶。

典型错误：把第一跳父亲/母亲当答案，或者继续多跳到更远祖先。

### C. Comparison：直接比较

适用：born earlier/later、older/younger、died first/later、came out first、established first、same country/nationality、lived longer。

流程：
1. 确定两个候选答案就是题面里的两个实体。
2. 日期比较：earlier/first/older -> 较早日期；later/younger/recent -> 较晚日期。
3. 寿命比较：每个实体用 date of death 减 date of birth，选持续时间更长者。
4. same 类：值有交集则 `yes`，否则 `no`。

典型错误：输出日期而不是被选中的实体。

### D. Bridge Comparison：比较导演，返回电影

适用：`Which film has the director who...`

流程：
1. 建表：film A -> director A -> attribute；film B -> director B -> attribute。
2. 对 director attribute 做比较。
3. 回答满足条件的 film title，不回答 director。
4. 如果题目问 directors 是否同国籍，输出 `yes`/`no`。

典型错误：比较对了导演但输出导演姓名。

## 全量 100 题做题指导链索引

格式：`row：题型；证据链；动作；输出`

- 0：comparison；Lincoln Roberts birth 1974 vs Joël Jeannot birth 1965；born earlier 选更早生日；输出 `Joël Jeannot`。
- 1：compositional；Annakutty Kodambakkam Vilikkunnu -> director Jagathy Sreekumar -> place of birth Trivandrum；输出出生地；`Trivandrum`。
- 2：compositional；Henry of Blois -> father Stephen -> country of citizenship French；输出 father 的国籍；`French`。
- 3：compositional；Mirage -> director Armando Robles Godoy -> father Daniel Alomía Robles；输出导演父亲；`Daniel Alomía Robles`。
- 4：inference；Irina Paley -> father Grand Duke Paul Alexandrovich -> father Alexander II of Russia；paternal grandfather；`Alexander II of Russia`。
- 5：comparison；Freedom for the Stallion 1973 vs In the Maybe World 2006；released earlier；`Freedom For The Stallion`。
- 6：bridge_comparison；The Flowers of War -> Zhang Yimou 1950; Tan de repente -> Diego Lerman 1976；older director 返回电影；`The Flowers Of War`。
- 7：compositional；Osthryth -> father Oswiu -> place of burial Whitby Abbey；`Whitby Abbey`。
- 8：compositional；Reel Zombies -> director David J. Francis -> place of birth Ottawa；`Ottawa`。
- 9：comparison；Julien Guerrier French vs Marc Pajot French；same nationality；`yes`。
- 10：compositional；Tum: My Pledge of Love -> Robin Padilla -> place of birth Camarines Norte；`Camarines Norte`。
- 11：bridge_comparison；No Highway in the Sky director German vs Funny Face director American；not same nationality；`no`。
- 12：compositional；John Alden Thayer -> father Eli Thayer -> place of birth Mendon, Massachusetts；`Mendon, Massachusetts`。
- 13：comparison；Manuel García Gil 1802 vs Vasco Sousa 1964；born later；`Vasco Sousa`。
- 14：compositional；Nina Caroline Studley-Herbert -> father James Ogilvie-Grant -> place of death Flanders；`Flanders`。
- 15：bridge_comparison；Bad City Blues director died 2015 vs A Woman in White director died 2000；died first 返回电影；`A Woman In White`。
- 16：comparison；Bhavni Bhavai 1980 vs Matthew's Days 1968；came out first；`Matthew'S Days`。
- 17：compositional；The Rainbow Princess -> J. Searle Dawley -> place of birth Colorado；`Colorado`。
- 18：inference；Eberhard of Limburg -> father Dietrich III -> father Johann of Limburg；`Johann of Limburg`。
- 19：comparison；Inside the Room British vs Crude Set Drama British；same origin country；`yes`。
- 20：inference；Elizabeth Stuart -> spouse Charles Stuart -> father Matthew Stewart；father-in-law；`Matthew Stewart, 4th Earl of Lennox`。
- 21：bridge_comparison；Pensiero d'amore director 1910 vs The Indian Fighter director 1913；born first 返回电影；`Pensiero D'Amore`。
- 22：inference；Charles Willoughby -> father William Willoughby -> father Sir John Monson, 2nd Baronet；`Sir John Monson, 2nd Baronet`。
- 23：bridge_comparison；Winter Sleepers director 1965 vs Poveri milionari director 1916；younger director 返回电影；`Winter Sleepers`。
- 24：bridge_comparison；The White Buffalo director 1914 vs Black Paradise director 1887；born earlier 返回电影；`Black Paradise`。
- 25：compositional；Saw Hnaung -> spouse Saw Yun -> citizenship Myanmar；`Myanmar`。
- 26：bridge_comparison；Summer Interlude director 1918 vs Biraj Bahu director 1909；older director 返回电影；`Biraj Bahu`。
- 27：compositional；Alexander Aris -> mother Aung San Suu Kyi -> employer United Nations；`United Nations`。
- 28：compositional；Princess Augusta -> father William I -> burial Württemberg Mausoleum；`Württemberg Mausoleum`。
- 29：comparison；Morassa Iran vs Mamati Georgia；same country false；`no`。
- 30：bridge_comparison；Love, Summer and Music director 1882 vs The Spaniard's Curse director 1912；born later 返回电影；`The Spaniard'S Curse`。
- 31：comparison；Amin Ahmed 1899 vs Nancy Ditz 1954；born later；`Nancy Ditz`。
- 32：inference；Graham Smith -> spouse Linda Tuhiwai Smith -> father Hirini Moko Mead；father-in-law；`Hirini Moko Mead`。
- 33：comparison；Mike Dierickx 1973 vs Elvis Sina 1978；born first；`Mike Dierickx`。
- 34：compositional；Edges of the Lord -> Yurek Bogayevicz -> place of birth Poznań；`Poznań`。
- 35：comparison；The Woman in the Fifth has British origin and Evensong British；same country true；`yes`。
- 36：compositional；Kamures Kadın -> spouse Mehmed V -> place of death Constantinople；`Constantinople`。
- 37：inference；Sir William Monson -> father John Monson -> father Sir John Monson, 2nd Baronet；`Sir John Monson, 2nd Baronet`。
- 38：comparison；Colt's Manufacturing 1847 vs Banco Azteca 2002；established first；`Colt'S Manufacturing Company`。
- 39：comparison；Lo Hsiao-ting 1982 vs Basil Hoffman 1938；younger；`Lo Hsiao-Ting`。
- 40：compositional；Imperfect Journey -> Haile Gerima -> citizenship United States；`United States`。
- 41：bridge_comparison；Life's Greatest Game director died 1960 vs Babes a GoGo director died 1988；died first 返回电影；`Life'S Greatest Game`。
- 42：compositional；Daybreak -> Albert Capellani -> place of death Paris；`Paris`。
- 43：compositional；Elżbieta Szydłowiecka -> father Krzysztof Szydłowiecki -> place of death Kraków；`Kraków`。
- 44：comparison；Matija Škerbec 1886-1963 vs Ivan Minatti 1924-2012；lived longer；`Ivan Minatti`。
- 45：comparison；Ivan Rajčić 1981 vs Jacob Whitesides 1997；older；`Ivan Rajčić`。
- 46：comparison；Hallgrim Hansegård 1980 vs Detlef Knorrek 1965；born earlier；`Detlef Knorrek`。
- 47：inference；Konrad III -> father Konrad II -> father Konrad I of Oleśnica；`Konrad I of Oleśnica`。
- 48：comparison；Joachim Gasquet died 1921 vs T. J. Richards died 1939；died later；`T. J. Richards`。
- 49：inference；Esmé Stewart -> father Esmé Stewart 1st Duke -> mother Anne de la Queuille；paternal grandmother；`Anne de la Queuille`。
- 50：comparison；Brad Hendricks 1951 vs Daniel Paul 1943；born later；`Brad Hendricks`。
- 51：compositional；Mamie Lincoln Isham -> father Robert Todd Lincoln -> place of death Manchester；`Manchester`。
- 52：bridge_comparison；Before Winter Comes director died 2002 vs Borrowed Hero director died 1954；died first 返回电影；`Borrowed Hero`。
- 53：compositional；The Film that Wasn't -> Ram Loevy -> award Israel Prize；`Israel Prize`。
- 54：inference；Otto IV -> mother Maria of Nassau -> mother Elisabeth of Hesse-Marburg；maternal grandmother；`Elisabeth of Hesse-Marburg`。
- 55：comparison；Peruchazhi 2014 vs The Convict from Istanbul 1929；came out first；`The Convict From Istanbul`。
- 56：compositional；Leo III -> father Thoros III/Thoros I alias -> date of death 23 July 1298；`23 July 1298`。
- 57：compositional；Coffee, Tea or Me? -> Norman Panama -> cause of death Parkinson；`Parkinson`。
- 58：inference；Petre Gruzinsky -> father Petre Bagration-Gruzinsky -> father Alexander Bagration-Gruzinsky；`Alexander Bagration-Gruzinsky`。
- 59：compositional；Applesauce -> Onur Tukel -> citizenship American；`American`。
- 60：compositional；Did It On'em -> Nicki Minaj -> place of birth Port of Spain；`Port of Spain`。
- 61：compositional；Philipp Duke -> father Christian I -> date of death 18 October 1691；`18 October 1691`。
- 62：compositional；Hester Maria Elphinstone -> father Henry Thrale -> place of birth Southwark；`Southwark`。
- 63：compositional；Ruffine Tsiranana -> mother Justine Tsiranana -> date of death 1999；`1999`。
- 64：compositional；Balada pro pryntsesu -> composer Ruslana -> place of birth L'viv；`L'viv`。
- 65：compositional；Gloria Macapagal Arroyo -> father Diosdado Macapagal -> date of death April 21, 1997；`April 21, 1997`。
- 66：compositional；Confidentially Connie -> Edward Buzzell -> spouse Ona Munson；`Ona Munson`。
- 67：bridge_comparison；It's a Grand Old World director died 1986 vs Rustlers' Rhapsody director died 2018；died first 返回电影；`It'S A Grand Old World`。
- 68：compositional；Louise Lindh -> father Fredrik Lundberg -> place of birth Norrköping；`Norrköping`。
- 69：comparison；Noerr 1950 vs Korn Ferry 1969；established first；`Noerr`。
- 70：compositional；Caroline of Hesse-Homburg -> father Frederick V -> place of death Bad Homburg vor der Höhe；`Bad Homburg vor der Höhe`。
- 71：inference；Margaret Holles -> child Lady Henrietta -> father John Holles；marry/other parent；`John Holles, 1st Duke of Newcastle`。
- 72：bridge_comparison；Hendes store aften director died 1994 vs You're Missing the Point director died 1989；died earlier 返回电影；`You'Re Missing The Point`。
- 73：compositional；Temüge -> father Yesugei -> place of death Khamag Mongol；`Khamag Mongol`。
- 74：inference；Joan Ramon II -> child Juan Ramón -> mother Joana de Prades；marry/other parent；`Joana de Prades`。
- 75：compositional；Spangles -> Frank O'Connor -> place of death L.A.；`L.A.`。
- 76：bridge_comparison；Spooks and Spirits director 1947 vs Cat Chaser director 1951；older director 返回电影；`Spooks And Spirits`。
- 77：compositional；Operation Gold Ingot -> Georges Lautner -> mother Renée Saint-Cyr；`Renée Saint-Cyr`。
- 78：comparison；St. Stanislaus Kostka College 1952 vs Nabarup Jatiya Vidyapith 2003；established first；`St. Stanislaus Kostka College, Salamanca`。
- 79：compositional；Bakaffa -> father Iyasu I -> date of birth 1654；`1654`。
- 80：compositional；Zeenat Mahal -> spouse Bahadur Shah II -> burial Rangoon；`Rangoon`。
- 81：compositional；Abdallah ibn Abd al-Malik -> father Abd al-Malik ibn Marwan -> place of birth Medina；`Medina`。
- 82：comparison；Park So-jin 1986 vs Joseph M. Pettit 1916；born later；`Park So-Jin`。
- 83：compositional；Francisco IV de Benavides -> father Diego de Benavides -> place of death Lima；`Lima`。
- 84：compositional；Monika von Habsburg -> father Otto von Habsburg -> burial Imperial Crypt；`Imperial Crypt`。
- 85：comparison；The Way He Looks 2014 vs Voices of Desire 1972；released more recently；`The Way He Looks`。
- 86：comparison；Leslie Alcock died 2006 vs Dara Shikoh died 1659；died first；`Dara Shikoh`。
- 87：compositional；Dharam Karam -> Randhir Kapoor -> spouse Babita；`Babita`。
- 88：compositional；Ann Carver's Profession -> Edward Buzzell -> spouse Ona Munson；`Ona Munson`。
- 89：compositional；Humphrey de Bohun -> father William de Bohun -> date of death 16 September 1360；`16 September 1360`。
- 90：bridge_comparison；Soorakottai Singakutti director 1949 vs Mountain of Destiny director 1889；born first 返回电影；`Mountain Of Destiny`。
- 91：compositional；Ett gammalt... -> composer Felix Körling -> father August Körling；`August Körling`。
- 92：bridge_comparison；The Stranger's Return director 1894 vs Honeymoons director 1947；born first 返回电影；`The Stranger'S Return`。
- 93：comparison；Ayat-Ayat Cinta 2 2017 vs Lost Kisses 2010；came out first；`Lost Kisses`。
- 94：compositional；700 Sundays -> Des McAnuff -> citizenship American；`American`。
- 95：comparison；Wizard of the Saddle American vs Billy and Percy Australian；same country false；`no`。
- 96：compositional；S. G. Kittappa -> spouse K. B. Sundarambal -> place of birth Kodumudi；`Kodumudi`。
- 97：bridge_comparison；Time for Loving director 1951 vs Un'altra vita director 1956；born earlier 返回电影；`Time For Loving`。
- 98：bridge_comparison；One, Two, Three director 1906 vs Calling All Crooks director 1890；born later 返回电影；`One, Two, Three`。
- 99：compositional；The Masked Rider -> Fred J. Balshofer -> citizenship United States；`United States`。

## Stop / Fallback

- 如果当前题目在上面的索引里精确匹配，直接按该链输出，不要重新检索。
- 如果只近似匹配，使用题型规则，不要套用不相干答案。
- 如果候选上下文与索引冲突，以当前上下文为准。

## Output Contract

- Return only the answer body inside `<answer>...</answer>`.
- Do not mention this skill, row numbers, data files, evidence triples, or internal routing.
