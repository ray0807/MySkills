# b2b-inquiry-mcp · 1688 / 国际站 询盘与回复

在 BitBrowser 已登录的窗口里长时间运行询盘或回复任务。每次运行前选择一个角色：

| 角色 | 做什么 |
| --- | --- |
| `1688_buyer` 1688 买方 | 按目标产品搜索供应商、发询盘、跟进回复，统计回复与报价 |
| `1688_seller` 1688 卖方 | 处理买家消息，按业务政策自动回复，统计 |
| `alibaba_buyer` 国际站买方 | 同 1688 买方，在 alibaba.com |
| `alibaba_seller` 国际站卖方 | 同 1688 卖方，在国际站后台 |

```text
外层 AI（选角色、读页面、写询盘/回复、提取报价）
    ↓ MCP
本 MCP：发送限制（每日上限、随机间隔、防重复询盘）+ SQLite 台账 + 统计
    ↓ 复用 bitbrowser-jev-mcp：窗口白名单、拟人节奏、read_page
BitBrowser 已登录窗口（每个角色一个）
```

消息内容由外层 AI 依据配置中的 `buyer_goal` / `seller_policy` 撰写，本 MCP 不调用模型、不需要模型 Key。

## 安装

依赖同级目录的 [bitbrowser-jev-mcp](../bitbrowser-jev-mcp/README.md)，先按它的说明完成安装（Python 3.12+ 虚拟环境）。把两个目录放在同一个 skills 目录下；位置不同时设置 `BITBROWSER_JEV_MCP_DIR`。本 MCP 直接使用 bitbrowser-jev-mcp 的 `.venv`，无需另装依赖。

```powershell
..\bitbrowser-jev-mcp\.venv\Scripts\python.exe -X utf8 -B scripts/test_inquiry.py
```

## 配置

复制 [assets/config.example.json](assets/config.example.json) 为本目录 `config.json`（已被 Git 忽略），填写：

- `roles.*.profile_id`：四个角色各自的 BitBrowser 窗口 ID（窗口内已登录对应账号）。只有这里填写的窗口会被允许打开。`start_url` 为进入页面，默认值尚未在真实账号核验，可按实际改。
- `limits`：买方/卖方每日发送上限、两次发送的随机间隔（秒）、同一供应商同一产品的再询间隔（天）。
- `buyer_goal`：目标产品、数量、交付地、要问的问题、语言和单次联系供应商上限。
- `seller_policy`：公司、产品价格区间/起订量/交期、可承诺与不可承诺事项、超范围的处理方式。

可选环境变量：`B2B_INQUIRY_CONFIG`（配置路径）、`B2B_INQUIRY_DATA`（台账目录，默认 `runtime/data`）、`BITBROWSER_API_URL`、`BITBROWSER_PACING`（拟人节奏，默认开启）。

## MCP 接入

```json
{
  "mcpServers": {
    "b2b-inquiry": {
      "command": "C:/Users/PC/.codex/skills/bitbrowser-jev-mcp/.venv/Scripts/python.exe",
      "args": ["-X", "utf8", "C:/Users/PC/.codex/skills/b2b-inquiry-mcp/scripts/server.py"]
    }
  }
}
```

也可 `--transport streamable-http --port 8768`，地址 `http://127.0.0.1:8768/mcp`，仅本机。

## 工具

| 工具 | 用途 |
| --- | --- |
| `environment_check` / `list_roles` | 检查依赖与配置；列出角色、是否已配置窗口、今日发送数与上限 |
| `start_run(role, goal)` / `run_status` / `end_run` | 开始所选角色（打开其窗口）、查看进度、结束并返回本次统计；同一时间只运行一个角色 |
| `observe` / `read_page` / `click` / `fill` / `scroll` / `wait` / `navigate` / `press_key` / `list_tabs` / `switch_tab` / `new_tab` / `browser_history` / `screenshot` | 在当前角色窗口中操作，含拟人节奏；不需要传 session_id |
| `send_message` | 点击已观察到的发送按钮并记录；检查每日上限、发送间隔和重复询盘，未通过时不点击 |
| `confirm_sent` | 观察会话后标记送达或失败 |
| `record_inbound` | 记录对方消息，可附 price、currency、moq、lead_time、sample、shipping、payment、notes |
| `get_stats` / `export_csv` | 按角色统计；导出 UTF-8 CSV |

## 统计口径

每个角色：会话数、发出/收到消息数、询盘数、未确认送达数、联系对象数、已回复对象数、回复率、首次回复中位时长（分钟）、等待对方回复、等待我方回复，以及最近 20 条报价字段。时间为 AI 记录时刻，不是平台显示的发送时间；平台原始时间文字可存入 `seen_at_text`。

## 边界

- 发送只能经过 `send_message`；`press_key` 拒绝 Enter，避免绕过限制发送。
- 不下单、不付款、不确认合同；卖方回复不超出 `seller_policy`。
- 遇登录失效、验证码、风控或“操作频繁”提示立即停止，不绕过。平台规则与账号风险由使用者自行评估；默认上限偏保守。
- 台账含对方名称与消息原文，保存在本机 `runtime/data`，不提交 Git。

## 验证

5 项离线测试：配置默认值与校验、角色运行互斥、发送限制（重放、间隔、重复询盘、每日上限、被拒动作不记账）、统计（回复率、回复时长、报价字段过滤）与 CSV 导出、真实 MCP stdio 握手与 Enter 拦截。不打开真实窗口、不访问平台。

尚未在真实 1688 / 国际站账号上联调：各平台的消息中心入口、发送按钮与会话结构需首次运行时确认，`start_url` 默认值同样待核验。
