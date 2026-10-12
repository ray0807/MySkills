# verified-buy-leads · 采购需求证据核验

帮外贸和 B2B 销售寻找**已经公开表达采购意向、值得继续确认的客户**，并核验需求是否有效、买家身份是否匹配、联系方式是否可靠，以及你的供货条件是否满足要求。

这是给 AI 助手使用的 Skill，不是独立运行的全网爬虫。AI 负责搜索、阅读与核验；配套 Python 脚本负责保存网页和维护本地线索库。

## 适合什么场景

- 查找目标产品的公开 RFQ、求购帖和采购公告。
- 从需求页追溯买家公司及公开业务联系方式。
- 每天或每周复查采购线索，保留状态更新和历史记录。
- 区分可跟进需求、平台线索、合作商机会与行业需求信号。

**公开求购不等于当前订单。** 本 Skill 将“公开需求待确认”和“买家已确认需求”分开。找到邮箱不代表需求仍有效，也不保证对方回复或成交。允许返回零条结果，不为了数量降低证据要求。

## 快速开始

将整个 `verified-buy-leads` 文件夹放入所用 AI 客户端的技能目录，保留 `scripts/`、`references/` 和 `assets/`。通用安装方法见[技能库说明](../README.md#如何使用)。也可以让支持本地文件读取的 AI 直接读取本目录的 [SKILL.md](SKILL.md)，按流程执行。

对 AI 说：

```text
请使用 verified-buy-leads 查找安全护目镜的公开采购需求。
我从中国供货，起订量 500 件，交期 20 天，优先阿联酋和沙特。
已有认证和具体规格稍后补充，暂时标为待核验，不要默认满足。
本次最多搜索 45 分钟、核验 20 条候选。
把配置和线索保存到 D:/lead-hunt-data，不联系任何买家。
```

以上产品、国家和供货能力只是示例，请替换成自己的实际情况。产品范围未明确时，AI 会先询问；其他未知条件会标为待核验。

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
| `products` | 可供应产品与必要规格 |
| `keywords_by_language` | 按语言组织的搜索词 |
| `available_certifications` | 已有认证；留空表示未知，不能假定满足要求 |
| `minimum_order_quantity` / `quantity_unit` | 起订量和单位 |
| `target_countries` / `excluded_countries` | 优先市场及排除市场；空数组表示未指定 |
| `lead_time_days` / `supplier_origin` | 实际交期与供货来源 |
| `search_budget_minutes` | 单次搜索时间预算，默认 45 分钟 |
| `max_candidates_to_verify` | 单次核验候选上限，默认 20 条 |
| `discovery_lookback_days` | 发现阶段的回溯窗口，默认 30 天；不代替有效性判断 |
| `data_dir` / `timezone` | 数据目录和判断日期使用的时区 |

相对数据路径由运行时的工作目录解析；建议使用绝对路径。运行数据应与 Skill 源码分开，提交 GitHub 时不要包含实际线索、联系方式或账号配置。

## 你会拿到什么

AI 会先报告值得跟进的需求，包含买家、国家、产品、数量、来源日期、截止日期、有效状态、供货匹配、联系方式、身份把握度和来源链接，并明确下一步需要确认什么。

| 优先级 | 含义 |
| --- | --- |
| A | 明确求购、仍开放、身份可靠、联系路径经过核验、供货匹配 |
| B | 明确求购，但有效性、身份、联系权限或供货条件仍有缺口 |
| C | 可能需求、身份较弱，或需要合作商才能执行 |

A/B/C 是跟进优先级，不是真实性或成交保证。完整规则见[证据与优先级](references/evidence.md)。已关闭、过期或供货不匹配的需求保留为历史，不进入当前跟进清单。

平台线索、身份待确认线索、合作商机会分别列出。行业新闻和项目投产等信号单独记录，不计入采购需求数量。渠道全部失败时，会报告无法完成检索，不会将其写成“没有需求”。

数据目录中的文件：

| 文件 | 内容 |
| --- | --- |
| `config.json` | AI 或用户保存的业务配置 |
| `leads.json` | 主线索库，由线索库脚本维护 |
| `leads.csv` | 可用 Excel 打开的导出表，复杂证据字段保存为 JSON 字符串 |
| `history.jsonl` | 线索更新前的记录，有更新时生成 |
| `channel_runs.jsonl` | AI 保存的渠道请求、核验与失败记录 |
| `signals.jsonl` | AI 保存的行业信号，有信号时生成 |

## 配套脚本

下面的命令均在本 Skill 目录执行。Windows 可以用 `py -3` 替换 `python`；其他环境使用实际可用的 Python 3 命令。

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

检查覆盖首次初始化、同键更新、历史保留、无效导入不改主库，以及网页成功/空响应/拦截处理。使用临时目录和本地测试服务器，不访问真实采购平台。

## 默认行为与边界

- 只检索公开资料、核验线索和维护本地数据，不自动注册、登录、发邮件或私信。
- 不猜邮箱，不把同名同国家或附件作者当作买家身份确认。
- 联系方式逐条保留来源；公开电话不自动标为 WhatsApp。
- 不继承旧版抓取脚本的页面正则与历史产出数字；批量抓取前需验证当前结构。
- “每日使用”描述的是工作频率，安装后不会自动创建定时任务。

买家回复确认仍在采购后，可根据实际回复更新确认状态，并保存日期及记录引用。只有用户明确授权，AI 才可以执行联系动作。

## 文件导航

- [SKILL.md](SKILL.md)：AI 执行入口。
- [assets/config.example.json](assets/config.example.json)：业务配置模板。
- [references/evidence.md](references/evidence.md)：证据、状态与评级规则。
- [references/channels.md](references/channels.md)：渠道选择及失败处理。
- [references/data.md](references/data.md)：线索字段与更新规则。
- `scripts/`：本地辅助脚本与离线回归检查。
