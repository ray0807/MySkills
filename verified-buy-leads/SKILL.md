---
name: verified-buy-leads
description: 根据用户输入的产品或关键词，构建产品、买家意图、场景、当地语言与平台矩阵，查找和审查明确需求、本人亲述痛点，核验免费联系路径、有效性及供货模式，分开展示可跟进、待核验和间接信号。支持每日增量检索，不限定 LED 或任何行业。
---

# 通用客户需求查找与筛选

先找需求证据，再查买家；纯公司名单、招聘/开业新闻不能充作采购需求。公开求购只证明曾表达意向，默认 public-unconfirmed；只有买方明确回复仍在采购才标 buyer-confirmed。允许零结果，不凑数。

## 从用户产品或关键词开始

接受产品名、型号、关键词或用途，例如“工业除湿机”“可堆叠托盘”“宠物胸背带”。已经给关键词就建立产品理解，不强迫重复填写产品名称。只有 screen/配件等歧义且无法确定产品时问一个澄清问题；完全没给主题时问“你想找什么产品或关键词的客户？”。定时运行直接使用已确认配置，缺主题才暂停提醒。

读取 [配置模板](assets/config.example.json)。明确是什么/不是什么、规格词族、能解决及不能保证解决的问题，以及 business_models（默认 product-sale，可配置 rental-service/installation-service/distribution）。未知认证、起订量、交期与价格不假定满足。其他缺项先记录假设，小批量探索，不给用户长问卷。

不同产品用独立数据目录/topic_id，换产品重建计划，不继承前一产品的去重记录、失败渠道或时间水位。附件 LED 示例、固定三个运行时间、国家和客户画像不作为通用默认值。

## 关键词与覆盖计划

读 [keywords.md](references/keywords.md) 和 [queries.md](references/queries.md)。保留 12 维检查，但按产品适用性填充，不强行编造十种客户或七种语言。按“产品词族 × 买方意图 × 使用场景 × 当地语言 × 平台”建立 query_cells，简短展示后执行，不额外等待确认。

Facebook、Instagram、TikTok、YouTube、X、Threads、LinkedIn、Reddit/论坛都是候选。按产品、可用工具和预算轮换，不强求每轮跑全；未能读取的评论区不能称已覆盖。不假定存在 social.search/browser.search；按 [channels.md](references/channels.md) 和 [strategies.md](references/strategies.md) 使用实际工具。

## 增量检索与主动调整

运行 run_state.py start 读检查点。首次按配置回溯；后续优先新内容。平台日期过滤只作发现，核对原帖/评论自己的日期，不用视频日期冒充评论日期。每个 query_id 用 channel_runs 中自己的成功窗口；失败/未跑组合下次补查，不能用其他组合的全局成功时间跳过。

默认 45 分钟/20 条候选。先明确需求和买方评论，再本人痛点；信号/渠道开发在相关且有预算时进行，单列不计需求。两个成功但零合格结果的同词族，换当地词、口语、句式、场景或平台。冷却记录产品/语言/平台/日期/next_check_at，不把一次 LED 经验写成永久全行业黑名单。有新假设才试新角度，不盲目扩大产品范围。

默认公开、免费、只读，不登录注册、不发帖评论、不发消息。访问限制是 blocked/error，不是“零需求”。账号或检索接口缺 Key 时只提示补缺项，验证后用，不阻断其他免费渠道。

## 每条候选的审查顺序

按 [evidence.md](references/evidence.md) 逐条判断：

1. 打开原文，记录作者、原话和可定位 URL。评论需评论者、内容、自己的日期及定位/上下文。卖家视频下“price?”不是自动合格的采购需求。摘要、聚合页或上下文不足为 possible，进待核验。
2. explicit 是买方明确采购/安装；pain 是使用方本人描述痛点且产品为合理解，分 seeking/complaint。经销商自己明确求购也可作买家；卖家广告和第三方泛论排除。
3. 判断 demand_mode：purchase/rental/service/replacement/unknown。求当地短租不等于向工厂买设备；仅卖硬件却无法直接满足时，supply_route=partner-only/unknown，待核验，不硬算直接采购。
4. 核对截止日期、修改/撤销/授标、最新回复、已购其他方案及明确拒绝目标产品的反证。新帖或“没人说已解决”不证明 open。截止时区按公告本地时间处理，不明则 unknown。
5. 核对产品/供货匹配：适用条件、成本、场地、认证、MOQ/交期。记录“痛点→可能方案→限制”，不要从一个痛点推定客户一定买该产品。
6. 核验 contact_path=free-direct/free-registration/paywalled/unknown，记录联系来源和可执行路径。免费浏览不等于可免费联系；公开帖不等于可私信。免费注册的权限需要证据，不承诺注册就能看。付费聚合页回溯免费原公告；govttenders.co.in 保持排除。只有付费或未知路径进 review。
7. 采购编号/原帖和评论 ID 构建 stable_key；保留 story_fbid/jk/comment_id 等业务参数。转载合并，新一轮采购保留独立键。联系方式只记公开业务资料及独立来源，不猜邮箱，不拿附件作者当联系人。

## 存储与交付

按 [data.md](references/data.md) 写库：leads.json 是完整审查台账；leads.csv 只导出可跟进；review.csv 是 possible、免费路径/供货待核验；history.csv 是关闭、过期或不匹配。signals.jsonl 单列招聘/项目/渠道名单，不计需求。

日报给窗口/预算、可跟进 A→B→C、原话、买家角色、购买/租赁/服务意图、日期、状态、匹配、免费路径、缺口与下一步；痛点附有条件的方案解释。待核验/信号/历史变化分别计数，附平台/语言/词族覆盖和未完成组合。“找全”只指约定矩阵完成，不承诺全网所有买家。

零新增可短报，但渠道失败、访问限制和需要用户处理的事项不能隐藏。附件中的高产/失效结论属于其他产品、时间和环境的经验，不继承为当前事实。

## 辅助脚本

Python 3.10+ 标准库，Windows/macOS/Linux。数据默认当前工作区 lead-hunt-data/，多产品分目录；不并发写同目录，不把客户数据写进 skill 源码。

- `python scripts/run_state.py start --data-dir <目录>`；结束 `finish --started-at <返回时间> --status ok|partial|failed`。只有完整成功推进全局检查点；细分查询水位记 channel_runs。
- `python scripts/run_state.py check --data-dir <目录> --input <URL数组JSON>`；mark 记录 source_url/outcome/reason，待复查可加 review_after（含时区）。到期/新证据允许重开，不用“见过”永远排除待核验项。
- `python scripts/lead_store.py --data-dir <目录> --input <经审查JSON数组>`；不带 input 初始化/重建分区导出，不能代替人工证据判断。
- `python scripts/fetch_public.py --url <公开URL> --output <快照>`；抓取失败不是没有需求。

不自行创建定时任务；每日或每天多次频率由用户指定。用户另行明确授权才可使用已登录账号或执行联系动作。
