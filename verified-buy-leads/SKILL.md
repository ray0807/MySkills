---
name: verified-buy-leads
description: 根据产品或关键词，优先搜索 Facebook、Instagram、YouTube 等免费社媒并保存候选链接，无需打开原帖或配置接口；区分有需求摘要的待核验线索、仅链接的发现入口与另行核验的可跟进客户。支持多语言场景覆盖和增量去重，排除 B2B 平台及付费线索。
---

# 通用客户需求查找与筛选

默认先收集相关链接，原帖核验可后续进行；纯公司名单、招聘/开业新闻不能充作采购需求。公开求购只证明曾表达意向，默认 public-unconfirmed；只有买方明确回复仍在采购才标 buyer-confirmed。允许零结果，不凑数。

## 默认 link-first：搜到就收录，不要求打开

用户输入产品/关键词后执行免费社媒定向搜索，保存真实返回的相关 URL。不调用原帖打开/抓取作为收录门槛，不因登录墙、评论打不开或身份未知丢弃链接；不要求配置 API、Key、第三方爬虫或登录账号才能开始。只有用户明确要求深度核验时，才进入下方可选核验流程并使用可用浏览能力。

- 有相关需求摘要或索引文本：candidate，待核验线索；逐字保存可见文本，不能称为已读原帖。无买家意图的广告/泛泛文字不能因有摘要就算需求候选，可作相关讨论入口或排除。
- 只有相关链接，没有需求文本：discovery，发现入口；群组、视频、账号可先保存，但不计作有需求的客户。不得虚构摘录填库。
- 用户要求核验且证据满足：使用原有 leads.json / leads.csv，不把候选复制过去自动升级。

候选与入口按 [data.md](references/data.md) 用 candidate_store.py 保存，默认交付 candidate-links.csv 与 discovery-links.csv，即使可跟进客户为零也要交付已发现链接。所有未读记录标 unverified，需求状态、身份和联系权限 unknown；发现时间与帖子时间分开，作者未知留空。B2B/付费排除规则保持。

## 默认渠道：免费社媒优先

先读 [channels.md](references/channels.md) 的工具能力检查和渠道准入。先盘点当前宿主真实可用的搜索能力和可选浏览权限，再选路线：已验证社媒连接器 → 已授权站内浏览 → 定向网页发现。仅有网页搜索时照常收录相关链接和摘要，明确未读原帖/评论，不强制补工具或账号。重点找 Facebook 公开群组/帖子/评论、YouTube 评论及作者需求、Instagram 帖子/Reels/评论，再按产品拓展 Reddit、行业论坛、LinkedIn、X、Threads、TikTok。群组、视频、博主或供应商账号可作为发现入口保存，不当作有需求的客户；发现具体需求帖/评论时优先保存其定位链接。

默认排除阿里国际站及类似 B2B 交易平台、采购线索库、付费聚合站，哪怕某一条 RFQ 可免费看、声称免费注册或存在公开联系方式也不作为客户交付。域名表见 [source-policy.json](assets/source-policy.json)，未列域名按实际类型识别，不能只查黑名单。旧配置、历史记录和查询计划不应继续调用被排除渠道；本规则优先于旧版渠道建议。没有结果时报告真实覆盖及限制，不回退 B2B 凑数。

免费社媒可能需要登录。默认查无需登录的公开内容；用户明确提供并授权使用已登录浏览器后，可只读其已有权限的内容。私密群未获成员权限、需要新注册/加群、评论无法读取时记 blocked/review，不申请加入、不创建账号。不能确认免费联系时不列可跟进；默认只保存发现链接，不为此提示用户配置账号；用户另行要求深入核验时才说明所需权限。当前任务不授权发送消息或评论。

## 从用户产品或关键词开始

接受产品名、型号、关键词或用途，例如“工业除湿机”“可堆叠托盘”“宠物胸背带”。已经给关键词就建立产品理解，不强迫重复填写产品名称。只有 screen/配件等歧义且无法确定产品时问一个澄清问题；完全没给主题时问“你想找什么产品或关键词的客户？”。定时运行直接使用已确认配置，缺主题才暂停提醒。

