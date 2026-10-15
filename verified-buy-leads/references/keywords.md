# 默认执行范围说明

默认 link-first：本文件的词库、场景、语言及搜索分支继续尽量覆盖，但“讨论入口反查”默认先收录真实返回的群组/视频/帖子链接，实际展开评论/回复属于可选后续核验。未读取评论须明示，不算评论内容已覆盖，也不阻止链接收集范围完成。coverage_obligations 增加 scope=link-discovery/content-verification；默认只以 link-discovery 计算本轮完成度，可选核验欠账另计，不混用分母。用户要求核验时才执行下面涉及原帖/评论读取的步骤。

# 从产品词到可追踪的检索覆盖

目标是系统减少漏搜，不只生成几句英文求购词。先展开完整的适用词库与场景清单，再分批执行；预算限制执行批次，不限制记录待查分支。所有规则跨产品适用，不预设 LED、固定国家或语言数量。

## 一、建立产品理解与词族

结合用户描述及实际查阅的行业/买方资料建立 product_profile：是什么、不是什么、子品类、供货方式、使用者、解决的问题和局限。对新术语保留来源链接和解释；未经核实标 proposed，不当已确认同义词。只有产品歧义影响检索才询问。

12 维逐项记录 terms、适用性及缺口，不强行凑词：

1. 标准品名、通俗名、同义词、行业缩写、常见有依据的拼写变体。
2. 子品类、规格、型号、材质、工艺、应用参数、单位与单位表达差异。
3. 目标市场的当地叫法、主要语言、常见混语和有依据的音译。
4. 买方意图：求供应商、询价、补货、批量定制、OEM/ODM、替换升级；租赁/维修/安装独立分类。
5. 使用组织、细分买家、终端/渠道角色，区分个人兴趣与商业采购。
6. 现有方案、替代品、旧设备及其俗称；不提目标产品的需求也可能出现在这些讨论中。
7. 使用者痛点、故障、限制及后果；保留“用户怎么说”，不只堆技术名词。
8. 求推荐、求帮助、比较、询问哪里买、再次采购等口语句式。
9. 具体使用场景、任务、地点、项目阶段与当地场景叫法。
10. 新建/扩张/改造/更换等触发事件，只作信号，不能推定采购。
11. 安装商、服务商、代理商及渠道角色；其明确采购与其广告分别判断。
12. 参与使用/决策/采购的职位、团队和社区名称。

每个维度写 applicability=applicable/not-applicable/needs-research；不适用要写理由。每个场景说明买家角色、使用任务、痛点、可用词族、替代方案、限制。不要以统一“十个客户场景/七种语言”代替适用性检查。

## 二、市场与语言覆盖

有目标国家时，对每个国家记录相关主要市场语言及买家实际使用语言，不默认英语足够；不适用的语言说明依据。产品词、痛点词和采购口语分别本地化，不能只逐字翻译品名。

未指定市场时先建立候选市场清单和选择依据，标为暂定范围；分批探索后补充语言和场景，报告未覆盖市场。不能把少数探索国家称为全球覆盖。用户明确指定国家/语言/排除项优先。

## 三、两条搜索路线都要规划

- **需求词直搜**：产品/当地词 + 买方意图 + 场景；另查不含场景、别名/型号以及不提产品的痛点/替换表达，避免过多限定导致漏搜。
- **讨论入口反查**：产品评测、安装教程、替代方案讨论、相关群组/帖子/视频/行业论坛 → 实际展开可访问评论及回复 → 识别具体需求作者。不能只在搜索结果里查“need 产品”，也不能把入口本身当客户。

每个适用场景都规划明确采购、求解/推荐、痛点/替换分支；每个词族安排不绑定某个场景的查询。按 supply 模式识别租赁/服务需求，不把这些流量当硬件采购。没有需求证据的项目新闻只单列信号。

## 四、建矩阵与队列，避免静默漏项

