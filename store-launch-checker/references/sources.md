# 官方资料与调研依据

整理时间：2026-10-13。以下是核验入口，不是永久不变的法规或平台标准。平台/支付/国家条件按用户实际部署和当前页面核验；不把某平台政策扩成所有电商站的法律义务。

| 来源 | 影响本 skill 的判断 |
| --- | --- |
| [Shopify 开店检查](https://help.shopify.com/en/manual/intro-to-shopify/initial-setup/new-to-shopify-checklists/local-grocery-checklist) | 商品、运费、支付及多种订单路径需要实际设置与测试，不只是前端好看。 |
| [Shopify 测试订单](https://help.shopify.com/en/manual/checkout-settings/test-orders) | 测试购买覆盖结算、库存、配送、邮件与税；测试模式和真实付款有区别，上线配置需重新核对。 |
| [Stripe 测试](https://docs.stripe.com/testing) | 使用匹配模式的测试机制，不向真实支付提交测试卡。 |
| [Stripe 履约](https://docs.stripe.com/checkout/fulfillment.md?payment-ui=stripe-hosted) | 支付返回页不足以证明收单，支付通知与幂等履约要验证。 |
| [Google 电商 SEO](https://developers.google.com/search/docs/specialty/ecommerce) | 内容发现、网站导航、产品数据与上线策略需要一起检查。 |
| [Google 电商上线](https://developers.google.com/search/docs/specialty/ecommerce/how-to-launch-an-ecommerce-website) | 上线时登记/抓取/索引观察与上线前保护阶段有区别。 |
| [Google 规范 URL](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls) | canonical/重定向/sitemap 一致性；缺 canonical 不自动等于不可上线。 |
| [Google robots](https://developers.google.com/search/docs/crawling-indexing/robots/intro) | 抓取与访问控制、索引限制不同。 |
| [多语言页面](https://developers.google.com/search/docs/specialty/international/localized-versions) | 对应语言页面与 hreflang 条件检查，不套用到单语站。 |
| [Product 商家结构化数据](https://developers.google.com/search/docs/appearance/structured-data/merchant-listing) | 核对商品价格/库存与实际页面，区分语法、资格及实际展示。 |
| [Google meta keywords](https://developers.google.com/search/blog/2009/09/google-does-not-use-keywords-meta-tag) | 不把 keywords 缺失当 SEO 问题。 |
| [Web Vitals 阈值](https://web.dev/articles/defining-core-web-vitals-thresholds) | 当前 LCP/INP/CLS，字段百分位与测量方法分开。 |
| [PageSpeed Insights](https://developers.google.com/speed/docs/insights/v5/about) | 实验室/字段、URL/origin 粒度及新站数据不足不可混淆。 |
| [GA4 电商验证](https://developers.google.com/analytics/devguides/collection/ga4/validate-ecommerce) | 验证事件真实接收与交易标识，不只检查代码存在。 |
| [Google Consent Mode](https://developers.google.com/tag-platform/security/guides/consent) | 记录同意状态与实现模式，不单凭网络请求认定违规。 |
| [Merchant Center 网站要求](https://support.google.com/merchants/answer/12160471?hl=en) | Shopping 渠道中的可购买、支付与政策条件，按渠道适用。 |
| [Merchant Center 结算要求](https://support.google.com/merchants/answer/9158778?hl=en) | feed、商品页与结算价格/附加费用的准确性。 |
| [退货政策说明](https://support.google.com/merchants/answer/14011730?hl=en) | 公开政策可访问、条件和相关页面一致性。 |
| [W3C 可访问性初查](https://www.w3.org/WAI/test-evaluate/preliminary/) | 初步和自动检查不等于完整可访问性认证。 |
| [OWASP 安全头](https://owasp.org/projects/secure-headers-project) | 被动响应头检查是线索，不能代表完整安全审计。 |
| [英国 ICO Cookie 指引](https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/guide-to-pecr/cookies-and-similar-technologies/) | 英国市场相关实现按最新适用要求核验；不对所有国家套同一 Cookie 法律结论。 |
