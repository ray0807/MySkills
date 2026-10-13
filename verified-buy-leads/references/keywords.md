# 关键词分析与检索顺序

首次运行根据用户产品生成完整关键词计划，保存到配置的 `keyword_plan`；之后每次运行沿用，并把新发现的有效说法补充进去。生成后直接开始检索，不等用户确认；用户提出修改时再调整。

`keyword_plan` 结构：
- `explicit`：按语言列出明确需求关键词，例如 `{"en": [...], "es": [...]}`。
- `pain_points`：每项为 `{"segment": "church", "pain": "投影太暗看不清歌词", "queries": ["projector too dim church"], "solution": "LED 屏高亮度，开灯也清晰"}`。
- `triggers`：触发事件关键词，用于主动开发名单。
- `channel_partners`：经销商、安装商等渠道客户关键词。
- `coverage`：下方 12 个维度各自的词条数；某维度为空时写明原因。

## 关键词必须覆盖的维度

关键词要全。生成计划后逐项自查以下维度，每个维度都要有词条；确实不适用的写明原因，不能静默跳过。

1. **产品名称**：标准名、别称、缩写、行业叫法、常见拼写错误（LED screen / LED display / LED wall / video wall / jumbotron / LED billboard）。
2. **规格和型号词**：买家会写进需求里的参数和品类（P2.5、indoor / outdoor、rental、transparent、flexible、COB）。
3. **目标市场语言**：每个目标国家的主要语言都要翻译产品名和采购表达，用当地真实说法（pantalla LED、painel de LED、écran LED、شاشة LED、LED-Wand）。没有指定国家时至少覆盖英语、西班牙语、葡萄牙语、法语、阿拉伯语、俄语、德语。
4. **采购表达**：RFQ、request for quotation、looking for supplier / manufacturer、need quote、wholesale、bulk order、importer、distributor wanted、OEM、tender、ISO（in search of）、WTB（want to buy）；以及各语言对应说法（cotización、compramos、appel d'offres、مناقصة）。
5. **终端客户类型**：尽量穷举会真正使用产品的场所和组织，一般不少于 10 类。例如 LED 屏：教堂、酒吧、夜店、餐厅、健身房、零售店、商场、酒店、学校、体育场馆、会议中心、展会搭建、租赁公司、汽车经销店、政府广场。
6. **被替代方案和竞品**：客户现在在用什么（projector、TV wall、LCD video wall、poster、lightbox、chalkboard menu）。
7. **痛点**：每类客户都要列出痛点，覆盖亮度与可视性、内容更新、维护成本、寿命、能耗、吸引客流、尺寸与安装限制等方面。
8. **求推荐与比较句式**："best X for Y"、"X vs Y"、"recommend"、"which X should we buy"、"alternatives to X"、"upgrade our X"。
9. **使用场景说法**：客户自己的叫法，不一定包含产品名（digital menu board、schedule display、storefront screen、scoreboard、stage backdrop）。
10. **触发事件**：开业、新店、翻新、扩建、搬迁、新建礼堂或场馆、举办大型活动（grand opening、renovation、new location、building a new sanctuary）。
11. **渠道与中间商**：经销商、安装商、系统集成商、标识广告公司、活动租赁公司、进口商（AV integrator、sign company、event rental、distributor）。
12. **决策人职位**：procurement manager、purchasing、facilities manager、AV manager、worship / tech director、store operations。

计划中的每条痛点关键词都对应一句"痛点 → 产品解决方案"，写入 `solution`，后续用作线索备注和跟进话术。

## 检索顺序

1. 按 segment 逐个处理；每个 segment 先跑明确需求，再跑痛点。全部 segment 完成后，再跑触发事件和渠道客户。
2. 一个关键词处理完（打开原文、核验、记录 channel_runs）再换下一个，不一次性堆叠所有词。
3. 日常运行中，每个关键词只看上次运行以来的新内容。预算不足以跑完全部关键词时，优先跑最久没搜过的关键词（依据 `channel_runs.jsonl`），并在汇报中列出本次未覆盖的关键词。
4. 某关键词连续无有效结果时，记录下来并换同 segment 的其他说法，不自动扩大到其他产品。

## 示例：LED 显示屏（节选）

以下只是示例，实际计划按用户产品生成，并覆盖上面全部维度。

| segment | 明确需求 | 痛点关键词 | 痛点 → LED 解决方案 |
| --- | --- | --- | --- |
| 教堂 church | "LED wall for church quote"、"church LED screen installation" | "projector too dim"、"can't see lyrics"、"replace church projector" | 投影在灯光下看不清歌词 → LED 屏高亮度，开灯也清晰 |
| 酒吧 bar | "LED video wall for bar" | "projector washed out"、"best display for bar" | 投影被环境光冲淡 → LED 屏亮度高，适合常开灯环境 |
| 餐厅 restaurant | "digital menu board supplier" | "menu board hard to update"、"digital menu board recommendation" | 纸质菜单更新麻烦 → LED 菜单屏可远程随时修改 |
| 健身房 gym | "gym LED display" | "class schedule display"、"how to show workout timer" | 课表和计时不直观 → LED 屏实时显示课表与计时 |
| 零售 retail | "storefront LED screen supplier" | "storefront screen recommendation"、"window display not noticeable" | 橱窗吸引力不足 → 户外高亮 LED 屏滚动展示促销 |
| 通用 | "LED screen RFQ"、"pantalla LED cotización" | "replace projector with LED"、"alternatives to projector" | 投影亮度、寿命和维护问题 → LED 替代投影 |
