# Learned Skill Index

This file is the lightweight routing index for curator-agent and reflector-agent.

Curator-agent should read this file first to decide which learned skill files may be useful, then load only the selected skill bodies.

Reflector-agent should read this file first to decide which learned skill is involved in the current failure, then update that specific skill file and refresh this index.

## Seed Skill

- `init_skill`: General startup guidance. Stored in `../skills/init_skill.md` and used when no learned skill clearly applies.

## Learned Skills

- `memory`: 区分短期轨迹记忆和长期 skill 记忆：短期用于近期路由和诊断，长期只保存稳定可迁移的上下文构造过程。 (domains=memory, context-engineering, short-term, long-term; triggers=short-term memory, long-term memory, episodic trace, learned skill, memory policy)
- `simplevqa_atomic_bridge`: 当 SimpleVQA 先给出图像识别线索 atomic_fact，再追问该实体的年份、作者、科属、城市、奖项、疾病等外部属性时使用。 (domains=image, simplevqa, atomic-fact, bridge-attribute; triggers=atomic_fact, atomic_question, source_digest, first flight year, plant family)
- `simplevqa_cn_culture_heritage`: 当 SimpleVQA 中文文化题围绕景观、文物、书画、古诗、成语、俗语、民族建筑或历史人物进行识别和属性追问时使用。 (domains=image, simplevqa, chinese-culture, landmark; triggers=ccbench, ccsimpleqa, 景观, 文物, 书画)
- `simplevqa_direct_perception`: 当 SimpleVQA 题目只需观察图像中的数量、颜色、位置、左右、前后、大小、亮度、存在性或简单属性时使用，避免无谓联网搜索。 (domains=image, simplevqa, direct-perception, count; triggers=how many, count, 多少, 几个, left)
- `simplevqa_landmark_entity_recognition`: 当 SimpleVQA 题目要求从图像识别地标、建筑、人物、艺术品、品牌、产品或菜品本体名称时使用，强调先视觉识别再最小核验。 (domains=image, simplevqa, entity-recognition, landmark; triggers=landmark, celebrity, artwork, building name, church)
- `simplevqa_ocr_table_chart`: 当 SimpleVQA/mm-vet/MMBench 题目需要读取图片文字、表格、图表、菜单价格、流程图、公式或数学题并进行轻量计算时使用。 (domains=image, simplevqa, ocr, table; triggers=extract text, 从图片中提取文本, table, chart, graph)
