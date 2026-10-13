# store-launch-checker · 独立站上线验收

一套给不了解上线检查的人使用的 AI Skill。不是只看速度和死链，而是围绕 **能访问 → 能找到商品 → 能信任 → 能买 → 商家能收单履约 → 能观察问题** 检查正常电商业务闭环。

支持 Shopify、WooCommerce、自建商城；询盘型站点改用表单到邮箱/CRM 的闭环。AI 负责选择样本、操作浏览器、核验与解释；脚本采集公开证据并校验报告。不会凭没有看到错误就给“健康度 100”。

## 检查什么

| 维度 | 重点 |
| --- | --- |
| 访问与上线环境 | 域名、HTTPS、证书、跳转、密码墙、维护模式、正式/测试配置 |
| 商品 | 商品图片/描述、SKU、变体、库存、价格币种、促销与真实卖点 |
| 找商品与购物车 | 分类、搜索、筛选、加购、数量、删除、金额一致性 |
| 结算与支付 | 目标国家、访客结算、地址、运费/税费、成功/失败支付与订单状态 |
| 收单与履约 | 后台订单、通知/Webhook、库存、邮件、物流与取消/退款测试 |
| 信任与政策 | 商家身份、有效联系、售后、配送/退货/退款、目标市场隐私要求 |
| 移动与可访问性 | 按钮遮挡、浮层、输入错误、键盘/焦点、设备与浏览器差异 |
| SEO | 索引限制、标题/描述、canonical、sitemap、内链、产品结构化数据、多语言 |
| 性能 | LCP/INP/CLS、实验室与字段数据、样本与测量条件 |
| 数据与渠道 | 购买/询盘埋点、金额/货币/交易去重、同意行为、适用时的 Shopping feed |
| 运营与被动安全 | 明显数据暴露、安全头线索、续期、异常负责人、备份与恢复 |

完整条目和逐项验收方法见 [checklist.md](references/checklist.md)。不是所有项目都适用于每家店：单语站不强求 hreflang、不投 Shopping 不强求 Merchant Center、没有优惠活动不强求优惠码。

## 快速开始

