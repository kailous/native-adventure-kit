# 第三方代码与发行核查

核对日期：2026-10-26。适用范围见 [LICENSE_SCOPE.md](../LICENSE_SCOPE.md)，操作风险见 [使用协议](../使用协议.md)。本清单区分“已读到许可证文本”“来源/修改可追溯”和“实际二进制已完成通知”；前者不代表后两者完成。原始许可证和版权声明均保持不变。

## 装配源码中的代码与资源

**GPL 专项补充：**文本补丁实际引入 8 个带 `GPL-2.0-only` 标记的运行时头文件，并进入原生编译链。逐文件来源、固定版本、修改记录和未决事项见 [GPL 组件清单](gpl-components.md)；随附 [GPL v2 正文](../licenses/GPL-2.0-only.txt)。以下 MIT 等组件列表不是整个原生 Mod 或装配运行时的单一许可结论。

Lotuskit 固定版本的[原始 LICENSE](../licenses/Lotuskit-LICENSE)完整保留，包含 GPL v2 及其自列其他组件通知，不代表这些其他组件均进入本项目补丁。装备数据的 [Marc Robledo MIT 原始通知](../licenses/Marc-Robledo-equipment-MIT.txt)也完整保留；生成头的 GPL 标记不抹去该来源条件。作者链、ABI 表达和生成数据权利的未确认部分继续标为待人工核验。

本仓库不携带完整上游源码树或二进制，但文本补丁包含实际源码及上下文。下列路径相对脚本装配后的 `MacNativeGames/`；保留的核对结果来自迁移前快照，实际使用时仍应核对锁定版本与补丁。本次读取了所列本地许可、相关源文件头、工程引用及补丁入口；没有重建二进制或把目录名当作完整权属证据。

