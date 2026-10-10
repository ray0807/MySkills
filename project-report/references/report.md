# 上报对象

MCP 工具 `report_project` 参数为 `{ "project": <对象> }`，上报是完整快照。项目字段定义以服务 `src/schema.ts` 为准。

必填 `id`（1–128 字符，字母数字、下划线或短横线）、`name`。

其他字段：`description`、`goal`、`status`（planned/active/paused/completed/blocked）、`progress`（0–100，有依据再填写）、`priority`（low/medium/high/urgent）、`repository`（URL）、`deadline`（带时区 ISO 8601）、`completed`、`pending`、`pendingTests`、`blockers`、`nextActions`（字符串数组）、`testSummary`、`source`、`tasks`、`metadata`。

任务必填 `id`、`title`、`status`（todo/in_progress/pending_test/testing/done/blocked）；可填 `priority`、`description`、`assignee`、`requiresHuman`、`estimatedHours`（非负）、`deadline`、`dependsOn`（任务 ID 数组）、`blockers`（字符串数组）、`testResult`。同一项目任务 ID 必须唯一且应稳定。

将更多背景放入 metadata，例如：`audience`、`acceptanceCriteria`、`scope`、`outOfScope`、`milestones`、`deployment`、`risks`、`openQuestions`、`evidence`、`progressBasis`。未确认进度时保留已有值；首次无依据时可以省略 progress（服务默认 0），同时注明 `metadata.progressBasis: "待确认，0 为默认值"`，不能将默认值描述为实测完成率。
