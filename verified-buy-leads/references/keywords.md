# 为任意产品生成关键词

从产品名/型号/关键词建立 product_profile：是什么、不是什么、规格词族、供货方式、实际使用者、替代方案、能解决与不能保证解决的问题。只有歧义影响检索时询问。

12 维覆盖：①标准名/别名/缩写 ②规格/型号/子品类 ③当地叫法和市场语言 ④买方采购表达 ⑤使用组织/买方角色 ⑥替代方案 ⑦本人痛点 ⑧求助/推荐/比较句式 ⑨场景口语 ⑩触发事件 ⑪渠道/服务商 ⑫决策职位。每维有内容或不适用原因，不凑十种客户、七种语言。

本地叫法先用当地资料确认含义，再组当地买家口吻。语言按用户市场与探索反馈选，不固定任何行业的 Tier。歧义词加限定与排除，不能把所有卖同类产品的企业一律排除：他们也可能明确采购。

keyword_plan 保留 explicit、pain_points、triggers、channel_partners、coverage；增加 product_profile、product_families、local_terms、query_cells。每格包含 query_id、product_topic、language、platform、segment、intent、query。12 维覆盖代表计划完整，平台/语言格子的执行状态才代表搜过。

pain_points 含 segment/pain/queries/solution/limitations，解释“问题→可能方案→条件”，不能承诺替代品永远不如本产品。

按“产品词族 × 买方意图（购买/租赁/服务/求助/吐槽）× 场景 × 当地语言 × 平台”小样本试 1–2 组，不展开无限笛卡尔积。先明确需求再痛点，相关且有预算再看信号。一个组合一轮不重复，预算不足报告未跑格子。

channel_runs 为每个 query_id 记录 window_since/window_until、实际打开数量、合格数、噪音/限制及 next_check_at。连续两次成功零合格时换口语、词族、场景或平台；访问失败不能当零命中。连续三次失败可降频，有日期的 7–14 天冷却只是策略，不永久判死。新产品重新评估，不继承 LED 历史水位。

缺省市场先少量相关市场探索，不把“全语言全网”作为不可验证承诺。约定矩阵完成不代表找到全网所有买家。