keyword_plan 保留 explicit、pain_points、triggers、channel_partners、coverage；增加 product_profile、product_families、local_terms、query_cells、scenarios、market_languages、dimension_audit、coverage_obligations、expansion_queue。

- dimension_audit：12 维的 applicability、terms、evidence_urls、gap、reason。
- coverage_obligations：从词库产生的应查分支，含 obligation_id、product_family、segment、market、language、platform、entry_type（direct-demand/discussion-comments）、intent、applicability、reason、query_ids。多个简单查询可共同覆盖一个分支，不要求一条长查询塞下全部维度。
- query_cells：query_id、obligation_ids、product_topic、product_family、market、language、platform、segment、intent、entry_type、query、status、reason、resume_cursor、last_run_at、next_check_at。
- expansion_queue：新别名/场景/语言/讨论入口、来源 URL、parent_query_id、待验证假设和状态。验证后补词库、生成查询，不能只在正文提一下就丢失。
- pain_points：segment/pain/queries/solution/limitations，不保证产品一定适合。

规划“词族 × 意图 × 场景 × 市场语言 × 平台 × 入口类型”的适用组合。先标不适用理由，再生成可执行批次；不盲目制造无意义的无限笛卡尔积。先广度扫描不同分支，再对高相关结果深挖；低产分支可降频，但仍须入队且保留欠账，不得只跑高产组合就称覆盖完成。

## 五、执行、翻页与滚动扩词

执行前按 channels.md 检查真实工具。优先社媒连接器/授权站内浏览，网页 site: 查询只作补充发现，不代表已读取评论。

对支持分页、滚动或评论排序的工具，继续读取可访问的后续页/回复；可切换 newest/relevant 等实际支持的排序检查差异。记录 pages_read、comments_read、sort_order、tool_limit、stop_reason、resume_cursor，不能默认第一页就是全部。遇预算、权限、工具上限或限流时保留续查位置，status=partial/blocked，不能 complete。不可序列化的浏览器游标可记录入口 URL、排序、已读末项 ID 和恢复说明，不保存登录令牌。

从真实结果补充客户自己的措辞、当地俗称、新场景和替代品。连续两个成功零合格查询触发换词、放宽/拆分限定、换语言/平台；不能直接把该分支判不适用。访问失败不是零命中，降频要有原因和复查日期。

## 六、覆盖审计和停止条件

query status：planned/running/complete/partial/blocked/deferred/not-applicable。complete 指完成本次约定窗口和可用工具范围内查询，不表示平台全部内容可见。not-applicable 需理由；deferred 仍是未完成，不算已查。channel_runs 的 ok/empty 只表示一次操作成功；若分页/评论未读完，对应 query 仍 partial，不得提前推进其完整成功窗口。

一个 obligation 只有相关 query 都 complete（或有明确依据不适用）才算已覆盖；只完成需求直搜不能替代评论分支。全部待查、失败重试与扩词任务写入数据目录 keyword_plan.json，下轮先补未完成窗口，不能被全局时间水位跳过。

结束前检查：遗漏的子品类？只搜标准名？只搜英文？只搜 need/buy？漏了替代品痛点？漏了不含产品名的场景？只看主帖/视频没读评论回复？只看第一页？某平台受限后被静默跳过？新发现词是否入队？排除付费/B2B 后是否仍有独立原证据？逐项写发现及待补任务。

报告分别给出：12 维准备状态、适用 obligations 总数、已完成/待执行/部分/受限分支数、实际原帖与评论读取量、过滤原因及范围。覆盖率以适用 obligations 为分母，只把完全完成的算分子；解释其仅代表约定矩阵，不代表全网召回率。无依据的候选未展开不能藏在分母之外，报告暂定范围及新增欠账。

默认 coverage-first：45 分钟/20 条核验是单批预算，不是产品词扩展上限，也不是找满 20 条就完成。达到预算保存队列和续查位置，报告 partial；下一次从欠账继续，不自行新建定时任务。结束可因约定矩阵完成、用户停止或预算/访问限制；后两种明确未完成，不能声称“一网打尽”。