安装整个目录到 AI 客户端技能目录，保留 scripts、references、assets。通用方法见[技能库首页](../README.md#如何使用)。对 AI 说：

```text
使用 store-launch-checker 检查 https://我的商城域名。
这是准备上线的电商独立站，优先检查能否正常购买及 SEO 上线配置。
请先检查公开页面、桌面和移动体验，给出阻断项、未验证项及具体修复方法。
不要真实付款、创建真实订单或修改后台。
```

提供 URL 就可以开始，AI 会从页面判断已有信息，只补问必要的市场、环境和测试授权。可以后续说：“测试环境和测试支付已配置，我授权在测试账户创建订单，收件人是……”，再验证交易闭环。

## 工具要求

- **公开采集和报告脚本**：Python 3.10+，只有标准库，兼容 Windows/macOS/Linux，无需付费 API。
- **浏览器实测**：AI 客户端的浏览器工具、Playwright 或已配置的浏览器 MCP，至少能读取渲染内容和操作页面。可用 bitbrowser-jev-mcp，但不是安装依赖。
- **性能**：可用 Lighthouse/PSI/CrUX；没有工具/Key 则明确未测，不编造指标。
- **私有闭环**：用户授权的后台、支付测试模式、收件箱、日志、分析调试工具。缺少连接时先完成其他检查，并提示补配置。

安装此 Skill 不会自动安装浏览器、不需要先开一组付费账号。后台或某工具缺少 Key 时只提示缺项，用户配置完成后才使用；现有有效配置复用。

## 可运行脚本

在本 Skill 目录执行：

先建立完整计划（电商 52 项；询盘站另加 4 项替代链路），避免漏掉不了解的条件：

```powershell
python -X utf8 scripts/new_plan.py --site-url https://example.com --environment unknown --output D:/store-check/results.json
```

计划不是检查结果，全部适用项从 not_tested 开始。AI 再按实际证据更新 results.json；条件不适用时写明理由，不静默删除。有自然搜索目标时需结合正式环境把关键索引检查设为门槛。

```powershell
python -X utf8 scripts/public_probe.py --url https://example.com --page https://example.com/products/sample --output D:/store-check/public-evidence.json
```

示例网址仅演示命令，请换成目标站。默认最多 12 个页面、40 次主动请求、请求间隔 0.25 秒；可用 --max-pages、--max-requests、--delay 调整。--page 可重复指定分类、商品、政策等代表页面。--check-images 加做同站图片 HTTP 检查。请求超时 10 秒，429 停止采集。

脚本读取主页/样本、robots.txt、常用 sitemap.xml、元标签、canonical、hreflang、JSON-LD 语法、同站链接与 HTTPS 证书。默认不跟随带查询参数或看起来会登出、加购、下单等的自动发现链接；显式 --page 是用户指定读取。自动发现页面尊重 robots，robots 阻止的指定样本仍可检查以定位配置。

只采集源 HTML，不执行 JS、不支付、不发邮件。HTTP 耗时不是 LCP/TTFB，JSON-LD 语法正常不代表富媒体资格通过；图片返回 200 不等于正确显示。第三方 CDN/外链、其他 sitemap 位置、索引文件/gzip 和站内 iframe 等需后续浏览器/专门工具检查。预算不含重定向跳数和一次 TLS 握手。

AI 结合所有实测证据按 [报告格式](references/reporting.md) 整理 results.json，然后运行：

```powershell
python -X utf8 scripts/build_report.py --input D:/store-check/results.json --output-dir D:/store-check/report
```

生成 report.md 与 report.json。报告校验器要求检查计划与证据，缺少的计划项自动记 not_tested；不能把缺结果或没有权限变成通过。它校验记录结构，无法证明伪造的证据真实，仍需 AI 和用户核验来源。

## 结论怎么读

| 结论 | 含义 |
| --- | --- |
| blocked | 有已证实的上线门槛失败或 critical 问题 |
| verification_required | 没发现上述失败，但关键环节尚未验证，不能确认上线准备充分 |
| ready_with_issues | 门槛在检查范围内通过，仍有质量问题或非门槛未测项 |
| ready_in_scope | 既定计划的适用项有证据通过，仅限样本、市场、时间与测试条件 |

不生成没有依据的全站健康评分。覆盖数量与检查结果分开：公开采集全成功，支付未测，仍是 verification_required。测试站 noindex 可正确；正式核心页面意外 noindex 对自然搜索目标才是相关问题。

## 和常见巡检方案的区别

- 当前核心指标用 LCP/INP/CLS，不继续把 FID 当当前标准。
- Google 不使用 meta keywords，缺它不是 SEO 故障。
- canonical、sitemap、结构化数据与 Shopping 账户按目的和场景判断，不全部强制。
- 付款页和感谢页不能证明支付、订单、通知、库存、邮件的闭环。
- Cookie 弹窗存在、Lighthouse 高分、政策页有链接都不足以证明全面合规。
- 新站没有真实用户性能数据或尚未收录，先说明阶段与证据限制，不误判技术失败。

依据与官方链接见 [sources.md](references/sources.md)，涉及国家/产品/支付规则时使用当前官方资料复核。

## 安全与测试

默认检查和提出建议，使用隔离会话做可逆购物车检查；不完成真实订单/付款、不改站、不扫描后台弱点或压力测试。测试订单、询盘发送、退款/履约模拟需要明确测试范围。报告不包含密钥、Cookie、完整客户资料或卡号。

```powershell
python -X utf8 -B scripts/test_checker.py
```

离线检查使用本机测试服务器和固定报告，验证采集范围/预算、robots 与操作链接跳过、解析及报告结论；不检查真实商城、不产生订单。真实网站的浏览器、支付和后台验收须使用该站点进行。

## 文件导航

- [SKILL.md](SKILL.md)：执行流程。
- [配置模板](assets/config.example.json)：可选业务/样本配置，不含密钥。
- [检查清单](references/checklist.md)：业务必要条件与验收方法。
- [浏览器和订单](references/browser-and-orders.md)：真实路径验证与停止条件。
- [SEO 和性能](references/seo-performance.md)：指标和配置判断。
- [报告规则](references/reporting.md)：证据、严重性、覆盖与上线结论。
- [官方资料](references/sources.md)：调研来源与适用范围。
