# bitbrowser-jev-mcp · 指纹浏览器 AI 执行脚手架

一个独立 Skill + Python MCP 服务：AI agent 读取页面并决定每一步，脚手架执行点击、输入和滚动，BitBrowser 提供带已有指纹和登录状态的窗口。也可把阶段目标委托给 Jev Ultrafast。业务判断由 AI 完成，不写死某个平台的规则。

```text
AI agent（观察、规划、每步判断、结果核验）
    ↓ MCP：observe / click / fill / scroll ...
本地 MCP 服务（元素校验、去重、持久标签）
    ↓ BitBrowser /browser/open → data.ws
指纹窗口执行 → 新页面证据 → AI 再判断

可选：submit_goal → Jev 判断动作 → get_job 返回结果
```

参考了 Claws 的 BitBrowser 驱动接口，但不依赖 Claws、Stagehand 或 Electron。无需修改 Jev 上游源码：按作业加载隔离模块，仅替换浏览器连接层，复用原来的观察、动作和模型策略。

## 安装

需要 Python 3.12+、Git、已启动且启用本地 API 的 BitBrowser。逐步模式无需 TypeSafe/文本模型密钥，使用外层 AI 自己的判断能力；默认 Jev 目标模式需要 TYPESAFE_API_KEY；TEXT_MODEL_API_KEY 仅在执行文字输入时需要。安装和离线测试不会调用模型。

