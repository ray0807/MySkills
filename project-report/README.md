# Project Report · 项目进度上报 Skill

让 AI 助手整理当前项目的进展，主动询问缺失信息，并通过 MCP 上传到项目管理中心。你的工作安排助手可以读取多个项目的状态，帮助你决定先做什么。

## 它能做什么

- 结合项目代码、文档、Git 状态和当前对话，总结已完成、正在做、待完成和待测试的工作。
- 主动补问项目目标、验收标准、截止时间、优先级、任务依赖和阻塞问题。
- 标记需要你亲自处理的任务，以及待确认的问题。
- 读取已有项目记录，更新完整快照并上传；管理中心同时保存上报历史。
- 引导你输入已有 API Key，或自动生成新的 Key。

它会先查资料，再分轮询问缺失信息，不会一次把所有问题丢给你。无法确认的内容会标记为待确认，不会编造进度或把未运行的测试标为通过。

## 使用场景

你同时维护多个项目，每个项目都有 AI 助手参与开发。调用这个 Skill 后，各项目的目标、进度和下一步行动就能汇总到同一个管理中心。

另一个负责安排工作的 AI 助手使用相同 API Key 查询全部项目，结合紧急程度、依赖和人工任务，为你安排工作。

**这个 Skill 负责整理和上报。项目数据由配套服务保存，工作安排由你的 AI 助手完成。**

## 使用前需要准备

1. 支持加载 `SKILL.md` 并执行本地脚本的 AI 客户端，例如 Codex。
2. Node.js 22 或更新版本。
3. 已部署的配套项目管理中心及其 HTTPS 地址。服务需要提供 `/mcp/report` 和 `/mcp/query` 两个 Streamable HTTP MCP 接口。

此文件夹只包含 Skill 和调用脚本，不包含服务端。配套服务采用 Cloudflare Workers + D1，可独立部署；服务部署时不需要设置用户 API Key。

## 安装与调用

将整个 `project-report` 文件夹放进 AI 客户端的技能目录，保留以下结构：

```text
project-report/
├── SKILL.md
├── README.md
├── references/
│   └── report.md
└── scripts/
    └── hub.mjs
```

Codex 通常使用 `~/.codex/skills/`。安装后，在目标项目的对话中调用：

```text
$project-report 帮我整理这个项目的进度，补问缺失信息并上报。
```

首次使用时，助手会询问服务地址，以及你要输入已有 Key 还是生成新 Key。之后会读取资料和已有记录，补问必要信息，整理并上传。

也可以要求：

```text
帮我设置这个项目的 API Key，我要使用已有 Key。
```

```text
帮我生成一个新的 API Key。
```

## API Key 规则

**API Key 就是用户身份，不需要注册或登录。**

- 相同 Key 对应同一组项目。要汇总多个项目，请在这些项目和工作安排助手中使用相同 Key。
- 换 Key 就换用户。旧数据仍属于旧 Key，不会自动迁移；保留旧 Key 才能继续访问旧数据。
- 新项目没有 Key 时，助手会让你选择输入已有 Key 或生成新 Key，不会擅自沿用其他项目的 Key。
- 每次设置、生成或更新 Key 后，都会提醒你立即复制并妥善保存。

自动生成的 Key 使用密码学随机数。自定义 Key 需为 24–256 个不含空格的可打印 ASCII 字符，建议使用随机 Key。

Key 保存在目标项目的 `.project-hub/config.json` 中，该目录会自动加入 `.gitignore`。文件包含明文 Key，应保存在自己的机器上，不要上传到 GitHub，也不要写入上报内容。持有 Key 的人可以读取和修改对应项目。

## 本地脚本

脚本只需要 Node.js，无需额外安装 npm 依赖。以下命令中的 `<Skill目录>` 和 `<项目目录>` 请替换为实际路径。

```powershell
# 自动生成 Key，保存到目标项目，并显示复制提醒
node "<Skill目录>/scripts/hub.mjs" generate --project "<项目目录>" --url https://<服务域名>

# 在本机终端交互输入已有 Key
node "<Skill目录>/scripts/hub.mjs" set --project "<项目目录>" --url https://<服务域名>

# 获取当前项目的已有记录
node "<Skill目录>/scripts/hub.mjs" get --project "<项目目录>"

# 上传 .project-hub/report.json 中的完整快照
node "<Skill目录>/scripts/hub.mjs" report --project "<项目目录>"
```

已有配置时，脚本不会直接覆盖 Key。明确要更换时，在 `generate` 或 `set` 命令后添加 `--replace`。更换意味着切换到另一个用户的数据空间。

生产服务地址必须使用 HTTPS；本地调试允许 localhost HTTP。

## 上报内容与注意事项

上报信息包括项目目标、范围、进度、任务、测试、阻塞、截止时间、下一步和需要人工处理的事项。更多背景与待确认问题通过 `metadata` 保存。详细字段见 [上报格式说明](references/report.md)。

每次上传是完整快照，同一项目 ID 会替换当前记录。Skill 会先读取旧记录，保留仍有效的信息；查询失败时不会直接当作新项目覆盖。上传成功后才会报告完成，失败时保留本地快照供重试。

完整执行流程见 [SKILL.md](SKILL.md)。
