# verified-buy-leads · 客户需求查找与证据核验

帮外贸和 B2B 销售寻找**值得跟进的客户**：既找已经公开表达采购意向的买家，也找正被某个问题困扰、而你的产品正好能解决的终端客户。每条线索都核验来源、身份、联系方式和供货匹配。

适用于任何产品。使用时先告诉 AI 你的产品是什么，AI 会生成覆盖全面的关键词，再一个个关键词去找客户：先找有明确需求的，再找遇到相关问题的，最后整理值得主动联系的开发名单。

**适合每天定时运行。** 首次运行回溯近期内容；之后每次只找上次运行以来的新内容（通常就是当天），并自动去重，见过的链接不会重复出现。

这是给 AI 助手使用的 Skill，不是独立运行的全网爬虫。AI 负责分析关键词、搜索、阅读与核验；配套 Python 脚本负责运行窗口、去重、保存网页和维护本地线索库。

## 适合什么场景

- 查找目标产品的公开 RFQ、求购帖和采购公告，包括政府和国际组织招标。
- 查找终端客户的痛点帖：求助、求推荐或吐槽现有方案，而你的产品能解决。
- 整理开发名单：新开业、翻新扩建等触发事件，进口商、经销商、安装商等渠道客户。
- 从需求页追溯买家公司及公开业务联系方式。
- 每天复查新线索，保留状态更新和历史记录。

## 三类结果

**明确需求**：对方点名要买或要装你的产品，例如 RFQ、求购帖、招标公告。

**潜在需求**：终端客户本人亲述的痛点，你的产品能解决。不搜"买产品"，而是搜"痛点"。以 LED 显示屏为例：

| 客户类型 | 痛点关键词 |
| --- | --- |
| 教堂 | "projector too dim"、"can't see lyrics"、想换掉投影 |
| 酒吧 | "projector washed out"、"best display for bar" |
| 餐厅 / 健身房 / 零售 | digital menu board、schedule display、storefront screen |
| 通用 | "replace projector with LED"、"alternatives to projector" |

求推荐、求助的定 B，可以直接给方案切入；纯吐槽的定 C。每条潜在需求的备注都写一句"痛点 → 产品解决方案"，跟进时可以直接当话术用。第三方讨论和卖家广告不算。

**开发名单**：对方没有表达需求，但有理由主动联系，例如新店开业、场馆翻新、招聘相关岗位、从海外进口同类产品、本地经销商和安装商。单独列出，附触发事件和建议切入点，不计入线索数。

获客方法覆盖 B2B 求购平台、搜索引擎指令、社媒求购帖、政府与国际组织招标、Reddit 和行业论坛、问答网站、竞品差评、开业和扩张新闻、建设许可、招聘信息、免费提单数据、竞品客户案例、展会参展商名单、行业协会名录、企业名录和地图搜索。完整列表见[获客方法](references/strategies.md)。

**公开内容不等于当前订单。** 本 Skill 将“公开需求待确认”和“买家已确认需求”分开。找到邮箱不代表需求仍有效，也不保证对方回复或成交。允许返回零条结果，不为了数量降低证据要求。

## 快速开始

