# 用户交付优先规则

默认唯一交付为 客户名单.csv（UTF-8 BOM），由 customer_list.py 合并 candidates.json 与 leads.json；无 leads.json 时兼容旧 review.csv/leads.csv。按规范化 URL 去重，有需求文本/已核验信息优先，旧待核验记录不会因本轮未新增而消失。排除 B2B/付费、关闭/过期/不匹配。只有相关入口也可列入同表，但类型=发现入口，不算有需求客户。状态在列中表示，不让用户理解内部文件分类。

candidate_store.py 默认入库后自动更新这份表，不再生成分区 CSV。--diagnostics 才额外生成下文的内部诊断导出。lead_store.py 仍兼容原有内部导出，并自动刷新统一表；内部文件默认不向用户罗列。已有分区文件保留，不擅自删除历史数据。可运行 `python scripts/customer_list.py --data-dir <目录>` 单独汇总旧数据。

列：类型、客户或作者、产品、标题或需求摘要、链接、状态、发布日期、发现时间、搜索词、备注。累计总数与本轮新增分开；未知字段留空，不推断身份或发布日期。

# 默认链接收录库：无需打开目标页面

默认 link-first 使用 candidates.json，与下文的可选核验库 leads.json 分开。不会为满足旧库 need_excerpt/last_verified_at 要求伪造原文或核验时间。

运行：`python scripts/candidate_store.py --data-dir <目录> --input <搜索发现JSON数组>`。不带 input 可重建导出。脚本本地运行、不联网、不读目标页面、不需要 Key 或额外依赖。

必填：source_url（搜索实际返回的 HTTP(S) 目标链接）、product（用户主题）、query（实际查询）、found_at（含时区发现时间）、evidence_mode（search-snippet/indexed-text/link-only）。

- search-snippet/indexed-text 另需 excerpt：逐字保留实际可见的相关需求文本，不补写、不将摘要冒充全文。
- link-only 无 excerpt；title、author、published_at、provider 可选，未知用空字符串或省略。published_at 只记录工具实际返回的日期文字，不能拿 found_at 代替。
- source_kind 沿用来源类型，未知可保存但不当已核验；已知 B2B 域名仍自动排除。新 B2B/线索站需 agent 正确标记类型。
- 所有发现记录强制 verification=unverified、validity/contact_path/identity_confidence=unknown、confirmation=public-unconfirmed，不能靠输入字段升级为核验客户。

导出：candidate-links.csv（有相关需求文本的待核验线索）、discovery-links.csv（仅链接入口）、excluded-candidates.csv（B2B/付费聚合排除项）。candidates.json 保存完整台账；CSV 有 UTF-8 BOM 和公式式文本转义。广告摘要不应写作需求摘录，只作相关入口或排除。文件中候选“线索”不代表已确认客户。

示例（占位地址，不是实际线索）：

```json
[
  {"source_url":"https://www.facebook.com/groups/example/posts/123", "product":"工业除湿机", "query":"site:facebook.com dehumidifier looking for", "found_at":"2026-10-15T10:00:00+08:00", "evidence_mode":"search-snippet", "excerpt":"Looking for a warehouse dehumidifier supplier", "provider":"实际搜索工具名"},
  {"source_url":"https://www.youtube.com/watch?v=example", "product":"工业除湿机", "query":"site:youtube.com warehouse humidity", "found_at":"2026-10-15T10:00:00+08:00", "evidence_mode":"link-only", "title":"仓库湿度相关讨论入口"}
]
```

按规范化 URL 去重，保留评论片段/业务参数；重复发现更新，只有链接的新记录不会抹掉旧摘录。run_state.check 同时读取 candidates.json 去重。后续核验应主动读取候选队列，不因为 URL 已 seen 永久跳过；有新文本可直接再次导入。同一需求不同 URL 仍需 agent 合并判断。每个产品用独立目录。

候选不会自动迁入核验库；用户要求后读取原文核验，满足规则才完整导入 leads.json。候选台账保留供追溯，报告按规范化 URL 合并计数，已升级条目不重复计入当前待核验数量。单进程写同目录；主 JSON 原子替换，CSV 失败可重建，不承诺跨文件事务。

---

# 线索与状态格式

`leads.json` 是完整 JSON 数组主库；四份 CSV 是互斥分区：可跟进 leads.csv、待核验 review.csv、关闭/过期/不匹配 history.csv、排除项 excluded.csv（不作为客户交付）。history.jsonl 保存更新前版本。CSV 使用 UTF-8 BOM，复杂字段为 JSON 字符串，公式式文本转义。

## 记录字段

必填：stable_key、buyer、country、product、source_url、need_excerpt、need_level、validity、confirmation、identity_confidence、fit、priority、last_verified_at、contacts。

- stable_key 用采购编号/原帖及评论 ID，转载合并。buyer/country/product 字符串可空表示未知；stable_key 和摘录不得空。
- need_level 为 explicit / pain / possible；validity 为 open / closed / expired / unknown。
- confirmation 为 public-unconfirmed / buyer-confirmed；后者另需 confirmation_evidence 和含时区 confirmation_at。
- identity_confidence 为 high / medium / low / unknown；fit 为 matched / partial / mismatch / unknown；priority 为 A / B / C。
- pain 必须有 pain_type（seeking 对应 B、complaint 对应 C）、pain_point、solution_pitch；另记录方案限制和反证，避免硬推产品。
- contacts 数组可空；元素含 type（email/phone/whatsapp/linkedin/website/platform）、value、source_url、confidence（high/medium/low/unknown）。只采集公开业务联系方式，不猜测。
- source_url 和联系人来源是真实打开过的 HTTP(S) 原文；last_verified_at 含时区。

