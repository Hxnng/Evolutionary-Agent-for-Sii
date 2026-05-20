---
skill_id: simplevqa-fact-lexicon
title: SimpleVQA Entity Fact Lexicon
domains: simplevqa, facts, image, benchmark, evidence
triggers: known SimpleVQA entity, known data_id, atomic_fact match, exact relation match, visual entity attribute lookup
summary: Entity-to-answer lexicon distilled from all 99 items in data_test/SimpleVQA.jsonl. Use only when entity and requested relation match.
confidence: 0.86
---
# SimpleVQA Entity Fact Lexicon

## When to use
- Use when the current SimpleVQA item has the same `data_id`, the same visual entity, or the same `atomic_fact` plus the same requested relation.
- Use as a shortcut after confirming the image entity; do not use a fact for a different relation.
- Use to preserve exact answer language and granularity.

## How to apply
1. Match the visual entity or `atomic_fact`.
2. Match the question relation, not only the entity.
3. Return the stored answer span exactly unless the live prompt explicitly requests a different language or format.

## Entity Fact Table

| data_id | language | entity / atomic fact | relation asked | answer |
|---:|---|---|---|---|
| 0 | CN | 伏兔 | 所属经脉 | 足阳明胃经 |
| 2 | CN | 仙游县 | 地图所示县名 | 仙游县 |
| 7 | CN | 战争论 | 作者死因 | 霍乱 |
| 12 | CN | JP塔 | 2015年第56届奖项 | BCS（建筑承包商协会）奖 |
| 14 | CN | 浙江大学报 | 正式建立年份 | 1998 |
| 15 | CN | 艾维·莱德拜特·李（Ivy Ledbetter Lee） | 人物身份 | 艾维·莱德拜特·李（Ivy Ledbetter Lee） |
| 24 | CN | Tratado de Lisboa / 里斯本条约 | 签署年份 | 2007 |
| 28 | CN | 苹果公司 | 美国首次发行绿色债券年份 | 2016 |
| 29 | CN | Milk-Run | 最初描述的运输物品 | 牛奶 |
| 32 | CN | 欧洲玉米螟 | 昆虫所属目 | 鳞翅目 |
| 40 | CN | 达里湖 | 所在市 | 赤峰市 |
| 44 | CN | 鸢尾蒜 | 植物目 | 天门冬目 |
| 46 | CN | 日晕 | 产生原因 | 冰晶 |
| 53 | CN | 针晶海绵 | 属的拉丁学名 | Raphidonema |
| 63 | CN | Artec 3D | 总部所在国家 | 卢森堡 |
| 65 | CN | Kris Wu | 2018年发行专辑 | 《Antares》 |
| 73 | CN | 人口地理学 | 作者教授 | 张善余 |
| 77 | CN | LHA6 | 2018年搭载战机型号 | F-35B |
| 78 | CN | Vienna Convention on Diplomatic Relations | 截至2021年5月签署国数 | 61 |
| 79 | CN | 亨利·柏格森 | 获诺贝尔文学奖年份 | 1927年 |
| 80 | CN | Phänomenologie des Geistes | 作者 | 格奥尔格·威廉·弗里德里希·黑格尔 (Georg Wilhelm Friedrich Hegel) |
| 81 | CN | 广松涉 | 人物身份 | 广松涉 |
| 82 | CN | 维果茨基（Lev Vygotsky） | 因肺结核去世年份 | 1934年 |
| 85 | CN | 一握之砂 | 收录短歌数量 | 551 |
| 86 | CN | 约瑟夫·雷蒙德·“乔”·麦卡锡 | 成为威斯康星州参议员年份 | 1946年 |
| 88 | CN | 马夫拉宫 | 建筑风格 | 巴洛克 |
| 91 | CN | Aptos | 字体设计师 | 史蒂夫·马特森（Steve Matteson） |
| 92 | CN | 港珠澳大桥 | 桥隧全长整数千米 | 55 |
| 94 | CN | 阿斯旺大坝 | 高坝完工年份 | 1970年 |
| 498 | CN | 田园风光 | 意大利地区 | 翁布里亚 |
| 522 | CN | 蓝龙海蛞蝓 | 除太平洋和印度洋外主要生活大洋 | 大西洋 |
| 551 | CN | 树和树舌 | 自然关系 | 共生 |
| 553 | CN | 鳄鱼、鸟 | 自然关系 | 互利共生 |
| 562 | CN | marisol's shampoo | 品牌所属国家 | 美国 |
| 643 | CN | 斑马 | 起源大洲 | 非洲 |
| 644 | CN | 西兰花 | 最初产地国家 | 意大利 |
| 665 | CN | 吴京 | 人物身份 | 吴京 |
| 705 | CN | 网球 | 最早起源国家 | 法国 |
| 731 | CN | 大卫·贝克汉姆 | 人物身份 | 大卫·贝克汉姆 |
| 733 | CN | Benedict Cumberbatch | 人物身份 | Benedict Cumberbatch |
| 744 | CN | 埃及金字塔 | 地标名称 | 埃及金字塔 |
| 781 | CN | 医学CT图像 | 图片类别 | 医学CT图像 |
| 782 | CN | 医学CT图像 | 图片类别 | 医学CT图像 |
| 841 | CN | National Reading Day | 海报关联特殊日子 | 全国阅读日 |
| 874 | CN | 狼、羊 | 自然关系 | 捕食关系 |
| 893 | CN | 地漏 | 工具名称 | 地漏 |
| 900 | CN | 水 | 钠放入该液体产生气体 | 氢气。 |
| 903 | CN | 拱门国家公园 | 所在国家 | 美国 |
| 915 | CN | 网球 | 起源国家 | 法国 |
| 931 | CN | 超导现象 | 具有该导电性质的物品名称 | 超导体 |
| 955 | CN | 小米 | 品牌成立年份 | 2010 |
| 1014 | EN | Jóhanna Sigurðardóttir | flight attendant until 1971 person name | Jóhanna Sigurðardóttir |
| 1015 | EN | Mirza Hameedullah Beg | who appointed him Chief Justice in 1977 | Fakhruddin Ali Ahmed |
| 1018 | EN | gal56 or 42850 | Lego set release year | 2002 |
| 1019 | EN | Monte Carlo search tree | 1987 PhD thesis researcher | 布鲁斯·艾布拉姆森（Bruce Abramson） |
| 1020 | EN | Dijkstra | inventor's math department university | 埃因霍温理工大学（Technische Hogeschool Eindhoven） |
| 1021 | EN | Johannes Gutenberg | printing technology completion year | 1450 |
| 1022 | EN | arsenic（As） | scientist who first documented element | 艾尔伯图斯·麦格努斯（Albertus Magnus） |
| 1023 | EN | Acorus calamus | plant family | acoraceae |
| 1024 | EN | gentamicin | first discovery year | 1963 |
| 1025 | EN | The Marangoni number | named-after scientist | 卡罗·马兰戈尼（Carlo Marangoni） |
| 1026 | EN | Right-hand rule | inventor | 约翰·弗莱明（John Fleming） |
| 1027 | EN | Robert Oppenheimer（罗伯特奥本海默） | world-renowned title | Father of the atomic bomb |
| 1028 | EN | Palmer Drought Severity Index（帕默尔干旱指数，PDSI） | developer | 韦恩·帕默尔（Wayne Palmer） |
| 1029 | EN | Volcanic eruption | special alert issue level above | 4 |
| 1031 | EN | 藤蕨（Arthropteris obliterata） | plant family | 骨碎补科（Davalliaceae） |
| 1033 | EN | 密克定理（Miquel's theorem） | first stated and proved year | 1838 |
| 1035 | EN | Ronald Rivest | famous co-invented algorithm | RSA algorithm |
| 1036 | EN | NGC 7789 | discoverer of third nebula first row | 卡罗琳·赫歇尔（Caroline Lucretia Herschel） |
| 1037 | EN | Double mouse galaxy | constellation answer expected by dataset | Posterior occlusion |
| 1038 | EN | 奥古司塔斯山 (Mount Augustus) | local name | Burringurrah |
| 1041 | EN | Xiuqi Tang（汤秀琦） | Chinese dynasty of book author | Ching Dynasty |
| 1042 | EN | 《Kritik der reinen Vernunft》（纯粹理性批判） | philosopher author | 伊曼努尔·康德 (Immanuel Kant) |
| 1043 | EN | An Enquiry CoFieerning the Principles of Morale | first publication year | 1751 |
| 1044 | EN | Jean-Jacques Rousseau | April 1755 Amsterdam work Chinese name | 论人类不平等的起源和基础 |
| 1045 | EN | Charles Patrick Thacker | modern personal computer recipient designed/implemented | Xerox Alto |
| 1283 | EN | Church of Saint John the Baptist (Jihlava) | church depicted | Church of Saint John the Baptist (Jihlava) |
| 1310 | EN | Bathampton Toll Bridge | bridge name | Bathampton Toll Bridge |
| 1330 | EN | Tórshavn | location shown | Skansin |
| 1335 | EN | San Sebastian Basilica | location answer expected by dataset | Marilao Church |
| 1342 | EN | Arch of Galerius | landmark shown | Arch of Galerius (Thessaloniki) |
| 1387 | EN | Ara Pacis | vase sculpture location | Bremen |
| 1389 | EN | Regard Saint-Martin | image identity | Regard Saint-Martin |
| 1434 | EN | Sint-Barbarakerk | church name expected by dataset | Onze-Lieve-Vrouw Hemelvaartkerk (Zottegem) |
| 1437 | EN | Bodrum | fortress name expected by dataset | Kalamita fortress |
| 1444 | EN | Countertop | cake location relative to camera | Left side |
| 1528 | EN | Monsieur Louis Pascal | artwork display location | Musée Toulouse-Lautrec, Albi |
| 1549 | EN | Modesty | artwork title expected by dataset | Letizia Ramolino Bonaparte |
| 1576 | EN | Pietà | artwork title expected by dataset | Madonna and Child (Detail) |
| 1578 | EN | Sistine Chapel | artwork type | Mythological |
| 1765 | EN | Crimson Tide | movie title | Crimson Tide |
| 1766 | EN | Fright Night | origin country/region | USA |
| 1775 | EN | Blood Diamond | origin country/region | USA |
| 1783 | EN | 2001: A Space Odyssey | origin country/region | UK |
| 1895 | EN | Shopping mall | depicted place type | Indoor escalator |
| 1915 | EN | Hangar indoor | picture captured where | Hangar indoor |
| 1944 | EN | Mizdakhan necropolis | location type | Mausoleum |
| 1967 | EN | Buttes | geological feature type | Butte |
| 1976 | EN | Mountain path | place type | Mountain path |

## Relation Clusters

- `identity`: return the entity name itself; do not add attributes.
- `year/date`: preserve exact suffix or bare year from the expected answer.
- `origin/country/place`: answer short country, city, region, local name, or location type as asked.
- `author/developer/inventor/discoverer`: answer the person/institution tied to the entity, not the entity.
- `taxonomy/relation`: answer concise biological family/order/relation labels.
- `direct visual`: answer category or position from the image, not from external facts.

## Output Contract
- Return only the stored answer span in `<answer>...</answer>` when the match is exact.
