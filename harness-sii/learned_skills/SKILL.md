# Learned Skill Index

This file is the lightweight routing index for curator-agent and reflector-agent.

Curator-agent should read this file first to decide which learned skill files may be useful, then load only the selected skill bodies.

Learned skills are grouped by dataset/task family to avoid cross-dataset contamination:
- `simplevqa/`: visual QA, OCR, image-entity and image-to-attribute skills.
- `2wiki/`: 2WikiMultihopQA evidence-graph and comparison skills.
- `general/`: cross-dataset memory and generic harness policies.
- `_memory/`: short-term episodic traces; not long-term skill memory.

Reflector-agent should read this file first to decide which learned skill is involved in the current failure, then update that specific skill file and refresh this index.

## Seed Skill

- `init_skill`: General startup guidance. Stored in `../skills/init_skill.md` and used when no learned skill clearly applies.

## Learned Skills By Dataset


### general

- `memory`: 区分短期轨迹记忆和长期 skill 记忆：短期用于近期路由和诊断，长期只保存稳定可迁移的上下文构造过程。 (domains=memory, context-engineering, short-term, long-term; triggers=short-term memory, long-term memory, episodic trace, learned skill, memory policy); file=`general/memory.md`

### simplevqa

- `simplevqa_atomic_bridge`: 当 SimpleVQA 先给出图像识别线索 atomic_fact，再追问该实体的年份、作者、科属、城市、奖项、疾病等外部属性时使用。 (domains=image, simplevqa, atomic-fact, bridge-attribute; triggers=atomic_fact, atomic_question, source_digest, first flight year, plant family); file=`simplevqa/simplevqa_atomic_bridge.md`
- `simplevqa_cn_culture_heritage`: 当 SimpleVQA 中文文化题围绕景观、文物、书画、古诗、成语、俗语、民族建筑或历史人物进行识别和属性追问时使用。 (domains=image, simplevqa, chinese-culture, landmark; triggers=ccbench, ccsimpleqa, 景观, 文物, 书画); file=`simplevqa/simplevqa_cn_culture_heritage.md`
- `simplevqa_direct_perception`: 当 SimpleVQA 题目只需观察图像中的数量、颜色、位置、左右、前后、大小、亮度、存在性或简单属性时使用，避免无谓联网搜索。 (domains=image, simplevqa, direct-perception, count; triggers=how many, count, 多少, 几个, left); file=`simplevqa/simplevqa_direct_perception.md`
- `simplevqa_landmark_entity_recognition`: 当 SimpleVQA 题目要求从图像识别地标、建筑、人物、艺术品、品牌、产品或菜品本体名称时使用，强调先视觉识别再最小核验。 (domains=image, simplevqa, entity-recognition, landmark; triggers=landmark, celebrity, artwork, building name, church); file=`simplevqa/simplevqa_landmark_entity_recognition.md`
- `simplevqa_ocr_table_chart`: 当 SimpleVQA/mm-vet/MMBench 题目需要读取图片文字、表格、图表、菜单价格、流程图、公式或数学题并进行轻量计算时使用。 (domains=image, simplevqa, ocr, table; triggers=extract text, 从图片中提取文本, table, chart, graph); file=`simplevqa/simplevqa_ocr_table_chart.md`

### 2wiki

- `twowiki_bridge_comparison`: 当 2Wiki 问题先从两个源实体桥接到人物/属性再比较时使用，避免返回中间实体而忘记映射回原始电影/书籍/作品。 (domains=2wiki, bridge-comparison, comparison, multihop; triggers=bridge_comparison, director of film, author of book, publication date, date of birth); file=`2wiki/twowiki_bridge_comparison.md`
- `twowiki_comparison`: 当 2Wiki 问题要求比较两个实体的日期、数字、寿命、国家/国籍或相等性时使用，先标准化值再返回题目要求的实体或 yes/no。 (domains=2wiki, comparison, date-normalization, evidence-graph; triggers=comparison, came out first, first, earlier, later); file=`2wiki/twowiki_comparison.md`
- `twowiki_multihop_chain`: 当 2Wiki 问题需要沿 evidence triples 从题目实体经过桥接实体到最终属性时使用，优先基于紧凑证据图推理而不是重新搜索。 (domains=2wiki, multihop, evidence-graph, compositional; triggers=2wikimultihopqa, context packet, compositional, inference, evidence triples); file=`2wiki/twowiki_multihop_chain.md`
- `twowiki_same_country_alias`: 当 2Wiki 问题判断两个实体是否同国/同国籍/同地点类别时使用，先把国籍形容词和国家名归一化再回答 yes/no。 (domains=2wiki, country-alias, equality, comparison; triggers=same country, same nationality, both from, country of citizenship, located in); file=`2wiki/twowiki_same_country_alias.md`
