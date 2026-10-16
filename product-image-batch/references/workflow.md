# 批次计划与记录

脚本使用 Python 标准库，无第三方依赖。路径参数支持绝对路径；计划中的相对路径基于计划文件目录，清单写出为绝对路径。

计划示例（产品与路径替换成扫描实际结果）：

```json
{
  "batch_id": "20261016-001",
  "style": {"description": "简洁商业摄影，柔和棚光", "references": []},
  "call_budget": 1,
  "tasks": [
    {
      "id": "cup-main",
      "product": "保温杯",
      "source": "../保温杯/原图.jpg",
      "references": [],
      "description_files": [],
      "platform": "alibaba",
      "slot": "01-白底主图",
      "output": "../保温杯/生成结果/alibaba/20261016-001/01-白底主图.png"
    }
  ]
}
```

id 在清单内唯一。默认 call_budget 等于用户选定的计划总图位数，额外重做预算默认零。样图仅用户明确要求时启用并计入总数，不额外增加调用。每图最多两次实际调用，第二次需要用户明确授权迭代预算；首次未明确生成成功时不自动重提。不要按估计费用声称确定价格。

初始化为任务增加 `pending`、`attempts: 0`、源文件 SHA256、空 `prompt`、`artifact` 和检查备注。批次增加 `calls_used: 0`。记录参考图与风格内容；恢复时重新检查源图和所有参考图 hash，风格变更使用新批次。

状态：`pending` 待做；`submitting` 即将提交/提交中；`submission_unknown` 无任务 ID 的提交结果未知；`submitted` 已保存 taskId 等待查询；`generated` 已取得结果 URL；`save_pending` 待落盘；`success` 检查通过且已复制；`needs_review` 已保存但仍需人工确认；`failed` 失败；`skipped` 缺资料或用户排除。

实际执行由 AI 读取/原子更新 JSON：调用前检查预算与 attempts，增加 attempts/calls_used，写 prompt 与 submitting；返回后立即写 taskId、submitted，后续只查询此 ID。每次查询存 service_status；成功存 resultUrl、实际返回的 pointsCost、generated；失败存 failReason、failed。调用超时无 ID 时存 submission_unknown，暂停该任务等待核验。

每个任务额外记录 provider=cocoon、model、aspectRatio、resolution、background、reference_urls（含 source_path、sha256、role、url）、taskId、resultUrl、pointsCost、quality_status、artifact（下载后的真实本地路径）。未提供字段保留 null，不估造费用。参考 URL 缓存按 SHA256 复用，不保存 Key，URL 失效不代表需要重新生图。

批次可增加 balance_checks 数组：每次包含 checked_at（带时区）、stage（before_batch/on_demand/finish）、status（success/error）、balance（服务实际值，失败为 null）、unit（按实际响应）、error_summary（脱敏）。余额字段和类型以真实工具响应为准，不按示例猜服务字段。价格有核实依据时记录 pricing_source、checked_at、对应规格和预估；没有依据留空。实际费用按 taskId 去重汇总服务返回的 pointsCost，并注明缺失项；不把余额前后差额当成实际费用，不自动把失败任务记为已退款。

默认每隔5–10秒查询，每个任务一轮约5分钟；到时保留 submitted 并报告进度，可先处理其他独立图位，再返回查询同一任务，不把单次轮询到时当作整批结束或要求用户回复继续。若服务长期无进展或宿主无法持续运行，明确记录阻塞与待办，不无限轮询、不重新提交。等待期间不超过60秒无更新。保存后核对可读性并进行视觉检查，只有文件存在且检查通过才 success。复制前确保目标不存在，重做使用 -v2 等版本名；无本地保存能力用 save_pending。

用同目录临时文件加 replace 原子保存，不并发改清单。单张失败不会停止其他独立任务，但整体认证、余额或服务故障应停批。

原图之外的供应商资料与文字也记录在任务 notes 或附加字段中，保留事实来源。生成失败记录异常摘要，不存凭据。中断时 submitting/submission_unknown/submitted/generated/save_pending 人工核验后处理，不由脚本自动重发。只有 success 且输出存在才视为完成；needs_review 的结果保留供用户检查，不默认重做。

计划的每个任务在 description_files 中填写扫描到的全部产品 TXT 路径；初始化会记录其 hash，恢复时检测资料变化。综合资料时保留来源，内容冲突需要用户确认。空列表表示无文本资料，不限制生成无文案图片。

数量与风格选定后默认整套连续执行，needs_review 不阻止后续独立任务。每次重做的 taskId、pointsCost、status 存入 attempts_history，保留旧记录；费用按所有唯一 taskId 去重汇总，服务未提供费用的任务计为未知，不当成零费用。

场景任务提交前记录 scene_plan（purpose、evidence、interaction、feasibility、composition、avoid、fallback），按 scene-planning.md 检查。交互关系不合理或缺依据的结果 quality_status=failed，状态 needs_review，保留具体问题；不得仅因“已生成”“产品看着相似”就标检查通过。

scene_plan 同时包含 preflight 与 preflight_summary；preflight 必须为 pass 才能付费提交场景图。revise 或 insufficient_evidence 时先修改方案或改为有依据的图位，不消耗一次生成来验证想法。该门槛目前由执行 skill 的 AI 遵守，辅助脚本没有拦截外部 MCP 调用的能力，不宣称已由代码强制执行。

初始化预算校验：call_budget 缺省等于 tasks 数量；额外调用需 authorized_extra_calls（非负整数）和 extra_calls_authorization（用户授权依据），预算必须与二者之和一致。记录授权不能代替真实用户授权。此检查仅约束清单，不拦截外部 MCP 调用。pending 返回 next_action，AI 必须区分核验未知提交、查询已有任务、保存已有结果和首次生成，不把所有待办重新生图。
