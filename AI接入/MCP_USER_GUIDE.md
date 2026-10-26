# 普通用户：让 AI 帮你接入 MCP

接入前建议阅读 [使用与风险说明](../使用协议.md)。agent 应说明凭据、远程和游戏操作风险并取得具体任务授权；这不是 MIT 源码使用权的额外条件。现有辅助脚本的固定确认输入见 [兼容说明](../docs/compatibility.md)。

适用于使用者另行取得并运行的兼容原生地图工具。当前版本提供地图源码及独立构建入口，不携带或自动下载地图 App 与 DataPacks；旧 Release 为历史归档。合法数据来源与单独导入参见 ../docs/map-client.md。MCP 是 AI 调用地图和游戏功能的连接协议；插件是给 AI 的使用说明及连接封装。安装插件不会自动启动 Mac 上的地图工具，也不会自动生成远程服务。

## 把这段话交给你的 AI

> 请阅读发布包「AI接入」目录的 MCP_USER_GUIDE.md、AI_GUIDE.md 和 PLUGIN_GUIDE.md。帮助我接入本机原生 TOTK 地图 MCP，并按需要生成我的私人插件。先确认你运行在我的 Mac、本地容器还是云端，以及客户端支持的 MCP 传输与认证方式。保留已有配置，只添加本项目。URL 和令牌从我自己的地图工具取得，不使用原作者连接。先以 initialize、tools/list 和搜索地图验证，不启动游戏、不发送游戏控制输入。只有我明确要求后再操作游戏。遇到登录、授权或密钥填写，让我在系统或客户端界面完成，不让我把秘密发进聊天。完成后告诉我连接是否验证成功、配置在哪里、尚有什么限制。

无文件读取能力的 AI：先把 AI_GUIDE.md 正文粘贴给它，再给所需章节；仅上传 zip 不保证 AI 能读取其中内容。不要上传带真实令牌的配置文件。

## 1. 在 Mac 上取得自己的连接

1. 打开 `TOTK Native Map.app`，保持运行，等待服务就绪。
2. 选择「服务 → MCP 连接信息…」或「复制 MCP 配置」。地址以界面为准，端口被占用时会变化；不要固定写死 8765。
3. 在自己的 AI 客户端 MCP 设置中导入复制的配置。里面的 `Authorization: Bearer ...` 是地图服务令牌，不是游戏解密 key、OpenAI API key 或 ngrok Authtoken。不要分享此配置。

界面复制的是下面这种结构，示例中的占位符不能直接连接：

```json
{
  "mcpServers": {
    "totk-offline": {
      "url": "http://127.0.0.1:实际端口/mcp",
      "headers": {"Authorization": "Bearer 你自己的地图服务令牌"}
    }
  }
}
```

## 2. 按 AI 所在位置选择

| AI 运行位置/能力 | 接入方法 |
| --- | --- |
| 同一台 Mac，支持 Streamable HTTP 和请求头 | 使用本地配置，不需要隧道或云插件 |
| Codex 本机版 | 在 MCP 设置添加 HTTP 服务；也可让 agent 把配置合并到现有 `config.toml`，见下方 |
| ChatGPT 网页或其他云端 agent | 不能把 Mac 的 127.0.0.1 当云端地址；用自己启用的 HTTPS 隧道，或平台支持的私有连接方式 |
| agent 在容器、远程主机或另一台电脑 | 其 localhost 不是 Mac；选择已授权的远程连接，不把本地 URL 原样照抄 |
| 客户端只支持旧 SSE 或 stdio | 不能把 HTTP URL 填到 command，也没有可直接替换的 /sse。优先更新客户端；确需桥接时按其官方文档选择桥接器并验证认证转发 |
| AI 不支持 MCP/外部工具 | 可以阅读指引帮助配置，但不能声称已连接或已操作游戏 |

非 Codex/ChatGPT 的客户端不需要 OpenAI 账号来使用本机 MCP；其产品是否开放 MCP、配置文件格式及认证能力由该产品决定。让 agent 查当前官方文档后再合并配置，不猜配置路径。

### Codex 配置示意

