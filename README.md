# Native Adventure Kit

基于上游原生运行实现的深度 Mod 装配工具：本仓库维护**脚本、Skill、文本补丁、版本锁、地图工具源码和说明**，不再携带完整 MacNativeGames 源码树、上游预编译工具或地图 App。

## 独立下载

- [地图 App v2.0.6](https://github.com/kailous/native-adventure-kit/releases/tag/map-v2.0.6)：macOS arm64 客户端成品、使用说明及运行时通知，不含 DataPacks、游戏或密钥。远程 ngrok Agent 由用户通过随包脚本直接从官方取得，不在公开附件中内置。
- [构建源码 2026.10.26](https://github.com/kailous/native-adventure-kit/releases/tag/source-v2026.10.26)：脚本、Skill、补丁、地图源码、版本锁及许可材料，不含 App 或预编译工具。

两者独立标记和打包，详见[发布范围与验证](docs/split-releases.md)。这不改变原生游戏 App 不对外发行的边界。

## DataPacks 数据包

地图与攻略 DataPacks 单独通过[百度网盘下载](https://pan.baidu.com/s/1iEN5GpfuFdfOlFbewLQHDQ?pwd=totk)，提取码：`totk`。数据包不放入 Git 或上述 Release 附件；下载后在地图 App 中导入 `.totkpack`。

下载前请查看[内容来源说明与清单](docs/data-pack-sources.md)，按文件名、大小及 SHA-256 核对版本。现有地图包除游民星空底图、瓦片和点位外，还含社区宝箱/任务数据及游戏资源派生地形；攻略与图鉴也有混合来源，不能一概视为游民或项目原创内容。当前地图标记 SVG 由维护者手工临摹，参考设计与图片的权利另行判断。

## 技术来源与贡献

原生运行、移植和构建基础来自 [MacNativeGames](https://github.com/ly05010419/MacNativeGames)、[d2r-mobile](https://github.com/jhaizhou-ops/d2r-mobile)、Ryujinx 等上游项目。本项目维护游戏控制、输入/菜单/显示扩展及 AI/MCP 工具的二次开发与集成，不将完整移植方案或所有补丁行宣称为本项目原创。继承和选择性合入的上游修改仍归功于其原作者；具体归属和未核实事项见 [第三方声明](docs/third-party-notices.md)。

补丁也可能包含上游代码片段和上下文，仍需遵守相关许可；改成脚本下载不消除游戏处理、技术保护措施或素材的授权问题。

## 准备源码

需要 Git 和 Python 3.9+。实际游戏构建另需 Apple silicon、macOS 26+、Xcode 命令行工具、Homebrew 依赖及 Python 3.14。

```sh
# --work 必须是仓库外、尚不存在的目录
python3 scripts/prepare_native.py --work /absolute/work/native-adventure
python3 scripts/prepare_native.py --work /absolute/work/native-adventure --verify
```

脚本自行从用户运行环境下载锁定上游，按文件哈希校验，应用文本补丁，再校验完整源码。当前锁定提交为 `f3e2f661dfc05d7f6708c903ea513c297db195f1`，不是每次追随最新 main。失败即停止；不调用 AI 猜测合并，不覆盖已有目录，不访问游戏、密钥或存档。

装配结果在 `/absolute/work/native-adventure/MacNativeGames/`。执行其 `build_app.py` 并自行提供合法游戏、累计更新、密钥和外部构建目录；参见 [完整步骤与排错](docs/bootstrap.md)。本步骤仅装配源码，不代表 App 已构建或游戏已验收。

## 素材与上游依赖

默认加载画面由脚本生成纯色 PNG 与中性文本 Logo，不携带原来的游戏/Figma 图像。可用 `--loading-assets /absolute/authorized-assets` 提供自己有权使用的 `background.png`、`logo.svg`、`footer.png`。该选项只读取外部输入，不将素材上传或提交到仓库。

上游版本中未修改的预编译着色器翻译器由上游取得并校验，不在本仓库镜像。SPIRV-Cross、hactool、Python 包及系统构建依赖仍由上游构建入口按其规则获取；并非所有依赖都锁定为同一系统镜像，未保证最终 App 逐字节一致。

## 地图工具源码

[map-client/](map-client/README.md) 包含 Swift 客户端、Python 后端及网页 UI 源码，以及有随附 MIT 的 Reicon 图标。游戏图片、原 Figma/品牌素材、DataPacks 和真实内容/匹配 JSON 未加入；默认生成空数据与中性占位图，可显式提供有权使用的外部资源。

[素材清单](docs/inventory/game-assets.md)及[逐文件记录](docs/inventory/game-assets.json)列出源位置、大小、哈希和已知来源，仅含元数据，不含实际素材。

装备表和物品目录的已知生成链、核验指纹及来源缺口见[生成数据来源](docs/generated-data-provenance.md)。当前目录一致性检查不等于输入授权已经核实。

## Skill 与 MCP

- [native-mod-build Skill](skills/native-mod-build/SKILL.md)：供支持文件型 Skill 的 agent 使用；其他 agent 可直接读取该文件。安装/发现方式由宿主决定，不自动写入用户的 agent 设置。
- [通用 AI 指导](AI接入/AI_GUIDE.md)、[MCP 接入](AI接入/MCP_USER_GUIDE.md)、[私人插件生成](AI接入/PLUGIN_GUIDE.md)。
- 地图客户端可由本仓库源码独立构建；本工具不从旧 Release 自动下载 App，也不建立私人远程连接。

## 目录与维护边界

| 目录/文件 | 用途与归属 |
| --- | --- |
| scripts/ | 维护者维护的上游装配/校验入口，不构建或启动游戏 |
| patches/ | 维护者审查的文本差异；保留相关上游版权，不接受二进制补丁载荷 |
| upstream.lock.json | 上游 URL、固定提交、补丁哈希及输入/输出文件清单 |
| skills/ | 用户或 agent 可读的构建协作指引，不代替脚本校验 |
| AI接入/ | MCP/插件协作说明及辅助工具 |
| docs/、licenses/ | 来源、许可、操作与兼容说明；保留原始许可文本 |
| map-client/ | 独立地图客户端/后端/网页源码及资源准备器，外部输出，不包含真实游戏素材和数据包 |
| docs/inventory/ | 资源清单元数据，不提供实际素材文件 |
| tests/ | 无真实游戏输入的装配与辅助入口回归测试 |
| 仓库外 --work | 用户运行脚本生成的源码工作区；核对用途后由用户自行保留/删除，脚本不自动清理已有工作区 |

## 历史版本

2026-10-26 经维护者明确授权，移除旧 Release 和附件，并将公开主线重建为当前源码的一次初始提交，清理旧标签及旧 Actions 记录。[发行列表](https://github.com/kailous/native-adventure-kit/releases)以远端实际状态为准。不重新分发旧地图 App、图像或预编译工具，也不抹去当前源码中的原版权和来源声明。

[v0.1.0 历史复核](docs/historical-release-review.md)保留旧包核验事实及处理记录。删除引用和附件不能保证清除 GitHub 缓存、他人克隆或已下载副本，也不追溯消除历史分发义务。

## 发布前检查

运行 `python3 -B scripts/check_release.py` 检查当前源码；实际候选 ZIP 使用 `--archive /absolute/candidate.zip`。检查只读，不上传、打包或启动游戏。范围、人工核验项与对外介绍模板见[发布检查说明](docs/release-governance.md)。通过检查不表示法律合规，当前仍保留来源与权利待核验警告。

## 许可证与风险

- 作者有权许可的独立原创代码：[MIT](LICENSE)，`Copyright (c) 2026 Li Peng`。
- 上游/派生片段：[保留的上游 MIT](licenses/MacNativeGames-LICENSE)与[各自许可证](docs/third-party-notices.md)。
- 原生 Mod 补丁中的 8 个头文件标有 [GPL-2.0-only](licenses/GPL-2.0-only.txt)；[逐文件来源与修改记录](docs/gpl-components.md)列明范围、Lotuskit 线索、装备表 MIT 来源及待核验事项。根 MIT 不替代这些条件，装配后的运行时不能一概视为 MIT。
- 游戏输入、素材、二进制和用户输出：按实际内容和权利分别判断。
- [授权范围](LICENSE_SCOPE.md)及[使用与风险说明 v1.2](使用协议.md)：不增加 MIT 许可条件，不构成法律合规认证。

当前项目发布脚本、Skill、源码、补丁和说明，不发行原生游戏 App。补丁中的 GPL 源码仍按其许可证分发；用户自行构建不等于取得生成 App 的再分发许可。已移除的历史附件未重新打包或认证；无法找回的原始数据来源继续标为待核验。
