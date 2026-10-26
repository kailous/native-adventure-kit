# DataPacks 内容来源说明与清单

核查日期：2026-10-26。此文档区分数据的获取来源、项目整理过程、图标制作方式及未确认的权利，不将所有内容归为项目原创或统一授予 MIT。

[百度网盘分享](https://pan.baidu.com/s/1iEN5GpfuFdfOlFbewLQHDQ?pwd=totk)，提取码 `totk`。链接由维护者提供；自动浏览未能解析百度分享页，本次没有下载或逐字核验网盘目录。以下内容以本地实际核验的两个包为准，网盘文件应按名称、大小和 SHA-256 比对。[机器可读记录](inventory/data-pack-sources.json)仅含元数据，不提供实际内容。

## 文件与版本

| 文件 | 大小（字节） | SHA-256 |
| --- | ---: | --- |
| hyrule-1.0.0.totkpack | 3,529,551,872 | `058032c9c9a22dac991bacacbf1408c9d1f651c89ec9b20b329c36b4f4f6b16c` |
| guides-zh-CN-1.0.0.totkpack | 181,284,864 | `0e9b995e748756fbca9700419efc5177169476a58f146d2c8ac7ba6881dc48e6` |

两个包均为 SQLite 数据容器，格式 `totkpack/1`、contentSchema 1。包内 `gameVersion=1.0.0` 是历史内容元数据，不表示项目支持运行游戏 1.0.0；当前维护主线仍是原生 1.4.3，也没有据此认证这些历史点位/地形全部适配 1.4.3。

## 地图包 hyrule：不是单一来源

实际包含 **95,821 个瓦片记录、13,818 个资源记录**。资源中的 13,809 项为 terrain，其余为 9 个顶层文件。

| 内容 | 包内位置/数量 | 已确认来源与处理 | 尚未确认 |
| --- | --- | --- | --- |
| 三层地图瓦片 | tiles 表，95,821 项 | 游民星空图像服务；本地下载器使用 `image.gamersky.com` 的 ground / underground / sky 瓦片路径，再存入 SQLite | 网站提供下载不等于其拥有全部底层游戏图像权利；再分发许可待核验 |
| 地图元数据、分类与区域 | catalog.json、catalogs.json、regions.json | 游民星空互动地图/API 下载记录；包内 catalog.json 与本地 mapId 18 原始响应结构和值一致 | 具体整理版本和各贡献人权利仍需按原始记录判断 |
| 地图点位与说明 | gamersky-archive.json，3,184 点、50 类 | 游民星空 mapId 18/19/20 点位及详情；项目作坐标转换、分类和本地整理，记录原点位 URL | 坐标转换不转移文字、图片或数据集合的权利 |
| 任务点位 | quest-points.json，181 点 | 游民星空点位，带原来源 URL；项目转换坐标 | 原始任务文字与数据集合再分发权限待核验 |
| 宝箱与额外任务数据 | extra-data.json，1,202 个宝箱、125 个任务 | 社区 paiyge/TOTK-compendium 的 backup.sql，经项目解析、去重和坐标转换 | 不能归为游民内容；数据许可与游戏底层表达分别判断 |
| 三张概览底图 | surface.png、sky.png、depths.png | 与本地运行底图对应；维护者说明地图来源为游民星空，瓦片下载链也指向该站 | 尚未找到这三张文件完整的原始下载/拼接记录，逐图来源和授权待核验，不补造具体 URL |
| 高度场 | terrain/**/*.u16，11,247 项 | 本地归档的游戏资源解码结果，来源路径记录含 TerrainArc 的高度资源；项目转为数据格式 | 属游戏派生数据，不是游民地图瓦片；原资源取得和再分发权限待核验 |
| 碰撞网格 | terrain/**/*.mesh，2,560 项 | 归档的游戏世界碰撞资源解码结果，经项目转换 | 原游戏资源及转换数据的权利不能由项目 MIT 自动覆盖 |
| 地形索引和覆盖说明 | terrain/index.json、terrain/coverage.json | 项目按上述资源生成索引、路径及覆盖信息 | 索引生成不等于原数据原创；覆盖不完整，未进行游戏内完整验收 |

地形打包入口明确只导入高度场和静态碰撞数据，没有导入已退役的导航网格/路由代码，包声明 `routingIncluded=false`、`fullMapComplete=false`。此处说明历史数据，不恢复或承诺导航执行功能。

游民来源入口：[互动地图](https://www.gamersky.com/tools/map/zeldabotw2/)。本地可核对的下载接口包括 `mapapi.gamersky.com/map/getMap`、`landmark/getLandmarkList` 和 `landmark/getLandmark`；瓦片路径记录为 `image.gamersky.com/webimg13/db/game_map/zelda_tok/tilesHD_Zeldamaps_5/` 下各层级。接口来源不是网站或底层素材的再分发许可证。

社区数据归档：[paiyge/TOTK-compendium@48af503758570acc88da54a9a7938919b631367b](https://github.com/paiyge/TOTK-compendium/tree/48af503758570acc88da54a9a7938919b631367b)。其[原始 MIT 通知](../licenses/DataPack-paiyge-MIT.txt)完整保留 Tianyao He、Paige Norris、Mian Wang 的版权行；该通知不替代其他来源和游戏素材的权限。

## 攻略与图鉴包 guides：混合文本、图片和整理结果

实际包含 **3,107 个资源记录**：4 个顶层 JSON、offline/ 的 2,459 项，以及 compendium/ 的 644 项。

| 内容 | 包内位置/数量 | 来源与项目处理 | 权利边界 |
| --- | --- | --- | --- |
| 攻略正文及缓存图片 | offline/：166 个 JSON、2,290 个 JPG、3 个 PNG | 由游民星空点位关联的原文/媒体链接缓存并结构化，原 URL 线索在整理索引中保留 | 转载、截图、水印和原作者文字不能一概归给项目或网站；逐篇授权待核验 |
| 攻略结构和关联 | structured-guides.json、quest-guide-links.json | 项目根据原点位和文章建立结构及任务关联 | 项目整理部分与嵌入的第三方内容分别判断 |
| 主线攻略整理 | main-story.json | 包内来源记录指向[游民主线攻略页面](https://www.gamersky.com/handbook/202305/1596273.shtml)，由本地工具整理 | 不因转换为 JSON 而取得原文再分发权 |
| 图鉴与装备数据 | compendium.json | 生成器和包内 sources 字段指向 Hyrule-Compendium-API、paiyge/TOTK-compendium、totk-resources；还读取 TOTK-helper、savegame-editors 和本地中文游戏消息 CSV | 各来源的程序许可、数据集合、译文和底层游戏表达分别核验 |
| 图鉴及防具图片 | compendium/：509 个 JPG、135 个 PNG | 一部分按 Hyrule-Compendium-API 返回的图片地址缓存；防具图片从本地 TOTK-helper 归档复制 | API/仓库的代码许可不自动证明所有游戏图像已授权再分发 |

已记录的来源入口与局限：

- [Hyrule-Compendium-API](https://github.com/gadhagod/Hyrule-Compendium-API)：图鉴条目及图片地址线索；本次未确认最初取得快照的完整版本及所有图片权利。
- [paiyge/TOTK-compendium](https://github.com/paiyge/TOTK-compendium)：宝箱、物品、任务和区域等社区数据，使用上述固定归档及 MIT 通知。
- [sagunkayastha/TOTK-helper@f0823bd4ab013858f522f52d053096dbca358eee](https://github.com/sagunkayastha/TOTK-helper/tree/f0823bd4ab013858f522f52d053096dbca358eee)：防具数据与图片的本地归档来源。所读 LICENSE 虽为 MIT 文本，但版权行含作者占位符，真实作者和图片权利仍待核验，不据仓库名补写作者。
- [marcrobledo/savegame-editors@b4db8cd11157c6d5ae54a0a5edc88dba82aebe9d](https://github.com/marcrobledo/savegame-editors/tree/b4db8cd11157c6d5ae54a0a5edc88dba82aebe9d)：中文名称/游戏 ID 匹配线索；原 MIT 通知保留，见[现有来源通知](../licenses/Marc-Robledo-equipment-MIT.txt)。
- [zoalasaurusrawr/totk-resources](https://github.com/zoalasaurusrawr/totk-resources)：包内 sources 列出的来源线索；不能仅凭该字段确认它对应每一张图或每一条数据，精确导入范围待核验。
- 本地中文游戏消息 CSV：图鉴本地化工具实际读取，但最初取得方式和授权记录无法还原，继续标为待核验，见[生成数据台账](generated-data-provenance.md)。

## 地图标记 SVG：维护者手工临摹制作

维护者于 2026-10-26 明确说明：**当前地图标记均由本人手工临摹为 SVG**。对应唯一维护源为 `assets/game-icons/` 的 **53 个 SVG**；`webui/icons/game/` 是工具同步的运行副本，不重复记作另一组原创作品。[逐项名称和文件指纹](inventory/game-assets.md#点位-svg-逐项名称)与[机器清单](inventory/game-assets.json)已同步这项制作来源说明。

该记录依据维护者说明，不表示对手工制作过程、参考原稿或每项授权作了独立鉴定。自行绘制/临摹的文件与被参考图形设计的权利应分开判断，不将临摹直接写成完全独立原创，也不把参考设计自动纳入根 MIT。

这 53 个 SVG 是 App 的界面资源；本次核对的两个 DataPacks 中没有独立 SVG 资源条目。分类 JSON 可能保留上游图标名称/URL，不能与实际手绘 SVG 文件混为一谈。该手工制作说明也不适用于另列的物品 RomFS 图标、amiibo 商品图片、图鉴图片、底图或其他界面装饰。

## 是否包含任天堂源代码

本次读取包格式、资源路径和若干解压样本，识别到 JSON、PNG/JPG、瓦片 BLOB、`.u16` 高度场和 `.mesh` 网格；未发现独立的 C/C++ 源文件、SDK 头文件、游戏可执行容器或密钥文件。打包入口导入的是内容数据，没有编译或导入原生运行时源码。

**这不是“没有任天堂受保护内容”的结论。**游戏图像、文本和从游戏资源解码的地形可能涉及与程序源码不同的权利；从游民或其他社区取得也不改变底层权利。未对每个 BLOB 做原始来源鉴定，不能凭扩展名保证绝无嵌入代码或其他内容。

## 核查范围与维护方式

- 两个包本次均实际重新计算整文件 SHA-256，读取 SQLite schema、metadata、资源目录，核对部分 JSON/二进制样本及其声明摘要；未运行包内内容，未修改或重新打包数据。
- 本文不是网盘上传记录，也未自动核对网盘文件；如分享内容更新，应重新核对文件摘要与此清单。
- 发布包入口、下载器及整理脚本作为来源证据读取；没有据此认证游民、API、社区仓库或项目作者对全部内容拥有再分发权。
- 根 MIT 不统一覆盖 DataPacks。来源注明、维护者接受风险、免费分享和更换存储平台都不构成额外授权。
- 建议网盘同目录提供本说明及适用的原始许可通知；本次没有操作网盘文件。未知原作者、原始素材和许可继续保持待核验，不编造确认结果。

其他边界见[授权范围](../LICENSE_SCOPE.md)、[第三方声明](third-party-notices.md)及[完整素材清单](inventory/game-assets.md)。本说明不构成法律合规认证。
