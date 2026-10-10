# Project Report · 项目进度上报 Skill

让 AI 助手整理当前项目的进展，主动询问缺失信息，并通过 MCP 上传到项目管理中心。你的工作安排助手可以读取多个项目的状态，帮助你决定先做什么。

## 它能做什么

- 结合项目代码、文档、Git 状态和当前对话，总结已完成、正在做、待完成和待测试的工作。
- 主动补问项目目标、验收标准、截止时间、优先级、任务依赖和阻塞问题。
- 标记需要你亲自处理的任务，以及待确认的问题。
- 读取已有项目记录，更新完整快照并上传；管理中心同时保存上报历史。
- 引导你输入已有 API Key，或自动生成新的 Key。

只整理当前项目的目标、进度与工作任务，不主动检查 GitHub、处理嵌套仓库、移动目录或清理旧部署。上报完成只给出简短结果，不展示完整 JSON 和过程日志。

它会先查资料，再分轮询问缺失信息，不会一次把所有问题丢给你。无法确认的内容会标记为待确认，不会编造进度或把未运行的测试标为通过。

## 使用场景

你同时维护多个项目，每个项目都有 AI 助手参与开发。调用这个 Skill 后，各项目的目标、进度和下一步行动就能汇总到同一个管理中心。

另一个负责安排工作的 AI 助手使用相同 API Key 查询全部项目，结合紧急程度、依赖和人工任务，为你安排工作。

**这个 Skill 负责整理和上报。项目数据由配套服务保存，工作安排由你的 AI 助手完成。**

## 使用前需要准备