新增审查字段：

- source_kind：social / forum / buyer-owned / official-procurement / b2b-marketplace / lead-directory / paid-aggregator / unknown。已知社媒及 B2B 域名由脚本识别，其他域名由审查者标注；缺失不能进入可跟进。域名边界精确匹配主域/子域，不使用字符串包含判断。
- access_context：public / existing-authorized-account / registration-required / unknown。free-registration 只在已有授权账号中实际验证联系能力后可跟进；需要新注册/申请权限的不能。

- demand_mode：purchase / rental / service / replacement / unknown。
- supply_route：direct / partner-only / unknown；只卖设备无法承接当地短租时不能记 direct。
- contact_path：free-direct / free-registration / paywalled / unknown。
- contact_path_evidence：对象，含 source_url、observation（实际观察到的联系权限/路径）、checked_at（含时区）。免费浏览不能替代免费联系证据。
- next_review_at：可选，含时区复查时间。

A 必须来源通过准入、explicit/open/high/matched、有 high 联系方式、经证据核实的免费联系路径及 direct 供货。脚本拒绝不满足的新 A。旧记录缺少新增字段按 unknown 处理，保留台账，但进入待核验，不自动补造证据。

分区优先级：来源属于 B2B/线索目录/付费聚合或 contact_path=paywalled → excluded；其余 closed/expired 或 fit=mismatch → history；possible、来源未知、需新注册、未核实免费联系（证据和至少 medium 的合格联系来源）、supply_route 非 direct → review；其余 explicit/pain → active。已知 B2B 域名不能用 source_kind=social 绕过；证据或联系人仍来自被排除平台时不构成合格免费路径。record_status、exclusion_reason、CSV 中 source_kind 由脚本计算，不接受输入自行提升。excluded 保留审计，仅汇总排除原因，不在推荐客户/待核验候选中混列。active 不代表买家已回复确认。

旧库重建：不带 --input 运行 lead_store.py，重新计算四份导出；原始记录不删除。旧版 free-registration 没有现有账号授权上下文时进入 review；known B2B 即使旧评级 A 也进入 excluded。

可选证据字段：segment、keyword、quantity、quantity_unit、specifications、published_at、deadline_at、delivery_country、identity_evidence、validity_evidence、fit_gaps、solution_limitations、author、comment_locator、next_step。未知留空，不推断数量和截止日期。

示例为占位记录，不能作为真实客户：

```json
{
  "stable_key":"forum:post-1:comment-2",
  "buyer":"", "country":"", "product":"工业除湿机",
  "source_url":"https://example.com/post/1#comment-2",
  "need_excerpt":"Looking for a supplier of warehouse dehumidifiers",
  "need_level":"explicit", "validity":"unknown",
  "confirmation":"public-unconfirmed", "identity_confidence":"unknown",
  "fit":"unknown", "priority":"B", "demand_mode":"purchase",
  "source_kind":"forum", "access_context":"public",
  "supply_route":"unknown", "contact_path":"unknown",
  "last_verified_at":"2026-10-15T12:00:00+08:00", "contacts":[],
  "next_step":"核实发布者身份、采购状态和免费业务联系路径"
}
```

同 stable_key 导入采用完整记录替换：先读取旧记录、合并需保留证据再导入。lead_id、first_seen_at 保留，updated_at 刷新。输入校验失败不改主库；单进程写同目录。主库原子替换，历史与 CSV 不是跨文件事务；导出失败以主库为准，重新运行不带 input 的命令重建。

## 增量运行

runs.jsonl：run_started_at、finished_at、status（ok/partial/failed）、summary；只有 ok 推进全局检查点。channel_runs.jsonl 按查询分别保存成功窗口，未执行/失败组合补查。

seen.jsonl：source_url、outcome（lead/signal/rejected）、reason、marked_at、可选 review_after（含时区）。check 合并主库、signals 和已处理 URL，返回 new/seen/revisit；mark 最后一次记录决定该 URL 后续复查时间，不传 review_after 表示本轮处理后取消既有预约。主库 next_review_at 在未被 mark 覆盖时生效。技术失败不应标永久 rejected，保留待复查。

URL 去常见跟踪参数、www、末尾斜杠和纯回顶部片段；保留 ref 等业务参数和评论片段。不同 URL 的同一采购仍按 stable_key/内容合并；变更的需求或新证据可主动复查。不同产品隔离数据目录。

## signals.jsonl

AI 逐行写对象：stable_key、company、country、segment、signal_type（trigger/importer/channel_partner/award_history/other）、trigger、source_url、evidence_excerpt、suggested_angle、contacts、found_at。contacts 与主库格式一致，时间含时区。信号不导入需求 CSV、不计入需求数。

## keyword_plan.json 与覆盖队列

由 agent 将已确认词库和执行计划写入用户数据目录 keyword_plan.json，结构见 keywords.md 与配置模板。它是需要持续更新的执行状态，不能只在回答里列几个词。coverage_obligations 保存应查范围，query_cells 保存 planned/running/complete/partial/blocked/deferred/not-applicable、原因及恢复位置；expansion_queue 保存真实搜索新发现的别名/场景等欠账。适用分支未完成必须列在报告中；分支不适用需理由。

每次 channel_runs 另记 entry_type、pages_read、comments_read、sort_order、tool_limit、stop_reason、resume_cursor 或恢复说明。一次请求 ok/empty 不代表整项查询完成；分页/评论尚未读完就标 query partial，不推进该查询完整窗口。不得存储 cookie、token 等登录信息。以上计划/查询日志由 agent 维护，run_state.py 不自动替 agent 做搜索或覆盖审计。