读取 [配置模板](assets/config.example.json)。明确是什么/不是什么、规格词族、能解决及不能保证解决的问题，以及 business_models（默认 product-sale，可配置 rental-service/installation-service/distribution）。未知认证、起订量、交期与价格不假定满足。其他缺项先记录假设，完整规划后分批探索，不给用户长问卷。

不同产品用独立数据目录/topic_id，换产品重建计划，不继承前一产品的去重记录、失败渠道或时间水位。附件 LED 示例、固定三个运行时间、国家和客户画像不作为通用默认值。

## 关键词与覆盖计划

读 [keywords.md](references/keywords.md) 和 [queries.md](references/queries.md)。保留 12 维检查，但按产品适用性填充，不强行编造十种客户或七种语言。默认 coverage-first：先展开产品别名/子品类、适用场景、买方口语、替代方案痛点及目标市场语言，按“词族 × 意图 × 场景 × 语言 × 平台 × 入口类型”建立覆盖清单和 query_cells。需求词直搜与讨论入口→评论/回复反查均须规划，不能只搜 need/buy 或只看第一页。按 keywords.md 建 keyword_plan.json，逐项记录不适用理由、分页停止原因、扩词队列和未查分支；简短展示后执行，不额外等待确认。

Facebook、Instagram、TikTok、YouTube、X、Threads、LinkedIn、Reddit/论坛都是候选。按产品、可用工具和预算轮换，不强求每轮跑全；未能读取的评论区不能称已覆盖。不假定存在 social.search/browser.search；按 [channels.md](references/channels.md) 和 [strategies.md](references/strategies.md) 使用实际工具。

## 增量检索与主动调整

运行 run_state.py start 读检查点。首次按配置回溯；后续优先新内容。平台日期过滤只作发现，核对原帖/评论自己的日期，不用视频日期冒充评论日期。每个 query_id 用 channel_runs 中自己的成功窗口；失败/未跑组合下次补查，不能用其他组合的全局成功时间跳过。

默认 45 分钟/20 条候选是单批预算，不是词库规模和检索完成标准。先覆盖不同分支再深入，找到足够客户不能替代覆盖检查；预算耗尽保存未执行/部分/受限查询、下一页/评论恢复位置和新词任务，明确 partial，下轮补查，不自行调度。先查需求表达和相关讨论入口，再查痛点；默认记录搜索实际返回的链接/文本，不强制展开评论。信号/渠道开发在相关且有预算时进行，单列不计需求。两个成功但零合格结果的同词族，换当地词、口语、句式、场景或平台。冷却记录产品/语言/平台/日期/next_check_at，不把一次 LED 经验写成永久全行业黑名单。有新假设才试新角度，不盲目扩大产品范围。

默认公开、免费、只读，不自行登录注册、加群或联系。已明确授权的现有账号按上面的访问规则使用。访问限制是 blocked/error，不是“零需求”。缺少专用社媒搜索工具时使用现有网页定向搜索收录链接，不要求用户申请接口、提供 Key 或订阅服务。

## 可选：用户要求深入核验时的审查顺序

按 [evidence.md](references/evidence.md) 逐条判断：

