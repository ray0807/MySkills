# 提交后自动上报

## 授权和安装

用户明确要求后，首次确认目标仓库和 Key。已有有效 Key 经用户同意可直接复用，缺少时提供新建/复用选择；之后持续复用，无交互、不输出 Key、不追问人工状态。普通手动上报保留访谈。

`node scripts/auto-report.mjs enable --project <仓库根目录>` 安装本机 post-commit，不提交代码、不上传旧提交。先设置 Key，并保存 `.project-hub/report.json` 初始基线（匹配 id/name 与已知项目事实）。远程已存在记录优先合并远程，不存在才使用本地基线。

已有 post-commit/core.hooksPath 时自动安装停止，不覆盖。检查原钩子后，在其正常执行路径接入 `node <skill绝对路径>/scripts/auto-report.mjs enqueue --project <仓库根目录>`，并在 config.autoReport 记录 enabled=true 与用户授权。不要在 exit 后盲目追加，不改全局 hooksPath。

## AI 摘要

暂存代码后、提交前，AI 根据真实实现、测试和用户反馈写 `.project-hub/summary-input.json`，执行：
`node scripts/auto-report.mjs prepare --project <仓库根目录> --input <摘要文件>`。

prepare 用 git write-tree 记录暂存区树和当前父提交，不修改暂存内容或创建提交。摘要只应用于匹配的下一次提交；修改暂存内容后重新 prepare。没有匹配摘要只上传 Git 事实，不能凭 commit 自动标任务完成或测试通过。

输入是部分更新：
```json
{
  "completed": ["有证据支持的完成事项"],
  "pendingTests": ["待实际使用验证"],
  "remove": {"pending": ["明确已完成的旧条目"]},
  "tasks": [{"id": "stable-task-id", "title": "任务标题", "status": "done", "testResult": "实际测试及结果"}],
  "testSummaryAppend": "实际检查日期、命令与结果，和人工反馈分开",
  "openQuestions": ["待确认事项"]
}
```

可明确更新 name/description/goal/status/priority/deadline；completed/pending/pendingTests/blockers/nextActions 追加去重，删除使用 remove；tasks 按 ID 合并未提供字段；openQuestions 追加。自动模式不改 progress 数字、不覆盖任意 metadata。不确定人工事项留待确认。

钩子不会唤醒 AI 模型或理解代码。AI 客户端加载 skill 后在提交前保存摘要；纯终端/未加载 skill 的客户端提交仍记录编号、标题、时间、分支和文件名。不上传代码 diff、作者邮箱、密钥或整个工作区。

## 队列和对账

钩子先写 queue/<commit>.json，再启动隐藏后台 Node worker，立即返回；网络失败不影响已创建的提交。Node 不可用/本地写盘失败会提示，不能保证这些情况下可靠入队。

worker 查询现有完整项目再合并，查询失败不当项目不存在。失败保留队列及 auto-status.json；下次提交重试积压，也可 retry。每次最多处理 20 项，本地锁避免同时上传；更大队列需继续 retry，不承诺离线仍上传成功。

成功响应必须返回匹配项目 ID，才写 sent/<commit>.json 并移出队列。上传保存但回复丢失时，下次从远程 codeActivity 的提交证据对账，不重复应用摘要。服务没有跨机器 CAS/事务幂等能力，多机器/手动上报并发仍有覆盖风险，同项目避免同时上报。

config、summary、queue、sent 和日志只在被忽略的 .project-hub。队列绑定 Key 的不可逆身份摘要，不向新 Key 自动迁移；换 Key 暂停自动模式，重新确认启用。旧队列在原身份处理，不擅自清空或迁移。

status 查看无密钥状态；retry 重试；disable 停止并保留钩子/队列。设置 PROJECT_REPORT_QUEUE_ONLY=1 时钩子只入队不启动网络 worker，适合离线验证；显式 retry 仍会上报。

依据：[Git hooks](https://git-scm.com/docs/githooks)。post-commit 是提交产生之后，不是推送后。客户端跳过 hooks 时不会触发，应在真实使用中验证；本 skill 测试只在临时仓库创建离线提交。
