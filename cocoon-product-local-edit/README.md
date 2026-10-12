# cocoon-product-local-edit · 局部修改

把 [Cocoon 图片 MCP](https://mcp.boomclaws.com/) 的通用文字生图/参考图编辑能力包装为 **指定区域换色、杂物移除和小范围细节编辑**。AI 负责理解需求、选择参考图、组织提示词、调用服务和核验结果，不是只返回一段提示词。

## 快速使用

把整个 `cocoon-product-local-edit` 目录放入支持 Skill 的 AI 客户端技能目录，保留 scripts 和 references。只安装这个目录即可，不依赖其他商品图片 Skill。通用方法见[技能库首页](../README.md#如何使用)。

先把图片 MCP 接入客户端：

```json
{
  "mcpServers": {
    "cocoon-ai": {
      "url": "https://mcp.boomclaws.com/mcp",
      "headers": {"Authorization": "Bearer YOUR_IMAGE_SERVICE_KEY"}
    }
  }
}
```

从服务管理页获取该图片服务自己的 Key，在本机私密配置替换占位符。此示例是通用结构，客户端具体字段按其要求设置。无需在 Skill 源码中填写密钥。没有配置或认证失败时，AI 会先提示配置，暂停生图。

附上参考图片，对 AI 说：

```text
请使用 cocoon-product-local-edit。
只把图中右侧镜腿末端改成深蓝色，镜框、镜片、Logo 和背景保持不变。
```

默认：**保留原画幅，1K，1 张**。无需填写一大组参数；AI 从图片、会话和用途判断。只有关键素材、位置或意图缺失时才询问。

## 执行过程

1. 确认 Cocoon MCP 已连接，读取实际工具 schema。
2. 查看参考图，记录商品与其他参考素材的角色。
3. 按用途组织提示词，明确要改变和要保留的内容。
4. 通过 generate_image 提交，保存 taskId。
5. 用 get_image_task 查询任务，查看实际生成图片。
6. 检查商品、细节和用户要求，展示结果与可用链接。

默认一次生成会扣服务积分。价格和余额以当次服务信息为准；安装和离线测试不扣生成积分。用户要求多张/更高规格时按明确数量执行，不默认批量扩张。超时或断连不自动再次提交，避免重复扣费。

## 本地参考图上传

服务需要公网参考图片 URL，不能直接读取 D 盘路径。已附带 Python 3 标准库上传助手：

```powershell
$env:COCOON_IMAGE_KEY = '在本机配置图片服务Key'
python -X utf8 scripts/upload_reference.py --file "D:/images/product.png" --output "D:/image-work/reference.json"
```

脚本上传到该服务的临时文件接口，返回 reference_url，**不会生成图片**。该上传接口用 multipart keyCode 字段认证，与 MCP Authorization 头不同。支持 PNG、JPEG、GIF、WebP、AVIF，文件上限 20 MiB；服务实际限制更严时以服务为准。凭据不写入结果文件，不自动重试上传。参考 URL 可能有有效期。

没有脚本执行能力时，可使用服务支持的上传方式获得可访问 URL，再由 AI 使用。原图需要能被查看，不能仅靠文件名决定内容。

## 输出与能力边界

交付实际图片、结果链接、任务 ID 和检查说明。生成成功不代表商品一定没有变形；AI 查看后才标视觉检查通过，无法查看时标待人工检查。

当前接口没有 mask 参数，属于提示词约束的生成式编辑；须检查未修改区域是否漂移。

不声称本服务有未提供的专用接口。图片无法内嵌显示时给可用结果链接，不以提示词或占位图代替成品。运行素材、参考记录和最终提示词放在独立数据目录，不提交 Git。

## 检查与维护

```powershell
python -X utf8 -B scripts/test_upload_reference.py
```

3 项离线检查覆盖图片格式、上传字段、结果不包含密钥，以及失败不重试。不会联系真实服务或使用生成额度。公开 MCP 地址与工具名已确认；需要使用者的有效连接才能实际生图，本次 Skill 创建没有进行收费生成或真实上传测试。

- [SKILL.md](SKILL.md)：AI 的任务专属流程与质量要求。
- [references/cocoon-mcp.md](references/cocoon-mcp.md)：工具字段、连接、上传、费用与异步任务处理。
- [scripts/upload_reference.py](scripts/upload_reference.py)：本地参考图上传助手。

## 缺少 Key 时

AI 会提示用户填写 Cocoon AI 图片服务 Key，优先在本机私密 MCP 配置中输入，填写并验证后才继续生成。本地上传助手缺少 COCOON_IMAGE_KEY 时会明确提示配置，不发送上传请求。已有有效连接不重复索取密钥，认证失败则提示更新。
