# 原生地图工具源码

本目录包含当前地图工具的 Swift 桌面端、Python HTTP/MCP 后端和 HTML/CSS/JS。`SOURCE_MANIFEST.json` 记录导出文件及来源哈希，程序主体保留外层项目实现；新增独立构建入口使其不依赖原作者机器目录或外层 build/。

## 构建

需要 Apple silicon Mac、Xcode 命令行工具、Python 3.9+，以及 `requirements-build.txt` 中的打包/直播依赖。先按根目录说明装配原生源码（供键位协议定义读取），再在自选虚拟环境安装依赖：

```sh
python3 -m pip install -r map-client/requirements-build.txt
python3 scripts/prepare_live_receiver.py --work /absolute/live-receiver
python3 scripts/build_map_client.py \
  --work /absolute/new-map-build \
  --native-source /absolute/native-work/MacNativeGames \
  --douyin-source /absolute/live-receiver
```

App 输出为 `/absolute/new-map-build/Native Adventure Map.app`，日志在同一工作区 logs/。输出目录必须在仓库外、尚不存在。仅构建并做 ad hoc 签名，不启动客户端、后台或游戏，不读写真实存档，不安装数据包；未提供 Developer ID 或公证保证。

## 数据与素材边界

默认不携带游戏原图、地图瓦片、攻略、图鉴、Figma 快照、DataPacks 或真实存档匹配表。空表使服务能够启动、查询工具清单及提供空结果；完整地图需合法数据包，存档点位/任务/图鉴匹配还需相应外部参考表。UI 使用中性占位图，与之前成品的视觉和数据完整度不同。

Reicon 通用图标保留原 [MIT](webui/icons/reicon/LICENSE)与 [来源记录](webui/icons/reicon/SOURCE.md)。程序中的物品和 amiibo 名称/ID 表仍用于协议，并不包括对应图片，其来源和权利也须区分。详见 [素材清单](../docs/inventory/game-assets.md)。

如自己有权使用原样资源，可增加 `--resources /absolute/authorized-resource-root`。根目录下的 `webui/` 仅允许导入：

- `save-reference.json`、`towers.json`、`quest-reference.json`、`compendium-save-reference.json`、`ui-assets.json`。
- `branding/`、`icons/game/`、`item-icons/`、`amiibo/`、`ui-assets/` 中的图片/SVG。

不自动复制 SQLite、DataPacks、offline/、compendium/ 或其他内容目录；不采集用户配置、令牌或存档。提供外部文件也不意味着其再分发自动获准。

## 可选远程隧道

公开地图 App Release 不附带 ngrok Agent。随包 `install_map_tunnel.command` 在用户机器上从官方取得固定哈希版本并对所选 App 作本地 ad hoc 重签，不采集 token、不启动隧道；需先关闭 App，并使用自己的 ngrok 账号。官方稳定下载若已变化，脚本会停止，不能跳过哈希检查。脚本也可从源码调用：`zsh scripts/install_map_tunnel.command "/absolute/Native Adventure Map.app"`。

默认不下载或附带 ngrok，缺少它时本机 MCP 仍可使用。确需构建内置隧道版本，可显式提供 `--ngrok-binary /authorized/ngrok`；须匹配 `desktop/tunnel-agent.json` 的既有哈希，构建时附其 credits。固定下载 URL 可能已更新，哈希失败必须人工核对，不能静默更新清单或跳过校验。账户与 token 不进入 App。

## 维护与验证

- 后端：`backend/`；客户端：`desktop/`；网页：`webui/`；空表/占位生成：`prepare_resources.py`。
- 修改源文件后更新来源记录中的本地派生说明，不用原哈希假装仍与导出源一致。
- 测试使用合成资源、隔离目录；不得把真实存档或素材作为公开测试夹具。
- PyInstaller/Pillow、Python 运行时和可选 ngrok 有各自许可；生成二进制需另行核对版权通知，不把根 MIT 作为所有嵌入内容的统一授权。

## 当前版本与运行数据

源码候选为2.0.24（124）。用户数据根为 `~/Library/Application Support/MacNativeGames/TOTK/Offline/`：`State/`保存修改器、直播规则、弹幕设置、连接状态、日志、手机HTTPS证书和轨迹；`DataPacks/`保存地图/攻略与注册表。首次启动在旧服务退出后迁移旧TOTK Native Map状态及TOTK Offline/DataPacks，校验摘要、保留证书权限并更新受控包路径；冲突或活服务时停止，不覆盖。日志改为追加。macOS Preferences和浏览器存储继续由系统管理。旧版App可能重建旧目录，请使用新版。

直播默认关闭，由用户显式连接。接收器源码不vendor：prepare_live_receiver.py从记录的固定官方提交下载并核对douyin-source.json，输出在用户指定外部目录；失败即停止。构建须提供--douyin-source，不能为凑齐构建而静默移除直播能力。仅复制十个源码/许可文件，不包含用户规则、账号、虚拟环境或protoc。接收器遵守原AGPL-3.0许可，非根MIT；构建产物保留其源文件和LICENSE。mini_racer等依赖遵守各自许可。打包包含签名引擎自检，不连接真实直播间。

手机陀螺仪使用局域网HTTPS和显式浏览器授权；启动地图不会自动授权浏览器、连接直播或控制游戏。物理手机方向、直播网络与真实游戏场景验收状态见根更新说明。
