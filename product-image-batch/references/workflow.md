# 批次计划与记录

脚本使用 Python 标准库，无第三方依赖。路径参数支持绝对路径；计划中的相对路径基于计划文件目录，清单写出为绝对路径。

计划示例（产品与路径替换成扫描实际结果）：

```json
{
  "batch_id": "20261016-001",
  "style": {"description": "简洁商业摄影，柔和棚光", "references": []},
  "call_budget": 8,
  "tasks": [
    {
      "id": "cup-main",
      "product": "保温杯",
      "source": "../保温杯/原图.jpg",
      "references": [],
      "platform": "alibaba",
      "slot": "01-白底主图",
      "output": "../保温杯/生成结果/alibaba/20261016-001/01-白底主图.png"
    }
  ]
}
```

id 在清单内唯一。首次生成计划图位数不能超过 call_budget；预算包含样图和重试。每图最多两次实际调用，第二次需要用户明确授权迭代预算；首次未明确生成成功时不自动重提。不要按估计费用声称确定价格。

初始化为任务增加 `pending`、`attempts: 0`、源文件 SHA256、空 `prompt`、`artifact` 和检查备注。批次增加 `calls_used: 0`。记录参考图与风格内容；恢复时重新检查源图和所有参考图 hash，风格变更使用新批次。

状态：`pending` 待做；`submitting` 即将提交/提交中；`submission_unknown` 无任务 ID 的提交结果未知；`submitted` 已保存 taskId 等待查询；`generated` 已取得结果 URL；`save_pending` 待落盘；`success` 检查通过且已复制；`needs_review` 已保存但仍需人工确认；`failed` 失败；`skipped` 缺资料或用户排除。

实际执行由 AI 读取/原子更新 JSON：调用前检查预算与 attempts，增加 attempts/calls_used，写 prompt 与 submitting；返回后立即写 taskId、submitted，后续只查询此 ID。每次查询存 service_status；成功存 resultUrl、实际返回的 pointsCost、generated；失败存 failReason、failed。调用超时无 ID 时存 submission_unknown，暂停该任务等待核验。

每个任务额外记录 provider=cocoon、model、aspectRatio、resolution、background、reference_urls（含 source_path、sha256、role、url）、taskId、resultUrl、pointsCost、quality_status、artifact（下载后的真实本地路径）。未提供字段保留 null，不估造费用。参考 URL 缓存按 SHA256 复用，不保存 Key，URL 失效不代表需要重新生图。

批次可增加 balance_checks 数组：每次包含 checked_at（带时区）、stage（before_sample/before_batch/on_demand/finish）、status（success/error）、balance（服务实际值，失败为 null）、unit（按实际响应）、error_summary（脱敏）。余额字段和类型以真实工具响应为准，不按示例猜服务字段。价格有核实依据时记录 pricing_source、checked_at、对应规格和预估；没有依据留空。实际费用按 taskId 去重汇总服务返回的 pointsCost，并注明缺失项；不把余额前后差额当成实际费用，不自动把失败任务记为已退款。

默认每隔5–10秒查询，总轮询预算约5分钟；到时保留 submitted，报告 taskId，后续恢复继续查询。等待期间不超过60秒无更新。保存后核对可读性并进行视觉检查，只有文件存在且检查通过才 success。复制前确保目标不存在，重做使用 -v2 等版本名；无本地保存能力用 save_pending。

用同目录临时文件加 replace 原子保存，不并发改清单。单张失败不会停止其他独立任务，但整体认证、余额或服务故障应停批。

原图之外的供应商资料与文字也记录在任务 notes 或附加字段中，保留事实来源。生成失败记录异常摘要，不存凭据。中断时 submitting/submission_unknown/submitted/generated/save_pending 人工核验后处理，不由脚本自动重发。只有 success 且输出存在才视为完成；needs_review 的结果保留供用户检查，不默认重做。
