# MCP / HTTP 发布接入

## 配置前置检查

所有模式均先验证接口，未完成时停在 configuration_required，只协助配置，不研究选题、写文章或生成图片。

- interface_type=mcp：配置 mcp_url 或已有连接器，完成初始化及工具发现，确认存在文章发布能力和可用目标。
- interface_type=http：配置 http_url、http_method、接口文档/请求字段映射、认证方式及目标。依据实际文档使用只读接口或无副作用的验证端点检查连接和权限，不盲目向发布地址发送 GET/POST。无验证端点时通过文档、目标及认证机制检查配置；仍无法确认发布能力则说明限制并等待补齐。
- auth_type 指定 none、bearer 或服务要求的方式；需要认证时要求凭据引用。站点/栏目固定在接口中时记录映射，不强求不存在的 site_id 字段。

接口配置与发布授权分别处理：连接通过不代表获准发布。配置检查不创建测试文章或上传测试媒体。

## 接口发现

用户给出的是 MCP 服务地址，不等于它接受 `POST /articles`。先用当前可用连接器或 MCP 客户端初始化，获取工具列表与输入 schema；根据服务支持协商协议与传输，不把任意 HTTP JSON API 当成 MCP。保存无密钥的能力映射：站点/栏目查询、文章列表/查询、媒体上传、创建草稿、发布或状态查询。只调用实际存在的工具，不能猜工具名和字段。

支持 Streamable HTTP、其他 MCP 传输或普通 HTTP API 的情况按实际接口文档适配，未明确就询问接口说明。远程携带凭据优先使用 HTTPS；若用户仅提供明文 HTTP，先核对是否本机/可信内网及认证方式，不自行把密钥发送到未知远程服务。不要把凭据写入 URL。

首次接入只做能力发现和只读检查；写入用用户实际授权的站点与栏目。接口提供 dry_run/校验功能时优先使用，没有时本地验证 payload，不擅自创建测试文章。

## 平台无关文章包

`article.json` 字段：
```json
{
  "content_key": "站点:选题稳定键:版本",
  "title": "",
  "slug": "",
  "language": "",
  "primary_keyword": "",
  "secondary_keywords": [],
  "search_intent": "",
  "excerpt": "",
  "meta_title": "",
  "meta_description": "",
  "body_markdown": "",
  "category_id": null,
  "tags": [],
  "cover_asset_id": null,
  "body_asset_ids": [],
  "source_urls": [],
  "requested_status": "draft"
}
```

这是内部字段，不保证服务支持。根据 schema 转换成平台实际要求的 Markdown/HTML、图片引用和 SEO 字段，保存 `publish-payload.json`（不含密钥）。HTML 只用平台允许的标签，移除脚本和不可信嵌入。没有 canonical、作者、结构化数据等字段时不伪造接口能力。图引用替换后再次预览。

## 状态与去重

每次运行稳定键包含站点与用户时区日期，同一次重试不得更换 content_key。主题重复检查按意图与既有文章内容，不仅按标题。更新旧文章需要明确对应文章 ID，禁止把 create 当 update。

状态：researched → drafted → quality_passed → media_uploaded → publish_pending → published。失败保存 last_error；不确定结果使用 publish_unknown。

发布前将 content_key、payload 摘要、目标站点和状态写入本地日志，锁定同站点运行。有幂等参数时用服务要求的键，同篇请求重用；没有幂等支持时先查 slug/content_key/文章目录。无法查询去重且一次写入超时后，停止再次 create，报告 publish_unknown；避免重复发布。

工具 HTTP 200 或 MCP 无协议错误不等于文章发布成功。检查工具业务错误、返回文章 ID、真实发布状态和 URL。接口仅返回草稿就记 draft，不记 published。可用时再查询状态或打开线上文章，验证标题、正文和图；查验失败区分“服务返回发布成功、线上显示未核验”和“发布状态未知”。

只读请求失败最多重试一次，429 尊重 Retry-After 且受预算限制。写请求明确未执行且服务支持幂等时最多重试一次；超时或断连可能已执行，先对账，未查清不重发。认证或权限错误不循环重试，不切换站点或凭据绕过。

`published.jsonl` 仅记录确认结果：content_key、site_id、article_id、status、url、published_at、verified_at、verification_method、media_ids。运行日志另存未知/失败，避免下一次当作“没发过”。已有远程文章不自动删除。