复制整个 Skill 目录到 AI 客户端的技能目录，安装通用说明见[技能库首页](../README.md#如何使用)。在本目录执行：

```powershell
powershell -NoProfile -File scripts/setup.ps1 -Python python
```

脚本建立 `.venv`、获取上游到 `vendor/jev-ultrafast`、安装依赖并运行离线检查。上游固定为已验证版本 `1231850a0bf1a0c0341fe408ef1668dbbfdfac46`；已有 vendor 版本不同会停止，不覆盖改动。用户机器的 Python 不在 PATH 时把 `-Python` 替换为绝对路径。

macOS / Linux 手动安装：

```bash
python3.12 -m venv .venv
git clone https://github.com/browser-use/jev-ultrafast.git vendor/jev-ultrafast
git -C vendor/jev-ultrafast checkout --detach 1231850a0bf1a0c0341fe408ef1668dbbfdfac46
.venv/bin/python -m pip install -r requirements.txt -e vendor/jev-ultrafast
.venv/bin/python -X utf8 -B scripts/test_scaffold.py
```

上述手动命令适用于首次安装；已有目录时先检查，不直接覆盖。上游代码与虚拟环境不提交到本 Skill 仓库；源码获取地址与版本保留在安装说明中。上游 MIT 许可证随克隆保留，见[上游项目](https://github.com/browser-use/jev-ultrafast)。

## 配置

Windows PowerShell（仅作用于当前终端与它启动的进程）：

```powershell
$env:BITBROWSER_API_URL = 'http://127.0.0.1:54345'
$env:BITBROWSER_ALLOWED_PROFILES = '你的窗口ID1,你的窗口ID2'
```

以下只在需要委托 Jev 目标执行时配置：

```powershell
$env:TYPESAFE_API_KEY = '你的TypeSafe密钥'
$env:TEXT_MODEL_API_KEY = '你的文本模型密钥'
$env:TEXT_MODEL_BASE_URL = '你的OpenAI兼容接口地址/v1'
$env:TEXT_MODEL = '你的文本模型名'
```

窗口 ID 从 BitBrowser 获取，不是窗口序号。白名单为空时不能执行；列表只返回允许窗口的 id、名称、序号，不返回 Cookie、账号密码或代理。模型密钥通过环境变量传入，不提交 Git。客户端直接启动 stdio 时也要配置它的环境变量；终端设置不会自动传给已运行的桌面客户端。

启动命令中的 `-X utf8` 必须保留，避免中文 Windows 默认编码导致 Jev 读取源码资源失败。上游导入 Browser Harness 时创建的运行目录默认保存在本脚手架 `runtime/`，不会启动它的 Chrome 守护进程。

可选 `TYPESAFE_MODEL` 和 `TEXT_MODEL_REASONING` 跟随上游模型配置。BitBrowser 与 CDP 地址限本机，不控制远程任意调试端口。

## MCP 接入

推荐 stdio，在当前目录运行：

```powershell
.venv/Scripts/python.exe -X utf8 scripts/server.py
```

AI 客户端的通用 stdio 配置结构（占位路径需改成安装后的绝对路径，字段以客户端支持为准）：

```json
{
  "mcpServers": {
    "bitbrowser-jev": {
      "command": "D:/skills/bitbrowser-jev-mcp/.venv/Scripts/python.exe",
      "args": ["-X", "utf8", "D:/skills/bitbrowser-jev-mcp/scripts/server.py"],
      "env": {
        "BITBROWSER_ALLOWED_PROFILES": "你的窗口ID"
      }
    }
  }
}
```

逐步模式使用上面的最小配置即可；需要 submit_goal 时，再给客户端环境加入 TypeSafe 和文本模型配置。

也支持本机 Streamable HTTP：

```powershell
.venv/Scripts/python.exe -X utf8 scripts/server.py --transport streamable-http --port 8767
```

MCP 地址：`http://127.0.0.1:8767/mcp`。这是 MCP 协议服务，不能按普通 REST `/submit` 接口调用。只绑定本机、没有公网鉴权；不要经代理暴露公网。

## 两种执行模式

**逐步控制（调试/明确要求时）**：AI 是大脑，工具是手脚。AI 判断“活跃”“值得联系”等条件，直接提供输入文字，工具只执行观察过的动作，不调用 Jev 的决策模型。LinkedIn、Facebook、YouTube 等只是可能使用的页面，不是内置业务模块，也没有承诺这些站点的具体流程已经实测。

**目标执行（默认）**：外层 AI 提交阶段目标，Jev 自行观察和选动作。只需 Jev 决策 Key 即可开始不含输入的任务；遇输入且缺文本模型 Key 会明确阻塞，不静默切回外层逐点击控制。两种模式互斥：先 close_session 才可 submit_goal；活动 Jev 作业结束后才能 open_session。

## AI agent 怎么用

对助手说：

```text
使用 bitbrowser-jev-mcp。
先检查逐步模式环境，在我允许的【窗口ID】执行。
请根据【任务目标】自行规划步骤，读取页面后决定动作，不写死平台流程。
每个动作执行后重新观察，核验结果再继续。
只查公开资料，不发消息、不报价、不购买，也不要修改窗口设置。
```

| 工具 | 参数 / 用途 |
| --- | --- |
| `environment_check` | 无参数；检查依赖、凭据存在性与白名单，不调用模型 |
| `list_profiles` | page=0、page_size=20；查看当前页允许窗口 |
| `submit_goal` | profile_id、url、goal；可选 max_steps=12、timeout_seconds=120 |
| `get_job` | job_id；返回状态、当前进度、最终页面证据及动作摘要 |
| `cancel_job` | job_id；请求取消，当前模型/动作结束后生效 |
| `open_session` | profile_id、url；建立跨步骤保留状态的标签，不要求执行器模型密钥 |
| `observe` | session_id；返回可见文字、动作列表和 snapshot_id |
| `read_page` | session_id；可选 max_scrolls=30、max_chars=60000；向下滚动并返回去重后的整页文字（评论、列表），只发送滚动，结束后须重新 observe |
| `click` / `select` / `scroll` | session_id、snapshot_id、action_id、request_id；执行对应观察动作 |
| `fill` | 同上，加 text；输入由 AI 提供 |
| `wait` | session_id、snapshot_id、request_id；短暂等待后再次观察 |
| `navigate` | session_id、snapshot_id、url、request_id；当前标签导航 |
| `press_key` | session_id、snapshot_id、key、request_id；支持 Enter、Tab、Escape、Backspace 和四个方向键 |
| `list_tabs` / `switch_tab` | 列出窗口页面，按 target_id 切换；切换后重新观察 |
| `new_tab` | session_id、snapshot_id、url、request_id；新建并切换标签，保留其他页 |
| `browser_history` | session_id、snapshot_id、direction、request_id；direction 为 back / forward |
| `screenshot` | session_id；返回 MCP 图片供 AI 查看 |
| `close_session` | session_id；只关闭脚手架自建标签并断开连接 |

提交返回 job_id，执行在后台进行；每次只允许一个活动任务，新提交在有活动任务时被拒绝。轮询间隔建议几秒。步骤上限 100，预算上限 600 秒；预算在每个 tick 前检查，当前网络请求可能使实际时长超出预算。

状态包括 queued、running、cancelling、cancelled、done、blocked、budget_exceeded、error。`done` 仅代表 Jev 判断完成，必须根据 URL/页面证据独立核验；所有最终执行结果带 verification=required。

逐步模式始终保留当前标签，输入、菜单和表单状态可连续使用；close_session 时仅关闭自建标签，切换到用户已有标签也不会把它关闭。目标执行模式每阶段创建新标签，结束关闭该标签，保留窗口与用户原有标签。登录状态共享所选 profile，但上阶段尚未提交的表单状态不会跨新标签保留。需要连续表单操作时合并为一个有明确停止条件的目标，不能假装下一阶段可继承原标签。

## 能力边界

- 不改指纹、代理、视口，不创建或删除窗口。
- 支持常见 HTML/ARIA 控件、基本按键及显式标签切换。弹窗如果成为可列出的 page target 可以切换；仍不保证 iframe、Shadow DOM、文件上传、复杂键盘组件和嵌套滚动。
- AI 负责高层编排，Jev 负责动作；目标文本不是只读隔离机制，服务不会可靠拦住所有“提交”操作。
- 发布、联系客户、付款和删除等必须已有用户授权；失败后不能自动重跑写入目标。
- 任务记录在内存，服务重启会丢失记录；已经执行的网页操作不会撤销。取消同样不能回滚动作。
- 运行信息可能包含已登录页面内容，本地使用、妥善处理，不上传源码仓库。

## 验证

```powershell
.venv/Scripts/python.exe -X utf8 -B scripts/test_scaffold.py
```

离线检查涵盖本机地址限制、模拟 BitBrowser API、窗口白名单、单作业排他与取消、实际 Jev 模块隔离及仅关闭自建标签、真实 Jev Agent 在模拟策略下的完成证据。没有付费模型调用，也不打开真实用户窗口。

另外覆盖 stdio 与 Streamable HTTP 的真实 MCP 握手、工具发现及配置缺失拒绝执行。当前共 10 项测试；测试 HTTP 服务只临时绑定本机随机端口，完成后退出。

真实联调仍需用户提供允许的窗口 ID；目标模式还需模型配置，在测试页面执行点击/输入/下拉等目标，确认真实 API 返回结构和浏览器兼容性。未完成该联调前，不宣称已验证生产网页自动化。


## 逐步调用示例

```text
open_session(profile_id, url) → session_id
observe(session_id) → snapshot_id + actions
AI 阅读页面，选择一个 kind=click 的 action_id
click(session_id, snapshot_id, action_id, request_id="唯一动作编号")
observe(session_id) → 新快照、执行后的页面
AI 核验结果并选择下一步，最终 close_session(session_id)
```

动作编号不能凭记忆生成，必须取自本次 actions。每次输入消耗快照；新动作重新 observe。同一 request_id 与相同参数重发只返回原记录，不执行两遍；换参数却复用编号会拒绝。输入超时返回 outcome_unknown，不意味着没执行。新编号不能用于绕过核验盲目重试。

逐步工具目前共有 16 个，加上环境、窗口和 Jev 作业工具，总计 21 个 MCP 工具。

逐步环境检查用 step_ready；goal_ready 表示 Jev 目标模式也已具备凭据。ready 保留为目标模式兼容字段，不能用它要求逐步模式填写模型密钥。

## 缺少密钥时

Jev 目标模式需要 TYPESAFE_API_KEY 与 TEXT_MODEL_API_KEY。环境检查会返回 missing_credentials 和配置提示；AI 只询问缺少的项目，等用户填写到本机 MCP 环境并重启服务后再执行。有效配置不重复询问，错误密钥需更新。逐步控制不使用这两个模型，因此无需为它填写 Jev 密钥。

### 2026-10-15 本机实测

在独立 BitBrowser 测试配置中，通过真实 stdio MCP 验证观察、输入、重复请求去重、点击、页面结果、截图、新建与切换标签及状态保留。修复了后台标签接受 CDP 输入但实际未生效的问题：任务标签在初始化及动作前激活。自建测试标签清理成功，配置窗口保留。本轮未调用付费模型，Jev 目标模式尚未完成真实模型验证。此结果不代表所有网站均已验证。

### 2026-10-15 亚马逊评论调研实测

- Jev 目标模式适合点击、导航类阶段；“在页面中找到某个区域并抄录文字”这类读取目标，两次耗尽 12 步预算仍无结果，第三次未执行动作即 blocked。读取页面内容应改用逐步模式 open_session → read_page，一次调用得到整页去重文字，不消耗模型。
- observe 只返回当前视口文字，长页面需反复滚动；为此新增 read_page。首次真实调用暴露懒加载导致滚动被判“页面已变化”，已改为重新观察后继续（最多连续 5 次）；修复后的版本仅通过离线测试，真实页面复测待有可用窗口时进行。动作列表的链接不含 href，打开某一商品需在 observe 结果中按标签点击。
- 亚马逊未登录时，完整评论列表（product-reviews，含按星级筛选）跳转登录页；商品页只公开约 8 条 Top reviews 和 AI 汇总，且文字中不含单条星级。需要差评样本时请用户在该窗口手动登录，不代为登录或绕过。

默认采用“外层AI规划→Jev执行→外层AI验收”。get_job 每5–10秒查进度，避免反复传回全页。goal_ready 不再要求文本模型 Key；text_input_ready 单独表示输入能力。真实付费模型执行尚待验证，已有本机测试仅证明逐步模式链路。
