# 搜索渠道预检：验证实际返回，不只看工具成功

启动正式查询前小样本预检，仅使用宿主真实已有工具。不要求用户开接口、提供 Key、登录账号或付费。截图里某引擎可用不代表当前环境或未来一定可用，不固定首选厂商。

## 检查步骤

1. 盘点可调用的搜索工具及已有网页/浏览器能力。先测试默认工具；可用即正式搜索，不必为了测试把所有搜索引擎跑一遍。
2. 对 Facebook、Instagram、YouTube 分别做一个宽松对照查询，例如 site:facebook.com 产品词，不加多个引号、国家和采购限定。无结果时用另一个已知相关的宽泛术语复测，避免把产品冷门误判成工具坏了。
3. 记录搜索**实际返回的外部结果 URL**，不拿标题、摘要里出现 facebook.com 当域名命中，不把广告/搜索导航混入分母。同域子域算命中，facebook.com.example.org 不算。搜索跳转链接用工具返回的真实目标地址；无法解析的重定向标未解析，不伪装成目标链接。
4. 每个样本尽量取至少 5 个不同结果。5 个以上且目标域占比至少 80% 标 usable-sample；混入明显异域结果标 site-filter-unreliable，表示此样本定向过滤不可靠，不武断断言工具一定吞了 site:。少于 5 个是 inconclusive-small-sample；空结果是 inconclusive-empty，不是平台没客户。重复同一 URL 不扩充样本。
5. 对异常查询去掉复杂操作符再复测一次；仍异常才换已有的替代搜索来源，或在当前可用网页工具内访问其公开搜索结果页（例如 DuckDuckGo HTML，前提是实际可访问并解析）。不假设存在 browser.search、HTTP 或特定引擎接口；没有替代工具就保留范围限制，不要求用户配接口。
6. 返回阻断页、人机验证、错误时分别记 blocked/captcha/error，不能因为 HTTP 200 就记成功，也不能靠零 URL 自动猜验证码。验证码/登录墙不绕过，切换可用来源；所有路线失败则如实交付已有名单与未覆盖范围。

一次 usable-sample 只表明链接发现可用，不证明能读社媒内部、评论或私密群，不证明产品相关性和买家意图正确。进入正式查询后仍抽查实际域名、产品相关性及买方口吻；某平台通过不等于其他平台通过。结果明显跑偏时重新预检，缓存按 provider+target_domain+query语法区分，不永久记引擎有效或无效。

## 离线辅助检查

agent 收集实测结果到数组后可运行：

`python scripts/search_probe.py --input <探测JSON> --output <数据目录>/search-capabilities.json`

示例（占位链接，不能当实测结果）：

```json
[{"provider":"实际工具/来源名", "query":"site:facebook.com 产品词", "target_domain":"facebook.com", "checked_at":"2026-10-15T12:00:00+08:00", "response_state":"ok", "result_urls":["https://www.facebook.com/example"]}]
```

脚本只核对已有结果、统计域名命中并标记样本状态，不联网、不代替 agent 搜索，不自动识别人机验证。response_state 必须根据实际响应填写。索引链接保存逻辑和用户输出不变：只交付客户名单.csv，不额外交付预检报告或要求用户理解工具配置。

search-capabilities.json 是内部运行记录，含 provider、query、target_domain、checked_at、result_urls、response_state、status、sample_size、target_count、target_ratio、invalid_count；另由 agent 记录切换原因、备选来源及后续正式查询表现。全路线无结果要区分引擎失败、样本不足和真实查询零命中。