1. 支持加载 `SKILL.md` 并执行本地脚本的 AI 客户端，例如 Codex。
2. Node.js 22 或更新版本。
3. 可访问配套项目管理中心 [project.boomclaws.com](https://project.boomclaws.com)。Skill 的服务地址已固定，无需选择或填写域名。

默认上报 MCP：`https://project.boomclaws.com/mcp/report`；查询 MCP：`https://project.boomclaws.com/mcp/query`。工作安排助手也可携带相同 Key 请求 `GET https://project.boomclaws.com/api/projects` 获取全部项目。

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

首次使用时，助手只询问你要输入已有 Key 还是生成新 Key，不询问或确认域名。之后会读取资料和已有记录，补问项目所需信息，整理并上传。

也可以要求：

```text
帮我设置这个项目的 API Key，我要使用已有 Key。
```

```text
帮我生成一个新的 API Key。
```

## 给 AI Agent 的安装说明

当用户要求安装此 Skill 时：

1. 从本地仓库或用户提供的 GitHub 仓库获取完整 `project-report` 文件夹，读取 `SKILL.md`。本仓库的根目录就是技能集合，源路径为 `<仓库目录>/project-report`；在完整项目仓库中，源路径为 `<项目仓库>/skills/project-report`。
2. 确定客户端技能目录。Codex 使用 `$CODEX_HOME/skills`；未设置 `CODEX_HOME` 时使用 `~/.codex/skills`。复制后目标应为 `<技能目录>/project-report/SKILL.md`，不要额外嵌套一层同名目录。
3. 复制整个文件夹。若同名技能已存在，先检查已有版本和用户的更新要求，保留本机自定义内容。
4. 确认 `SKILL.md`、`references/report.md` 和 `scripts/hub.mjs` 均存在。运行 `node --version` 检查 Node.js 22 或更新版本，并运行 `node --check <安装目录>/scripts/hub.mjs` 检查脚本。
5. 回复安装路径和 `$project-report` 调用示例。若依赖未满足，明确说明。若当前会话尚未识别新技能，可让用户开启新会话再调用。

Windows PowerShell 首次安装示例（将源目录替换为实际下载或克隆位置）：

```powershell
$source = (Resolve-Path -LiteralPath '<仓库目录>/project-report').Path
$skillRoot = if ($env:CODEX_HOME) { Join-Path $env:CODEX_HOME 'skills' } else { Join-Path $env:USERPROFILE '.codex/skills' }
$target = Join-Path $skillRoot 'project-report'
if (Test-Path -LiteralPath $target) { throw '技能已存在，请先检查再更新。' }
New-Item -ItemType Directory -Path $skillRoot -Force | Out-Null
Copy-Item -LiteralPath $source -Destination $target -Recurse
Get-Item -LiteralPath (Join-Path $target 'SKILL.md'), (Join-Path $target 'references/report.md'), (Join-Path $target 'scripts/hub.mjs')
node --version
node --check (Join-Path $target 'scripts/hub.mjs')
```

macOS / Linux 首次安装示例：

```bash
source_dir='<仓库目录>/project-report'
skill_root="${CODEX_HOME:-$HOME/.codex}/skills"
target="$skill_root/project-report"
if [ -e "$target" ]; then
  echo '技能已存在，请先检查再更新。'
else
  mkdir -p "$skill_root" && cp -R "$source_dir" "$target" &&
    test -f "$target/SKILL.md" && test -f "$target/references/report.md" &&
    node --version && node --check "$target/scripts/hub.mjs"
fi
```

**安装时不需要 API Key，也不要生成 Key 或上传项目。** 服务固定为 `https://project.boomclaws.com`，不要询问域名。用户首次调用时，只询问输入已有 Key 或生成新 Key。客户端不支持加载 Skills 时，不要声称已安装成功；可说明本地脚本调用方式。

## API Key 规则

**API Key 就是用户身份，不需要注册或登录。**

- 相同 Key 对应同一组项目。要汇总多个项目，请在这些项目和工作安排助手中使用相同 Key。
- 换 Key 就换用户。旧数据仍属于旧 Key，不会自动迁移；保留旧 Key 才能继续访问旧数据。
- 新项目没有 Key 时，助手会让你选择输入已有 Key 或生成新 Key，不会擅自沿用其他项目的 Key。
- 每次设置、生成或更新 Key 后，都会提醒你立即复制并妥善保存。
- 新生成 Key 会直接在聊天回复中以完整、可复制的代码块展示，不需要去配置文件中寻找。沿用已有 Key 的普通上报不会重复展示或提醒。

自动生成的 Key 使用密码学随机数。自定义 Key 需为 24–256 个不含空格的可打印 ASCII 字符，建议使用随机 Key。

Key 保存在目标项目的 `.project-hub/config.json` 中，该目录会自动加入 `.gitignore`。文件包含明文 Key，应保存在自己的机器上，不要上传到 GitHub，也不要写入上报内容。持有 Key 的人可以读取和修改对应项目。

## 本地脚本

脚本只需要 Node.js，无需额外安装 npm 依赖。以下命令中的 `<Skill目录>` 和 `<项目目录>` 请替换为实际路径。

```powershell
# 自动生成 Key，保存到目标项目，并显示复制提醒
node "<Skill目录>/scripts/hub.mjs" generate --project "<项目目录>"

# 在本机终端交互输入已有 Key
node "<Skill目录>/scripts/hub.mjs" set --project "<项目目录>"

# 获取当前项目的已有记录
node "<Skill目录>/scripts/hub.mjs" get --project "<项目目录>"

# 上传 .project-hub/report.json 中的完整快照
node "<Skill目录>/scripts/hub.mjs" report --project "<项目目录>"
```

已有配置时，脚本不会直接覆盖 Key。明确要更换时，在 `generate` 或 `set` 命令后添加 `--replace`。更换意味着切换到另一个用户的数据空间。

脚本固定连接 `https://project.boomclaws.com`，无需传入 `--url`。旧配置中的地址不参与选择，生成或设置 Key 时会写入固定服务地址。

## 上报内容与注意事项

上报信息包括项目目标、范围、进度、任务、测试、阻塞、截止时间、下一步和需要人工处理的事项。更多背景与待确认问题通过 `metadata` 保存。详细字段见 [上报格式说明](references/report.md)。

每次上传是完整快照，同一项目 ID 会替换当前记录。Skill 会先读取旧记录，保留仍有效的信息；查询失败时不会直接当作新项目覆盖。上传成功后才会报告完成，失败时保留本地快照供重试。

完整执行流程见 [SKILL.md](SKILL.md)。