1. 打开原文，记录作者、原话和可定位 URL。评论需评论者、内容、自己的日期及定位/上下文。卖家视频下“price?”不是自动合格的采购需求。摘要、聚合页或上下文不足为 possible，进待核验。
2. explicit 是买方明确采购/安装；pain 是使用方本人描述痛点且产品为合理解，分 seeking/complaint。经销商自己明确求购也可作买家；卖家广告和第三方泛论排除。
3. 判断 demand_mode：purchase/rental/service/replacement/unknown。求当地短租不等于向工厂买设备；仅卖硬件却无法直接满足时，supply_route=partner-only/unknown，待核验，不硬算直接采购。
4. 核对截止日期、修改/撤销/授标、最新回复、已购其他方案及明确拒绝目标产品的反证。新帖或“没人说已解决”不证明 open。截止时区按公告本地时间处理，不明则 unknown。
5. 核对产品/供货匹配：适用条件、成本、场地、认证、MOQ/交期。记录“痛点→可能方案→限制”，不要从一个痛点推定客户一定买该产品。
6. 核验 contact_path=free-direct/free-registration/paywalled/unknown，记录联系来源和可执行路径。免费浏览不等于可免费联系；公开帖不等于可私信。需要新注册的路径不能交付为可跟进；free-registration 仅在已有授权账号中实际核实免费联系能力时可用。记录 source_kind、access_context 和联系路径证据。B2B 平台及付费联系路径进入 excluded，不挤占待核验客户清单。确实找到独立的免费买方原帖/官网原需求才可另行重新审查，不从 B2B 复制联系人冒充独立来源。
7. 采购编号/原帖和评论 ID 构建 stable_key；保留 story_fbid/jk/comment_id 等业务参数。转载合并，新一轮采购保留独立键。联系方式只记公开业务资料及独立来源，不猜邮箱，不拿附件作者当联系人。

## 存储与交付

按 [data.md](references/data.md) 写库：默认 candidates.json 保存发现记录，candidate-links.csv 为有相关文本的待核验线索，discovery-links.csv 为仅链接入口，excluded-candidates.csv 为排除项；可选核验库中，leads.json 是完整审查台账；leads.csv 只导出可跟进；review.csv 是 possible、免费路径/供货待核验；history.csv 是关闭、过期或不匹配；excluded.csv 单独保留 B2B/付费排除记录，只在报告中汇总排除数量及原因，不展示为客户候选。signals.jsonl 单列招聘/项目/渠道名单，不计需求。

默认报告先给待核验链接和发现入口，明确“未打开原帖”；若另做核验，再列可跟进 A→B→C。分别报告发现条数、候选条数与已核验条数，不用“0 条客户”掩盖链接收录结果。报告给窗口/预算、原话、买家角色、购买/租赁/服务意图、日期、状态、匹配、原帖/具体评论定位、免费路径的实际操作入口及账号前提、缺口与下一步；痛点附有条件的方案解释。待核验/信号/历史变化分别计数，附适用分支总数、完成/待执行/部分/受限数量、实际读取原帖与评论数量、平台/语言/词族覆盖和未完成组合。默认以 scope=link-discovery 的链接搜索分支计算本轮覆盖；content-verification 单独记录为可选核验，未读评论不冒充已读，也不因未做核验使链接收集失败。12 维准备齐不等于搜齐；只有约定发现分支全部执行并完成遗漏检查才称本轮矩阵完成。“找全”只指约定矩阵完成，不承诺全网所有买家。

零新增可短报，但渠道失败、访问限制和需要用户处理的事项不能隐藏。附件中的高产/失效结论属于其他产品、时间和环境的经验，不继承为当前事实。

## 辅助脚本

Python 3.10+ 标准库，Windows/macOS/Linux。数据默认当前工作区 lead-hunt-data/，多产品分目录；不并发写同目录，不把客户数据写进 skill 源码。

- `python scripts/run_state.py start --data-dir <目录>`；结束 `finish --started-at <返回时间> --status ok|partial|failed`。只有完整成功推进全局检查点；细分查询水位记 channel_runs。
- `python scripts/run_state.py check --data-dir <目录> --input <URL数组JSON>`；mark 记录 source_url/outcome/reason，待复查可加 review_after（含时区）。到期/新证据允许重开，不用“见过”永远排除待核验项。
- `python scripts/candidate_store.py --data-dir <目录> --input <搜索发现JSON数组>`；无需联网或读取原帖即可入库，自动去重导出。
- `python scripts/lead_store.py --data-dir <目录> --input <经审查JSON数组>`；不带 input 初始化/重建分区导出，不能代替人工证据判断。
- `python scripts/fetch_public.py --url <公开URL> --output <快照>`；抓取失败不是没有需求。

不自行创建定时任务；每日或每天多次频率由用户指定。用户另行明确授权才可使用已登录账号或执行联系动作。