以下是需要替换实际地址的配置片段，不是整份配置。采用环境变量时，必须确保实际启动 Codex 的进程能读取该变量；桌面图标启动通常不会继承某个终端临时设置的变量。普通用户优先使用客户端提供的安全凭据字段。

```toml
[mcp_servers.totk_native]
url = "http://127.0.0.1:实际端口/mcp"
bearer_token_env_var = "TOTK_MCP_TOKEN"
```

本机添加后，让 AI 重新加载 MCP 或开启新会话，先列出工具，再搜索“神庙”。不要用攻击、移动或刷物品验证连接。[Codex 官方 MCP 配置](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)。

## 3. ChatGPT/云端接入

在地图工具里打开「服务 → 固定地址 MCP 隧道…」，使用**自己的** ngrok 固定域名和 Authtoken。账号登录与令牌填写由使用者在对应界面完成；Authtoken 保存在 macOS 钥匙串。启用后等状态为 connected，再点「复制远程 MCP 配置」。远程 URL 应为 HTTPS 且以 `/mcp` 结尾，保留配置中的额外 ngrok 请求头。

接入会使持有地图服务凭据的远程客户端能够访问 MCP 能力，包括游戏控制。只分享给自己信任的客户端；退出地图工具或停止服务后，连接即不可用。远程服务需要 Mac 在线且保持运行。

ChatGPT 当前官方流程为：Plugins → 添加自定义 MCP server → 填写自己的 HTTPS `/mcp` 地址或平台提供的 Secure MCP Tunnel → 配置认证 → 创建为插件 → 检查工具并在新会话选用。界面与账号/工作区权限可能不同，按当时实际入口和[官方接入说明](https://developers.openai.com/plugins/deploy/connect-chatgpt)操作。

本项目自带 ngrok 隧道不等同于 OpenAI Secure MCP Tunnel，不生成 `tunnel_id`，也不提供 OAuth 登录。若客户端支持 API key/Bearer，使用自己的地图服务令牌；若只接受 OAuth，需部署由自己管理、提供真实 OAuth 与上游 Bearer 转发的桥接服务，或者改用支持 Bearer 的客户端。不要选择“无认证”来绕过，不把令牌拼进 URL，不复用原作者私有中转域名。自动构建 OAuth 服务不属于本包功能。

## 4. 验证与排错

成功应有：MCP 初始化成功、`tools/list` 返回实际工具、一次 `search_points` 返回结果。地图查询不要求游戏运行；实时位置、画面和游戏控制需要原生游戏在线。存档进度还需要正确的存档目录。

| 现象 | 优先检查 |
| --- | --- |
| 连接被拒绝/超时 | 地图工具是否运行、当前端口、AI 是否真的在同一台 Mac |
| 401 | Authorization 是否完整，是否误用 ngrok 或游戏密钥；从界面重新复制 |
| 浏览器 GET /mcp 返回 405 | 本服务不提供 GET 流；用 MCP POST 初始化验证，405 本身不等于服务损坏 |
| 400/415 | 客户端协议版本、JSON-RPC 和 Content-Type，不能当普通网页请求 |
| ngrok 错误或警告 HTML | 隧道状态、自己的域名/Authtoken，以及远程配置的 ngrok 请求头 |
| ChatGPT 只能选 OAuth | 当前平台认证不匹配；使用匹配的客户端或自己的 OAuth 桥接 |
| 工具列表仍旧 | 在连接设置刷新工具元数据，再开新会话；以实际 tools/list 为准 |
| 地图为空 | 本公开版本不含数据包；检查是否已有合法兼容数据并完成导入，不是 MCP 令牌问题 |
| 游戏工具 disconnected/stale | 检查原生游戏与版本，不向断线游戏重复发送控制请求 |

本包「generate_mcp_bundle.py」提供只做 initialize、通知和 tools/list 的 `check` 子命令，使用方法见 [插件生成指引](PLUGIN_GUIDE.md)（发布包文件名为 PLUGIN_GUIDE.md）。它不调用游戏工具，也不打印令牌。配置是私人文件，校验结果不代表已安装平台插件或游戏实测通过。
