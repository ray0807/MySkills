# 通用客户需求查找：先收录链接，后核验

输入任意产品或关键词，优先搜索 Facebook、Instagram、YouTube 等免费社媒，扩展场景、买家表达和当地语言，保存相关链接。**默认不打开原帖、不读取目标网页，也不要求用户配置接口、API Key 或第三方爬虫。** 登录墙不会阻止链接入库。

## 怎么用

将整个 skill 文件夹更新到你的 agent 的 skills 目录，然后说：

> 用 verified-buy-leads 找工业除湿机的客户线索，尽量覆盖不同场景和语言。先记录链接，不用打开帖子。

也可输入“包装托盘”“宠物胸背带”等关键词；没给主题才询问。其他国家、规格、MOQ 等未知先留空，不需要填长表。不同产品用独立数据目录。

Skill 使用宿主已有搜索工具；没有专用 social.search 也可以用网页 site: 定向搜索。它不会自动获得社媒内部或私密群搜索能力，也不能保证搜索引擎收录了所有帖子。没有真实搜索结果时不编造链接。

## 默认交付什么

| 文件 | 内容 |
| --- | --- |
| candidate-links.csv | 有相关需求摘要/索引文本的待核验线索；原帖未读 |
| discovery-links.csv | 只有相关链接的发现入口，例如群组、视频、账号；不计作有需求的客户 |
| candidates.json | 完整发现台账，按 URL 去重 |
| excluded-candidates.csv | B2B 平台、付费线索排除记录，不当客户推荐 |
| leads.csv | 只有另行核验后符合条件的可跟进客户 |

记录链接、实际搜索词、产品、发现时间、工具名，以及真实返回的标题、需求摘要、作者和发布日期。没有的字段留空，发现时间不能冒充发帖时间。摘要、索引文本、仅链接分别标 search-snippet/indexed-text/link-only，统一标“未核验”。

例如报告可以是：“发现 30 个链接：12 条带相关需求摘要、18 个讨论入口；原帖均未打开，已核验客户 0。”不能把它简化成“找不到客户”，也不能把 30 个链接说成 30 位确认采购客户。

阿里国际站、Made-in-China、TradeKey 等 B2B 平台及付费聚合站继续排除；免费社媒需要登录不能直接推定它收费，不因无法打开而丢弃相关链接。只看到卖家广告、点赞或泛泛互动，不算需求摘要，可留作相关讨论入口。

## 尽量减少漏搜

默认 coverage-first：先建立产品别名/子品类、场景、买方口语、痛点、替代方案和目标市场语言，保存 keyword_plan.json。规划需求词直搜与相关群组/评测/教程入口两条路线，从真实结果滚动补词。

45 分钟/20 条候选是单批预算，未完成查询保存队列及恢复位置。默认覆盖率仅计算链接发现范围；没有读取评论要明说，但不因未做原帖核验就把已完成的链接收集算失败。访问/查询未完成仍 partial，不承诺全网零遗漏，不自行建立定时任务。

## 可选：后续核验

只有用户要求“帮我核验这些线索”时，再尝试读取原帖、评论、身份、时效、供货匹配及免费联系路径。没有读取能力就保留待核验状态，不强迫用户申请接口。公开求购不是买家已回复确认，采购/租赁/服务意图要分清。

核验库导出 review.csv（缺证据）、history.csv（关闭/过期/不匹配）、excluded.csv（排除项），leads.json 保留核验台账，history.jsonl 保存更新前版本。收录脚本不会自动将候选升级成核验客户。搜索、收录和读取均不授权发消息、评论或加群。

## 本地辅助脚本

Python 3.10+，仅标准库。从本 skill 目录执行：

```sh
python scripts/candidate_store.py --data-dir ./lead-hunt-data/product-a --input ./search-results.json
python scripts/run_state.py check --data-dir ./lead-hunt-data/product-a --input ./candidate-urls.json
python -B scripts/test_helpers.py
```

search-results.json 为搜索发现数组，完整例子见 [data.md](references/data.md)。脚本不联网，不独立搜索，不需要 API Key。CSV 使用 UTF-8 BOM，方便 Excel 打开；重新收录相同链接不会增加重复行，只有链接的记录不会覆盖以前保存的需求摘要。原有 run_state 与 lead_store 脚本继续用于增量状态和可选核验库。

配置模板见 [config.example.json](assets/config.example.json)，默认 collection_mode=link-first、open_source_pages=false、require_api_setup=false，由 agent 读取执行。[SKILL.md](SKILL.md) 为工作规则，[keywords.md](references/keywords.md) 为覆盖计划，[channels.md](references/channels.md) 为渠道准入。请同步整个文件夹，包含 scripts 和 assets，避免只更新说明而沿用旧规则。