| 组件与实际位置 | 来源、适用许可和本地证据 | 修改/核验边界 |
| --- | --- | --- |
| d2r NSO 改写与工具：`games/totk/third_party/d2r/` | [d2r-mobile](https://github.com/jhaizhou-ops/d2r-mobile)；随附 [MIT](https://github.com/ly05010419/MacNativeGames/blob/f3e2f661dfc05d7f6708c903ea513c297db195f1/games/totk/third_party/d2r/LICENSE)，声明 `Copyright (c) 2026 jhaizhou`，与当前上游 LICENSE 文本相符 | 本项目适配代码；精确导入提交、逐文件差异和完整归属链**待人工核验**，不声称所有内容原创 |
| d2r_gfx 宿主/NVN 层：`games/totk/third_party/d2r_gfx/` | 沿用 d2r-mobile 通用部分，随附 [MIT](https://github.com/ly05010419/MacNativeGames/blob/f3e2f661dfc05d7f6708c903ea513c297db195f1/games/totk/third_party/d2r_gfx/LICENSE)，声明 `2026 jhaizhou` | 本项目有扩展；精确上游版本与逐文件来源**待人工核验**；子目录其他许可不能被此 MIT 覆盖 |
| deko3d 派生贴图布局：`games/totk/third_party/d2r_gfx/gfx/nvn/nvn_tex.c` | 源文件头明确记录基于 deko3d `source/dk_image.cpp` 并修改块高规则；随附 [zlib 文本](https://github.com/ly05010419/MacNativeGames/blob/f3e2f661dfc05d7f6708c903ea513c297db195f1/games/totk/third_party/d2r_gfx/LICENSE.deko3d)，声明 `2018–2020 fincs` | 已有派生来源与修改说明；精确上游提交及复用范围**待人工核验**；保留原始通知，不冒充原作 |
| bcdec 0.985：`games/totk/third_party/d2r_gfx/third_party/bcdec/` | `bcdec.h` 标明作者 Sergii “iOrange” Kudlai 和版本；[随附许可](https://github.com/ly05010419/MacNativeGames/blob/f3e2f661dfc05d7f6708c903ea513c297db195f1/games/totk/third_party/d2r_gfx/third_party/bcdec/LICENSE)为 **MIT OR Unlicense**，不是无条件忽略版权通知 | 按实际选择的许可履行条件；当前文件与上游版本的完整差异**待人工核验** |
| 翻译器前端：`games/totk/tools/totk_xlate/` | d2r-mobile 派生，随附 [MIT](https://github.com/ly05010419/MacNativeGames/blob/f3e2f661dfc05d7f6708c903ea513c297db195f1/games/totk/tools/totk_xlate/LICENSE)，声明 `2026 jhaizhou`；`Service.cs` 与 `patches/` 为实际构建输入 | 本项目有修改，原有版权不因此转移；精确来源映射**待人工核验** |
| Ryujinx 子集：`vendor/ryujinx/` | [随附 MIT](https://github.com/ly05010419/MacNativeGames/blob/f3e2f661dfc05d7f6708c903ea513c297db195f1/vendor/ryujinx/LICENSE.txt)，声明 `Ryujinx Team and Contributors`；含 `Ryujinx.Graphics.Shader`、`Ryujinx.Common`、`Spv.Generator`；[子项目许可](https://github.com/ly05010419/MacNativeGames/blob/f3e2f661dfc05d7f6708c903ea513c297db195f1/vendor/ryujinx/src/Spv.Generator/LICENSE)也需保留 | vendor README 自述 1.3.2，不等于已验证精确提交。发布脚本在临时副本应用 `patches/*.patch`；完整来源、已应用修改和子项目逐文件归属**待人工核验** |
| Ryujinx.Audio 派生效果：`games/totk/runtime/audio_reverb.c`、`audio_effects.c` | 两文件头明确记载移植来源、版权和 [MIT 文本](https://github.com/ly05010419/MacNativeGames/blob/f3e2f661dfc05d7f6708c903ea513c297db195f1/games/totk/third_party/licenses/Ryujinx-Audio.txt) | 已确认文件头；此前把整个 mixer 一并写为移植代码的范围没有逐文件证据，`audio_mixer.c`/其他音频文件的具体复用边界**待人工核验** |
| 预编译翻译器：`games/totk/prebuilt/macos-arm64/totk_xlate` | 配套 [构建记录](https://github.com/ly05010419/MacNativeGames/blob/f3e2f661dfc05d7f6708c903ea513c297db195f1/games/totk/prebuilt/macos-arm64/README.md)和 `.sha256`；`publish_native.sh` 调用 .NET 10 NativeAOT，引用上述源码及补丁 | 源码许可证已找到，但实际 SDK/runtime、NuGet 嵌入组件、构建对应性与所需通知的完整清单**待人工核验**；不能只标“整个二进制 MIT” |

## 构建时取得或链接的代码

`build_app.py` 固定 SPIRV-Cross 与 hactool 提交；这些源码不在本公开仓库内。本次只读核对外部构建缓存的对应 Git HEAD、许可和文件头，不修改缓存。Opus/libvpx 版本仅是本机核查样本，不据此断言历史 Release 使用了同一版本。

| 组件 | 实际构建证据与许可证 | 发行与待核验事项 |
| --- | --- | --- |
| SPIRV-Cross | 固定 `aa217aeb6c9f0ace7a0ab233b28807edf45eb165`；[根 LICENSE](https://github.com/KhronosGroup/SPIRV-Cross/blob/aa217aeb6c9f0ace7a0ab233b28807edf45eb165/LICENSE) 为 Apache-2.0。脚本编译的 11 个 `.cpp` 文件头均标 **Apache-2.0 OR MIT**；该树还含 `LICENSES/` 的 MIT、Apache-2.0、CC-BY-4.0、KhronosFreeUse 文本 | 不再将所有文件一概写成单一 Apache-2.0。实际编入的头文件/资源、所选许可及应附通知**待人工核验**；目录中有某许可不代表该许可对应内容一定进入二进制 |
| hactool | 固定 `1d64a83450e025622f3468c28fc4164dad2c5ef6`；缓存根 LICENSE 为 ISC，声明 `2018 SciresM`；[固定提交来源](https://github.com/SciresM/hactool/tree/1d64a83450e025622f3468c28fc4164dad2c5ef6) | `build_app.py` 对 `main.c`/`nca.c` 加入私有 title-key、受限 base 文件/BKTR 处理等修改；不能称原版未修改。为外部合并工具，是否进入某个成品须按实际清单判断；再分发须保留 ISC 通知 |
| hactool 内嵌 mbedTLS | 固定 hactool 树的 `mbedtls/`，`version.h` 标 2.6.1；其 LICENSE 指向 `apache-2.0.txt`，并明确逐文件例外；所读版本头为 Apache-2.0、ARM 原有版权 | 不把现代 mbedTLS 默认许可套到此旧快照。全部参与编译文件及例外**待人工核验**；分发 hactool 二进制时一并核查内嵌 mbedTLS 所需许可/通知 |
| libopus | `games/totk/Makefile` 显式链接 `/opt/homebrew/opt/opus/lib/libopus.a`；本机样本 1.6.1 的 COPYING 与[上游同版本文本](https://github.com/xiph/opus/blob/v1.6.1/COPYING)相符，为 BSD 三条款式文本，另列专利许可引用 | 二进制分发材料需再现对应版权、条件与免责声明；不能因静态链接而省略。实际 Release 所用版本、构建选项、子组件/专利声明**待人工核验** |
| libvpx | Makefile 显式链接 `/opt/homebrew/opt/libvpx/lib/libvpx.a`；本机样本 1.17.0 的 LICENSE 与[上游同版本文本](https://github.com/webmproject/libvpx/blob/v1.17.0/LICENSE)相符，BSD-3-Clause，声明 WebM Project authors | 二进制发行需保留对应通知；实际版本、嵌入子组件和 PATENTS 等发行材料**待人工核验**，不据根许可证推断专利清单齐备 |
| .NET runtime / NativeAOT | 翻译器工程 `TargetFramework=net10.0`，发布脚本 `PublishAot=true`；[.NET 10.0.0 LICENSE](https://github.com/dotnet/runtime/blob/v10.0.0/LICENSE.TXT) 为 MIT，版权属于 .NET Foundation and Contributors；同版本另有 [THIRD-PARTY-NOTICES](https://github.com/dotnet/runtime/blob/v10.0.0/THIRD-PARTY-NOTICES.TXT) | 10.0.0 文本仅为明确标识的参考，不是当前二进制 runtime 版本证明。无需外装运行时不等于未嵌入运行时；实际补丁版本、NativeAOT 和第三方 notice 集合**待人工核验** |

## 其他不能遗漏的依赖与素材

外链 DataPacks 的范围与来源已单独列为[内容来源说明](https://github.com/kailous/native-adventure-kit/blob/main/docs/data-pack-sources.md)：游民地图/攻略、社区宝箱/图鉴、中文文本和游戏派生地形分别处理，不统称游民或项目原创。当前地图标记 SVG 的维护源由维护者说明为手工临摹；该制作说明不替代原参考设计权利核验。社区 paiyge/TOTK-compendium 的原 MIT 通知另附于 [DataPack-paiyge-MIT.txt](../licenses/DataPack-paiyge-MIT.txt)，不覆盖其他数据来源。

- `vendor/ryujinx/src/Ryujinx.Common/Ryujinx.Common.csproj` 实际引用 Microsoft.IO.RecyclableMemoryStream、MsgPack.Cli、Humanizer、Gommon。版本声明在 `Directory.Packages.props`，但没有本次预编译产物的完整 restore/嵌入清单。各包及传递依赖的许可、裁剪结果和二进制通知均**待人工核验**，不能把 props 中所有包视为都已链接。
- `games/totk/requirements.txt` 列出 cryptography、lz4、capstone、nsz。它们不是这份源码快照中的 vendor 源码；实际安装版本的许可、传递/原生依赖和是否随其他成品分发**待人工核验**。
- 配套地图 App（Release 成品）与原生游戏 App 不是同一产物。已定位地图成品中的 Python 运行时、图像库、ngrok 及 `webui/icons/reicon/LICENSE`；完整版本、各组件分发条件、应附通知及图片/字体权限均**待人工核验**。此表不是地图二进制的完整 SBOM，也不将 ngrok 默认认定为 MIT。
- 源码 `games/totk/assets/branding/loading/` 有设计来源记录和游戏标识；用户提供设计、公开下载或 Wiki 收录不等于第三方再分发许可。地图、攻略、图鉴、装备/amiibo 图标及 DataPacks（包括外部存储副本）的授权仍需独立核实。

## 发行时应如何使用本清单

MIT/ISC 组件按各自条件保留版权及许可通知；BSD 类二进制按对应许可在随附文档/材料中再现通知；zlib 派生源码保留通知并标明修改。选择 Apache-2.0 路径时按其第 4 条提供许可副本、保留适用声明、标明修改，并处理原发行物存在的适用 NOTICE。双重许可按实际选择核对，不能只列 SPDX 名称代替应附文本。

静态链接、AOT 或“工具仅在构建时运行”不会自动消除相应分发义务；构建时使用也不代表该工具必然被分发。具体哪些通知随哪个成品提供，以实际发行清单和许可文本为准。

原始许可证保持不变；旧 Release 后续已按维护者授权移除，见[历史处理记录](historical-release-review.md)。不根据目录搬迁、补丁格式或历史清理认证合规。下一次发行前应完成 [发布前清单](../LICENSE_SCOPE.md#发布前简要清单)，尤其补齐实际二进制组件清单及法律/许可人工核验；清单完成仍不等于法律合规认证。

## 新增地图源码导出

map-client/ 包含项目地图程序及随附 MIT 的 Reicon 通用图标；Reicon 原 LICENSE 和 SOURCE.md 保持原样。游戏图像、Figma 原稿、内容数据库和真实匹配表未复制。程序内物品/amiibo 名称与 ID 表仍保留，需区分程序、事实/名称和数据集合的权利。PyInstaller、Python、Pillow 及可选 ngrok 的成品发行通知按实际包含内容核查，默认构建不下载 ngrok。

## 直播接收器（外部输入）

地图2.0.24集成使用saermart/DouyinLiveWebFetcher，记录上游提交40a904bdb0561a5a9c958a95634a29681cc4fbf4；逐文件摘要在map-client/douyin-source.json。官方源码通过prepare_live_receiver.py进入用户外部工作区，接收器及其LICENSE随用户本地构建的地图保留。原许可为AGPL-3.0，不改为根MIT；上游README的声明与许可应分别阅读。map-client/douyin/danmaku_hook.py为现有集成适配器，不收录私人直播规则。mini_racer、betterproto、requests、websocket-client和PyExecJS遵守各自许可，构建者需核对二进制依赖的通知。
