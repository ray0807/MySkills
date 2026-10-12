# 我的 AI 工作技能库

这里收集我为日常工作编写和维护的 AI Skills，把重复的工作流程整理成可复用的技能，让 AI 助手更方便地参与项目开发、信息整理和工作管理。

我会根据实际使用持续改进已有技能，也会陆续添加更多自己编写的 Skill。希望这些工具既方便自己的工作，也能为有类似需求的人提供参考。

## 现有技能

| Skill | 用途 |
| --- | --- |
| [project-report](project-report/README.md) | 整理项目进度，主动补问缺失的目标、验收和排期信息，通过 MCP 上报到项目管理中心，供 AI 助手汇总项目并安排工作。 |
| [verified-buy-leads](verified-buy-leads/README.md) | 查找 B2B 公开采购需求，核验需求有效性、买家身份、联系方式和供货匹配，维护带更新历史的本地线索库。 |

`project-report` 固定连接已部署的服务 [project.boomclaws.com](https://project.boomclaws.com)，无需选择或填写域名。API Key 在使用 Skill 时设置，安装时无需提供。

### 让 AI 助手读取已上报的项目

各项目用 `project-report` 上报后，负责安排工作的 AI 助手使用**同一个 API Key** 接入查询 MCP，即可读取全部项目。Key 建议放在环境变量 `PROJECT_HUB_API_KEY` 中，不要写进会提交到 Git 的配置文件。

Cursor（`~/.cursor/mcp.json`）：

```json
{
  "mcpServers": {
    "project-hub": {
      "url": "https://project.boomclaws.com/mcp/query",
      "headers": { "Authorization": "Bearer ${env:PROJECT_HUB_API_KEY}" }
    }
  }
}
```

Codex（`~/.codex/config.toml`）：

```toml
[mcp_servers.project-hub]
url = "https://project.boomclaws.com/mcp/query"
bearer_token_env_var = "PROJECT_HUB_API_KEY"
```

其他客户端按"远程 Streamable HTTP MCP + `Authorization: Bearer <API Key>` 请求头"配置。接入后可用的工具：

| 工具 | 参数 | 返回 |
| --- | --- | --- |
| list_projects | 无 | 全部项目详情，含进度、任务、待测试、阻塞和下一步 |
| get_project | `id`：项目 ID | 单个项目详情 |
| project_history | `id`；`limit`：1–100，默认 20 | 该项目最近的上报记录 |

配置完成后，直接对助手说：

```text
读取我所有项目的状态，按截止时间、优先级、依赖和阻塞，帮我排今天要做的事，并单独列出需要我亲自处理的任务。
```

不支持 MCP 的客户端也可以直接请求 HTTPS 接口：

```bash
curl -H "Authorization: Bearer $PROJECT_HUB_API_KEY" https://project.boomclaws.com/api/projects
```

返回空列表通常表示使用的 Key 与上报时不同。

## 如何使用

每个文件夹是一个独立 Skill，包含 `SKILL.md`，以及必要的脚本、参考资料和使用说明。

1. 阅读对应 Skill 的 README，了解用途、依赖和配置要求。
2. 将整个 Skill 文件夹放入 AI 客户端的技能目录。以 Codex 为例，通常为 `~/.codex/skills/`。
3. 按该 Skill 的说明，在 AI 对话中调用并完成必要配置。

不同 AI 客户端的 Skill 支持方式可能不同，请按客户端要求安装。部分技能需要 Node.js、MCP 接口或配套服务，具体以各技能说明为准。

## 给 AI Agent 的安装说明

用户要求安装本仓库的 Skill 时，请执行以下流程，而不是只告诉用户手动复制：

1. 获取仓库文件：已有本地克隆时直接使用；只有 GitHub 地址时，将该仓库克隆到临时目录。不要猜测仓库 URL。
2. 从用户指定的 Skill 目录读取 `README.md` 和 `SKILL.md`，确认依赖。用户没有指定具体技能时，让用户选择；不要自动安装所有技能。
3. 确认目标客户端的技能目录。对于 Codex，优先使用 `$CODEX_HOME/skills`，未设置 `CODEX_HOME` 时使用 `~/.codex/skills`。其他客户端使用其实际配置目录。
4. 复制整个 Skill 文件夹，包括脚本和参考资料。不要只复制 `SKILL.md`，也不要把仓库根目录当成一个 Skill 安装。
5. 如果目标已经存在，先检查已有内容；按用户的更新要求处理，保留本机配置和自定义修改，不直接覆盖。
6. 检查安装目录中的 `SKILL.md` 和引用文件均存在，按该 Skill 的 README 验证依赖。回复实际安装路径和调用方式；安装不等于执行技能，不要在安装期间生成 Key 或上传项目。

下面是 **Codex 首次安装** 的命令示例。请在本仓库根目录执行，并将 `project-report` 替换为用户选择的技能名。若使用完整项目仓库，则先进入其中的 `skills` 目录。

Windows PowerShell：

```powershell
$skillName = 'project-report'
$skillRoot = if ($env:CODEX_HOME) { Join-Path $env:CODEX_HOME 'skills' } else { Join-Path $env:USERPROFILE '.codex/skills' }
$source = (Resolve-Path -LiteralPath "./$skillName").Path
$target = Join-Path $skillRoot $skillName
if (Test-Path -LiteralPath $target) { throw '技能已存在，请先检查已有内容再更新。' }
New-Item -ItemType Directory -Path $skillRoot -Force | Out-Null
Copy-Item -LiteralPath $source -Destination $target -Recurse
Get-Item -LiteralPath (Join-Path $target 'SKILL.md')
```

macOS / Linux：

```bash
skill_name='project-report'
skill_root="${CODEX_HOME:-$HOME/.codex}/skills"
target="$skill_root/$skill_name"
if [ -e "$target" ]; then
  echo '技能已存在，请先检查已有内容再更新。'
else
  mkdir -p "$skill_root" && cp -R "./$skill_name" "$target" && test -f "$target/SKILL.md"
fi
```

每个 Skill 的 README 都应提供独立的 Agent 安装步骤、依赖检查和调用示例，方便单独分享与安装。

## 仓库结构

```text
skills/
├── README.md
└── project-report/
    ├── README.md
    ├── SKILL.md
    ├── references/
    └── scripts/
```

后续新增的技能会放在各自独立的目录中，并更新上方的技能列表。

## 持续更新

这些技能来自实际工作需求，会随着使用反馈不断调整。如果你发现问题或有改进建议，欢迎通过 Issue 交流。

配置技能时，请将 API Key 等敏感信息保存在本机私密配置中，不要提交到仓库。
