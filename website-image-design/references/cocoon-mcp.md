# Cocoon MCP 接入与调用

公开接入地址 https://mcp.boomclaws.com/mcp，Streamable HTTP；请求头 Authorization: Bearer <服务Key>。复用现有连接，发现实际工具名称，以当次 tools/list schema 和响应为准，以下是已有接口约定，不是实时能力保证。

缺 Key 请在本机私密配置填写；没有 Key 到 https://mcp.boomclaws.com/ 注册登录获取。不在聊天、提示词、日志或源码保存 Key。认证失败停止该服务调用，不改用其他账号或服务。

## 工具

- get_points_balance：查询实际余额，保留原单位与精度，失败不当作零。当前价格未知就说明未知，不猜剩余可生成张数。结束时可刷新余额。
- generate_image：提交一张图片。常用字段 prompt、model、imageUrls、aspectRatio、resolution、background、waitSeconds，以实际schema为准。不要发明 n/count、mask、任意宽高等字段。
- get_image_task：用 taskId 查询已有任务，不为查询另行生成。

已知模型约定：文生图 gpt-image-2-5，图生图 gpt-image-2-5-image-to-image；默认1K，画幅按页面和实际支持选择，非强制方图。已知分辨率1K/2K/4K，背景opaque/transparent/auto；白底不等于透明。模型、支持画幅及特殊限制调用前核对schema；不要默默切换模型。参考URL最多16张，提示词最多20000字符，限制如有变化以服务为准。outputFormat不能保证实际输出格式。

## 参考图

先查看本地产品图和风格图，明确首图与其他图角色。imageUrls 需要可用HTTP(S)图片URL，不能填本地路径、网页地址或附件ID。网站风格需AI实际浏览总结，再写入提示词，生图服务不替AI浏览。

本地图片用 scripts/upload_reference.py 上传：POST https://mcp.boomclaws.com/v1/point/public/upload/temp-file，multipart字段 file 与 keyCode，返回 data.downloadUrl。上传认证字段不同于MCP请求头；脚本从 COCOON_IMAGE_KEY 读取同一个Key。已有公网图片URL可直接使用，不必额外上传。

脚本支持PNG/JPEG/GIF/WebP/AVIF，单文件不超过20MiB。仅做基础类型识别，不能代替图片解码与视觉检查。用户要求将参考图用于该服务生成已包含相应上传用途，无须每张再次确认。URL可能过期；按原图hash复用，失效再上传，不将参考URL作为正式网站资源。

脚本拒绝重定向以免转发凭据。HTTP错误会提供状态和可用跟踪号，不输出响应正文；403本身不能证明是Cloudflare或Key问题。不要伪装浏览器、不断试探或臆断故障原因。

## 提交与查询

建议 waitSeconds=0，拿到 taskId 立即在本地非公开记录中保存，记录提示词、素材来源/角色、规格、结果与实际返回费用。记录在项目既有私密运行位置或本地忽略目录即可，无固定表单要求；最终图片正常进入项目资源目录。检查MCP isError、JSON-RPC及业务错误，HTTP200不等于生成成功。

已知任务状态0待处理、1成功、2失败。间隔5–10秒查询，短轮询后可继续其他开发工作再回查，不因为等候进度就结束请求。成功且实际有resultUrl（兼容result_url）才获取结果。失败保存failReason，退款未核实不宣称已退款。

生成没有已知客户端幂等保证。提交超时无ID时可能已执行或扣费，先核验历史，不自动重提；有ID只查原任务，有结果只保存。余额不足、认证和整体服务故障时停止新提交，不反复付费试错。默认不追加未授权的重做。

费用按唯一taskId汇总pointsCost实际值，重复查询不重复计费记录；未知项单列，不把余额前后差额当成任务账单。数量和费用已授权就连续执行，不增加逐图确认。

## 结果

先按宿主允许方式查看实际结果，核对产品、场景物理关系、文字和构图。不能查看时注明未做视觉检查，不假称通过。保存结果是网站开发交付的一部分，按实际格式落盘，不能只把临时URL接入页面。不要下载媒体来绕过宿主显示限制。

图片保存、视觉质量和页面接入分别如实报告，不以服务成功代替最终效果。完整网站开发、测试与交付仍沿用正常流程。
