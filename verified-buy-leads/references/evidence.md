# 通用需求审查标准

## 证据分类

- explicit：买方原文明示采购或相应供货服务，保留原话与来源。数量未知可以成立，不对所有产品要求 1000 件。
- pain：使用方本人描述问题，且用户产品是合理方案。pain_type=seeking 求助/推荐，complaint 只吐槽；必须 pain_point、solution_pitch。评估成本、部署条件、替代方案与反证，不写无依据的优势承诺。
- possible：摘要、无法定位原评论、单句 price please、角色或对象不清。进 review，不计可跟进。
- signal：招聘、项目、开业、进口与渠道关系，单列 signals.jsonl，不计需求；不能用纯公司名单凑数。

保留现有 pain 存储名；上传版本的 latent 是同一类概念的别名，不需要破坏已有数据。附件客户编号与需求不导入为新线索。

## 商业模式与状态

demand_mode：purchase/rental/service/replacement/unknown。supply_route：direct/partner-only/unknown。需求真实不等于用户能供货；只卖产品不能把本地短租、维修需求自动计作硬件买家。

validity=open/closed/expired/unknown。open 要有明确开放证据，例如有效未撤销公告、买方最新说明仍在找。新帖和没有关闭回复不足以证明；社媒痛点通常 unknown。已经解决、授标、买到其他方案或明确拒绝该产品转 history。截止时间按公告时区判断，再转换展示；缺时区影响结果时留 unknown。

fit=matched/partial/mismatch/unknown。认证、规格、MOQ、交期、原产地和履约能力分别核对；未知不默认具备。局部可满足标 partial 并列 fit_gaps，不把“产品名一致”当 matched。

confirmation=public-unconfirmed 默认；buyer-confirmed 必须有回复依据和含时区日期。找到了联系方式不是确认需求。

## 来源准入

先按 channels.md 筛来源。source_kind 为 social/forum/buyer-owned/official-procurement/b2b-marketplace/lead-directory/paid-aggregator/unknown；B2B、线索目录、付费聚合及 paywalled 路径为 excluded，优先于有效期和评级。常见域名由 source-policy.json 拦截，其他来源由 AI 按实际类型标记。unknown 只能 review，不因联系方式可见自动升级。

access_context 为 public/existing-authorized-account/registration-required/unknown。需要新注册或申请加群不能可跟进；已有授权社媒账号可以核实其已有免费权限，不额外登录/申请权限。权限不足如实 blocked。

## 联系路径与身份

contact_path=free-direct/free-registration/paywalled/unknown；contact_path_evidence 记链接、验证事实与访问时间。免费浏览、免费注册和免费业务联系不是同一能力。只有帖子可见但联系权限未知时仍 unknown，不推测注册可以解锁。free-registration 只有 access_context=existing-authorized-account 且免费联系路径已实际核实时才能交付。

每个 contacts 保存 type/value/source_url/confidence，只记公开业务联系或明确商务用途，不记私人住址/私人电话，不猜邮箱。平台入口可作业务联系路径，但不代表用户授权已联系。

identity_confidence=high/medium/low/unknown。high 需需求发布者与机构有明确关系和交叉支持；姓名+国家、同名企业或附件作者不足。匿名账号可证明原作者入口，不自动证明公司身份。联系路径 confidence 与组织身份分开。

## 优先级与清单

- A：explicit、open、identity high、fit matched、supply_route direct，来源通过准入、免费路径有证据并有 high 联系路径。产品能力未知不能 A。
- B：explicit 有明确缺口，或 pain+seeking。
- C：pain+complaint 或其他有证据的低优先级需求，不容纳广告/纯名单。

能跟进还需 explicit/pain、未关闭/过期、fit 不为 mismatch、contact_path 为有证据的免费路径、有 contacts、supply_route=direct。B2B/线索目录/付费聚合或付费联系进入 excluded，不展示为候选客户；possible、未知路径、来源未知、新注册未就绪、合作商待落实进入 review。其余 closed/expired/mismatch 进入 history。优先级不会把 review 自动变成可跟进。

新导入 A 严格校验上述必要字段；历史记录缺字段按 unknown 待复查，不能推断免费或可直接供货。所有记录保留在 leads.json，不因重新分区删除证据。
