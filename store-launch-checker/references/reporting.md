# 检查报告与上线结论

报告 JSON：site_url、checked_at（含时区）、environment、markets、sample_urls、tools、limitations、checks。

每条 check：id（checklist 的稳定 ID）、title、status、severity、launch_gate、evidence、impact、remediation、retest。severity 为 critical/high/medium/low/info；launch_gate 是业务门槛，与 severity 分开。status 为 pass/fail/unknown/not_tested/not_applicable。

evidence 为数组，元素可包含 url、observed_at、method、observation、artifact_path、sample/region/device。结论与截图/响应/后台记录分开；不只写“AI 认为”。fail/pass 都需要可定位证据；not_applicable 写原因。unknown 写已执行但无法确定什么；not_tested 写尚未执行的原因。

报告必须显示门槛未验证项和样本覆盖；没有填结果的计划项补成 not_tested，不能默默删掉。覆盖率可为已得确定结果的适用条目/适用条目总数，明确排除不适用项；不把覆盖率说成健康度或上线通过率。

结论规则：
- blocked：门槛 fail，或已证实 critical 问题。
- verification_required：无上述失败，但有适用门槛 unknown/not_tested，或无法确认环境/业务适用性。
- ready_with_issues：适用门槛有证据通过，仍有其他 fail 或未验证项；把剩余风险列明。
- ready_in_scope：既定计划的适用检查均有证据通过，仍限定在样本/时间/市场内，不表示任何用户场景绝无故障。

严重性根据业务影响：付款成功但后台无订单是阻断；一次第三方工具 403 是检测限制；缺社交图通常优化项；正式核心商品意外 noindex 对自然搜索目标可设门槛，测试环境正确 noindex 不作为故障。

report.md 建议结构：结论与覆盖→上线阻断→缺少的必要证据→优先修复（每项影响、证据、修复、复测）→已通过→按市场/工具未测→范围与来源。不是只输出长清单。不同问题可汇总同一根因，但保留各受影响页面。

scripts/build_report.py 可校验并渲染检查结果。它不读取网页、不推断通过，要求输入 checks 和 planned_checks 数组；计划项必须含 id、title、launch_gate。AI 从 checklist 建立适用计划，至少保留域名/商品/结算/收单/履约等实际业务门槛，不能为了得到 ready 删除付款验证。未知环境须加明确门槛检查。
