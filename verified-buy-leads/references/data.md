# 线索库格式

主库 `leads.json` 是 JSON 数组；`leads.csv` 是对应导出；`history.jsonl` 保存更新前的记录。UTF-8，CSV 使用 BOM 方便 Excel 打开，复杂证据字段为 JSON 字符串。CSV 只是导出，更新通过 JSON 输入。数据包含公开业务联系方式，按用户目录和权限保存。

每条记录必填：
- `stable_key`：例如 `alibaba-rfq:12345`、`ted:<公告号>`；没有编号时使用原始需求 URL（删除跟踪参数但保留业务参数）。采购编号优先，转载与原文合并。再次采购有新编号时使用新键。
- `buyer`, `country`, `product`：字符串，可为空表示未知。
- `source_url`：真实打开过的原需求 http(s) URL。
- `need_excerpt`：支持采购意向或痛点的原文摘录。
- `need_level`：explicit / pain / possible。
- `need_level` 为 pain 时另需：`pain_type`（seeking / complaint）、`pain_point`（客户遇到的问题）、`solution_pitch`（一句话"痛点 → 产品解决方案"）。seeking 的 priority 必须为 B，complaint 必须为 C。
- `validity`, `confirmation`, `identity_confidence`, `fit`, `priority`：枚举见 evidence.md。
- `last_verified_at`：含时区的 ISO 8601 时间。
- `contacts`：数组，可为空。元素包含 `type`, `value`, `source_url`, `confidence`；type 可为 email、phone、whatsapp、linkedin、website、platform。联系人来源必须是真实 http(s) URL。

可选：`segment`（终端客户类型，如 church、bar）、`keyword`（命中的检索词）、`quantity`, `quantity_unit`, `specifications`, `published_at`, `deadline_at`, `delivery_country`, `identity_evidence`, `validity_evidence`, `fit_gaps`, `next_step`, `confirmation_evidence`, `confirmation_at`。未知留 null 或空，不填写模型猜测。枚举不得随意新增。

buyer-confirmed 必须有 confirmation_evidence 和含时区的 confirmation_at。A 必须 explicit、open、high、matched 且存在 high 联系路径；平台权限和联系对象是否正确仍需人工核验。需要逐项缺口时使用 fit_gaps。

导入同 stable_key 采用完整记录替换；因此更新前读取原记录，合并需要保留的联系人与证据，再导入。脚本添加/保留 lead_id 和 first_seen_at，刷新 updated_at。导入失败不改主库；单进程使用，不并发写同一目录。历史先落盘，主库原子替换；导出失败时以主库为准并重新运行初始化命令重建 CSV。

示例结构（占位 URL 不能作为实际线索使用）：
```json
{
  "stable_key": "platform:procurement-id",
  "buyer": "", "country": "", "product": "",
  "source_url": "https://example.com/request",
  "need_excerpt": "采购原文",
  "need_level": "explicit", "validity": "unknown",
  "confirmation": "public-unconfirmed", "identity_confidence": "unknown",
  "fit": "unknown", "priority": "B",
  "last_verified_at": "2026-10-12T12:00:00+08:00",
  "contacts": [], "next_step": "核验发布者与公司关系和需求有效状态"
}
```

## 运行状态与去重

- `runs.jsonl`：每次运行一行，由 `run_state.py finish` 写入：`run_started_at, finished_at, status(ok/partial/failed), summary`。没有 ok 或 partial 记录时为首次运行。
- `seen.jsonl`：处理过的候选链接，由 `run_state.py mark` 写入：`source_url`（规范化后）、`outcome`（lead / signal / rejected）、`reason`、`marked_at`。被排除的候选也要记录，避免第二天重复核验。
- 去重时，`leads.json`、`signals.jsonl` 和 `seen.jsonl` 中的链接都算见过。链接规范化会去掉 www、末尾斜杠、片段和 utm 等跟踪参数。同一需求换了链接时，仍需按 stable_key 和内容人工判断是否重复。

## 开发名单 signals.jsonl

每行一个对象：`stable_key`、`company`、`country`、`segment`、`signal_type`（trigger / importer / channel_partner / award_history / other）、`trigger`（发生了什么）、`source_url`、`evidence_excerpt`、`suggested_angle`（建议的切入话术）、`contacts`（格式同主库）、`found_at`。未知字段留空，不编造。

## 潜在需求示例
```json
{
  "stable_key": "reddit:abc123",
  "buyer": "", "country": "US", "product": "LED screen",
  "segment": "church", "keyword": "projector too dim church",
  "source_url": "https://example.com/r/churchtech/abc123",
  "need_excerpt": "Our projector is too dim, nobody can read the lyrics. What should we upgrade to?",
  "need_level": "pain", "pain_type": "seeking",
  "pain_point": "投影太暗，会众看不清歌词",
  "solution_pitch": "投影开灯后看不清歌词 → LED 屏高亮度，开灯也清晰",
  "validity": "unknown", "confirmation": "public-unconfirmed",
  "identity_confidence": "low", "fit": "unknown", "priority": "B",
  "last_verified_at": "2026-10-12T12:00:00+08:00",
  "contacts": [{"type": "platform", "value": "帖子回复", "source_url": "https://example.com/r/churchtech/abc123", "confidence": "medium"}],
  "next_step": "确认教堂名称和场地尺寸，回复中给出 LED 替代投影方案"
}
```
