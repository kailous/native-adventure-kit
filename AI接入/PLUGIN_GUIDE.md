# 让 agent 生成自己的私人插件

插件生成/安装建议先阅读 [使用与风险说明](../使用协议.md)，并确认具体文件写入或账号操作授权。现有辅助脚本仍使用 v1.1 固定确认输入，agent 不得伪造回复；按 [兼容说明](../docs/compatibility.md)处理。这只是选择使用辅助入口时的交互格式，不限制 MIT 权利，本次未修改程序。

先按 [MCP 用户教程](MCP_USER_GUIDE.md)连接自己的地图服务，再加载 [通用 AI 指导](AI_GUIDE.md)。发布包中这两份文件分别叫 MCP_USER_GUIDE.md 和 AI_GUIDE.md。

## 最短做法

把这段交给能读文件、执行命令的 agent：

> 请阅读发布包 AI接入/ 下全部说明，确认我的 MCP 客户端和认证能力。先生成一个不含任何真实凭据的 TOTK 私人插件包；只有我提供自己的远程 HTTPS MCP 地址时才加入服务器声明。本机 HTTP MCP 单独按我的客户端官方格式配置。使用 generate_mcp_bundle.py，不上传公开目录、不覆盖旧插件，不复用原作者的插件或服务器。先验证包结构，再指导我在自己的客户端安装、填写凭据并刷新工具。把“文件已生成”“账号已安装”“MCP 可调用”分别报告。

## 生成器

需要 Python 3.9+，仅标准库。发布包内在 AI接入/ 目录执行；命令中的目录都由使用者自己选择，输出目录必须尚不存在：

```sh
# 只生成通用说明技能插件；不绑定服务，配合已经配置的 MCP 使用
python3 generate_mcp_bundle.py generate --out "/absolute/path/my-totk-plugin"

# 给支持便携插件/API key 认证的宿主生成自己远程服务的连接声明
python3 generate_mcp_bundle.py generate \
  --url "https://your-own-domain.example/mcp" \
  --out "/absolute/path/my-totk-connected-plugin"
```

第一种方式生成 skills-only 插件；第二种额外生成 portable `mcp.json`，声明 Streamable HTTP 及 OpenAI 扩展中的 API-key/Bearer 认证，不包含实际 token。生成器不发网络请求、不部署服务器、不登录账号、不安装插件。URL 示例必须替换成自己的真实地址；生成成功不证明地址可用。

输出包括 `totk-native-helper/` 和同名 zip。目录含 Agent Plugins 1.0 `plugin.json`、`skills/totk-native-guide/SKILL.md`、所需参考文档，以及可选的 `mcp.json`。便携格式不等同所有宿主原生格式；旧版 Codex/其他宿主可能需要其官方兼容 manifest。让 agent 查对应宿主规范并生成适配副本，保留原包，不机械改扩展名。

远程认证声明只描述如何填写凭据；实际令牌由使用者在支持的客户端凭据界面输入。若宿主忽略 OpenAI 扩展、无法提供请求头，或要求 OAuth，则不能直接使用这个 Bearer 连接包。不要改为 auth none；改用独立 MCP 配置或自己部署的真实 OAuth 桥接。ngrok 场景还需按地图工具复制的远程配置保留 `ngrok-skip-browser-warning: 1`；不支持额外头的宿主需单独核对兼容性。

## 安装与验证

支持 Agent Plugins 的宿主，按其当前“从本地目录/包安装”或私有插件导入流程选择生成目录/zip。有 plugin-creator 能力的 agent 可在使用者明确要求保存到自己账号后调用其受支持的私有安装流程；没有该工具时停留在文件交付，并说明安装未完成。不要凭空提供插件 ID、app ID 或市场链接。

ChatGPT 也可直接从自己的 MCP endpoint 创建连接插件；当前入口和权限以[官方说明](https://developers.openai.com/plugins/deploy/connect-chatgpt)为准。包生成和服务器发现是两件事，均需验证；新会话选中插件后先列工具、再查一个神庙。无需公开上架，也不自动复用原作者的私有 OAuth 中转。

若客户端没有插件体系，只需配置 MCP，再把 AI_GUIDE.md 作为项目说明/指令加载，不需要上传插件 zip。[OpenAI 插件概览](https://learn.chatgpt.com/docs/plugins)。

## 可选：只读握手检查

把地图工具「复制 MCP 配置」的内容保存为**自己本机的私人 JSON 文件**（含真实令牌，不要上传/分享），限制权限后执行：

```sh
chmod 600 "/absolute/private/totk-connection.json"
python3 generate_mcp_bundle.py check --config "/absolute/private/totk-connection.json"
```

检查器仅发送 initialize、notifications/initialized 和 tools/list，不调用任何地图或游戏工具，不打印 URL/令牌/服务返回的详细内容。成功显示协议和工具数量。它不是 SSE/stdio 桥接器，不安装插件；检查通过也不等于宿主已安装、OAuth 已配置或游戏内通过。

通用 HTTP 协议参考：[MCP Streamable HTTP](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)。所有产品界面与账号能力均可能变动；本说明核对日期为 2026-10-26。