将整个 `verified-buy-leads` 文件夹放入所用 AI 客户端的技能目录，保留 `scripts/`、`references/` 和 `assets/`。通用安装方法见[技能库说明](../README.md#如何使用)。也可以让支持本地文件读取的 AI 直接读取本目录的 [SKILL.md](SKILL.md)，按流程执行。

对 AI 说：

```text
请使用 verified-buy-leads 帮我找客户。
```

AI 会先问你的产品是什么。也可以一次说清楚：

```text
请使用 verified-buy-leads 帮我找客户。我做 LED 显示屏，从中国供货。
想找有需求的终端客户，比如酒吧、教堂、餐厅、健身房；遇到投影太暗等问题、能用 LED 屏解决的潜在客户也要。
优先美国和英国。本次最多搜索 45 分钟、核验 20 条候选。
把配置和线索保存到 D:/lead-hunt-data，不联系任何人。
```

AI 会先展示按客户类型分组的关键词计划，然后直接开始检索；你可以随时让它增减客户类型或关键词。以上产品和市场只是示例，未说明的条件会标为待核验。

关键词按 12 个维度生成，确保覆盖全面：产品名称和别称、规格词、目标市场语言、采购表达、终端客户类型、被替代方案、痛点、求推荐句式、使用场景、触发事件、渠道中间商、决策人职位。计划保存在配置中，之后每天沿用并补充。

之后每天对 AI 说"用 verified-buy-leads 找今天的新客户"即可，也可以在客户端里设置每日定时运行。Skill 本身不会自动创建定时任务。

## 运行要求

| 能力 | 要求 |
| --- | --- |
| 搜索与网页核验 | AI 助手需要可用的联网搜索或浏览工具；没有联网能力时无法完成新的线索检索 |
| 本地保存和导出 | Python 3.10 或更高版本，仅使用标准库，无需安装 pip 包 |
| 操作系统 | Windows、macOS、Linux；不依赖 Bash、curl 或 GNU date |
| 平台账号 | 公开检索不要求账号；登录、报价和联系需要用户另行授权 |

渠道可达性、公开字段及账号权益需要当次核验。Skill 不内置“某平台每天必有几条线索”的承诺。

## 配置自己的业务

将 [assets/config.example.json](assets/config.example.json) 复制到数据目录，命名为 `config.json`，按实际情况填写。也可以直接把业务条件告诉 AI，让它生成配置。

| 字段 | 用途 |
| --- | --- |
| `products` / `product_description` | 可供应产品、规格和用途说明 |
| `replaces` | 产品能替代的现有方案，例如投影仪、纸质菜单 |
| `target_segments` | 终端客户类型，例如 church、bar、restaurant |
| `keyword_plan` | AI 生成的关键词计划：`explicit` 为各语言明确需求词，`pain_points` 为按客户类型整理的痛点、检索词和解决方案，`triggers` 和 `channel_partners` 用于开发名单，`coverage` 记录 12 个维度的覆盖情况 |
| `available_certifications` | 已有认证；留空表示未知，不能假定满足要求 |
| `minimum_order_quantity` / `quantity_unit` | 起订量和单位 |
| `target_countries` / `excluded_countries` | 优先市场及排除市场；空数组表示未指定 |
| `lead_time_days` / `supplier_origin` | 实际交期与供货来源 |
| `search_budget_minutes` | 单次搜索时间预算，默认 45 分钟 |
| `max_candidates_to_verify` | 单次核验候选上限，默认 20 条 |
| `first_run_lookback_days` | 仅首次运行使用的回溯天数：明确需求 30、潜在需求 365、开发名单 90。之后每次只找上次运行以来的新内容 |
| `data_dir` / `timezone` | 数据目录和判断日期使用的时区 |

相对数据路径由运行时的工作目录解析；建议使用绝对路径。运行数据应与 Skill 源码分开，提交 GitHub 时不要包含实际线索、联系方式或账号配置。

## 你会拿到什么

AI 先说明本次是首次运行还是日常运行、检索的时间窗口，然后只报告本次新增和状态有变化的线索：先明确需求，再潜在需求，包含买家或机构、客户类型、国家、产品、数量、来源日期、截止日期、有效状态、供货匹配、联系方式、身份把握度和来源链接，并明确下一步需要确认什么。潜在需求另附"痛点 → 解决方案"一句话。

| 优先级 | 含义 |
| --- | --- |
| A | 明确求购、仍开放、身份可靠、联系路径经过核验、供货匹配 |
| B | 明确求购但有效性、身份、联系权限或供货条件仍有缺口；或潜在需求中的求推荐、求助 |
| C | 可能需求、身份较弱或需要合作商才能执行；或潜在需求中的纯吐槽 |

A/B/C 是跟进优先级，不是真实性或成交保证。完整规则见[证据与优先级](references/evidence.md)。已关闭、过期或供货不匹配的需求保留为历史，不进入当前跟进清单。

开发名单另起一节，列出公司、类型、触发事件、建议切入点和联系方式，不计入线索数。平台线索、身份待确认线索、合作商机会分别计数；按关键词和获客方法汇报命中情况、去重跳过的数量，以及本次没来得及覆盖的关键词。渠道全部失败时，会报告无法完成检索，不会将其写成“没有需求”，下次运行也会重新覆盖这段时间。

数据目录中的文件：

| 文件 | 内容 |
| --- | --- |
| `config.json` | AI 或用户保存的业务配置 |
| `leads.json` | 主线索库，由线索库脚本维护 |
| `leads.csv` | 可用 Excel 打开的导出表，复杂证据字段保存为 JSON 字符串 |
| `history.jsonl` | 线索更新前的记录，有更新时生成 |
| `channel_runs.jsonl` | AI 保存的渠道请求、核验与失败记录 |
| `signals.jsonl` | 开发名单：触发事件、进口商、渠道客户、中标历史 |
| `runs.jsonl` | 每次运行的开始时间和结果，决定下次运行的时间窗口 |
| `seen.jsonl` | 处理过的候选链接（包括被排除的），用于去重 |

## 配套脚本

下面的命令均在本 Skill 目录执行。Windows 可以用 `py -3` 替换 `python`；其他环境使用实际可用的 Python 3 命令。

每次运行开始时获取时间窗口，结束时记录本次运行：

```powershell
python scripts/run_state.py start --data-dir D:/lead-hunt-data
python scripts/run_state.py finish --data-dir D:/lead-hunt-data --started-at <start 返回的 run_started_at> --status ok
```

`start` 返回 `mode`：`first` 表示首次运行，`daily` 表示日常运行，并给出 `since`（上次成功运行的开始时间）。`--status` 为 `ok`、`partial` 或 `failed`；failed 不会让下次的时间窗口前移。

去重：检查一批候选链接里哪些是新的，以及记录处理过的候选：

```powershell
python scripts/run_state.py check --data-dir D:/lead-hunt-data --input D:/lead-hunt-data/candidates.json
python scripts/run_state.py mark --data-dir D:/lead-hunt-data --input D:/lead-hunt-data/handled.json
```

`check` 的输入是链接数组，输出 `new` 和 `seen` 两组。`mark` 的输入是 `[{"source_url": "...", "outcome": "lead|signal|rejected", "reason": "..."}]`。链接比较前会去掉 www、末尾斜杠、片段和 utm 等跟踪参数。

初始化空库或重新导出 CSV：

```powershell
python scripts/lead_store.py --data-dir D:/lead-hunt-data
```

导入 AI 已核验并整理好的 JSON 数组：

```powershell
python scripts/lead_store.py --data-dir D:/lead-hunt-data --input D:/lead-hunt-data/reviewed-leads.json
```

输入字段见[线索库格式](references/data.md)。相同 `stable_key` 更新已有记录并保留历史；更新采用完整记录替换，请先合并要保留的联系人和证据。无效输入会被拒绝。脚本检查字段和评级条件，不能代替 AI 对真实网页的核验。不要并发写入同一个数据目录。

保存一个公开文本网页快照：

```powershell
python scripts/fetch_public.py --url "https://example.com/" --output D:/lead-hunt-data/snapshots/example.html
```

此网址仅用于演示，不是采购线索。下载结果以 JSON 输出：`ok`、`blocked` 或 `error`。空响应、HTTP 错误和常见访问挑战不会被当作正常空结果；网页成功下载后仍需要阅读和核验。该脚本不处理二进制附件或 JavaScript 页面渲染，也不保证识别所有登录墙。

运行本地回归检查：

```powershell
python -B scripts/test_helpers.py
```

检查覆盖首次初始化、同键更新、历史保留、无效导入不改主库、潜在需求的必填字段与 B/C 评级、首次与日常运行窗口、链接去重，以及网页成功/空响应/拦截处理。使用临时目录和本地测试服务器，不访问真实采购平台。

## 默认行为与边界

- 只检索公开资料、核验线索和维护本地数据，不自动注册、登录、发邮件、私信，也不在论坛或社群发帖回复。
- 不猜邮箱，不把同名同国家或附件作者当作买家身份确认。
- 联系方式逐条保留来源；公开电话不自动标为 WhatsApp。
- 不继承旧版抓取脚本的页面正则与历史产出数字；批量抓取前需验证当前结构。
- 设计为每天运行，但安装后不会自动创建定时任务，需要在客户端中自行设置。

买家回复确认仍在采购后，可根据实际回复更新确认状态，并保存日期及记录引用。只有用户明确授权，AI 才可以执行联系动作。

## 文件导航

- [SKILL.md](SKILL.md)：AI 执行入口。
- [assets/config.example.json](assets/config.example.json)：业务配置模板。
- [references/keywords.md](references/keywords.md)：关键词 12 个维度、检索顺序和 LED 屏示例。
- [references/strategies.md](references/strategies.md)：外贸获客方法大全及各方法的产出类别。
- [references/evidence.md](references/evidence.md)：证据、状态与评级规则。
- [references/channels.md](references/channels.md)：渠道选择及失败处理。
- [references/data.md](references/data.md)：线索字段与更新规则。
- `scripts/`：本地辅助脚本与离线回归检查。
