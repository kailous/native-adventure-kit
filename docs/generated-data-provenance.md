# 生成数据的来源与未决事项

核查日期：2026-10-26。本记录只保存来源链、哈希和核验状态，不复制游戏素材、CSV、Actor pack 或其他原始数据。许可边界见 [GPL 清单](gpl-components.md)与[第三方声明](third-party-notices.md)。来源可追溯与取得再分发授权是不同事项。

## 装备默认值

已确认的维护链：归档 savegame-editors 装备表 → 外层 `mod/telemetry/equipment_defaults.hpp` → `tools/build/sync_native_mod_assets.py` → 补丁中的 `games/totk/runtime/equipment_defaults.h`。

- 核查归档为 [marcrobledo/savegame-editors@b4db8cd11157c6d5ae54a0a5edc88dba82aebe9d](https://github.com/marcrobledo/savegame-editors/tree/b4db8cd11157c6d5ae54a0a5edc88dba82aebe9d)，文件 `zelda-totk/zelda-totk.class.equipment.js`。归档版本不是精确导入版本的证明。
- 本次已核对去重后的默认耐久 206 项、余料耐久 128 项，对应值与归档相符；不宣称整个归档表逐项完整复制。
- [原 MIT 通知](../licenses/Marc-Robledo-equipment-MIT.txt)与该固定归档根 LICENSE 字节一致，保留 Marc Robledo 及其自列 Octicons/GitHub Inc. 通知。
- 维护输入和生成头已有 GPL-2.0-only 标记。原 MIT 来源通知继续保留，不能由输出标记抹去；数据事实、选择编排和适配表达分别核验。

待核验：最初导入人、精确导入提交、转换和筛选依据、全部贡献者及数据权利。外层 Git 的 2026-10-12 基线记录不足以证明初次创作或授权。

## 物品目录

已确认的生成逻辑：`tools/data/generate_spawn_catalog.py` 读取中文 `PouchContent.csv`、`totk-actor-names.json`，并按外部 Actor pack 是否存在筛选，再输出 `mod/telemetry/spawn_items.hpp` 与 Python 物品目录；sync 工具进一步生成 native `spawn_catalog.h`。

- 当前 C++ 维护目录与地图 Python 目录均为 **378 个唯一 actor**，顺序完全一致，目录 hash 均为 `6e5b9280a55389ba`。
- 目录顺序参与请求编号匹配，hash 不一致时现有客户端会拒绝生成请求；发布治理不修改顺序或字段。
- `spawn_items.hpp` 无 SPDX，sync 工具固定写入输出 GPL 标记。不能由此认定原始名称、ID、译文或整个数据集合已获 GPL/MIT 授权。
- CSV 和 actor JSON 的初次获取网站、导出工具、固定原始版本及授权材料尚未找到。不能根据文件名断言来自 Wiki、Nintendo 官方或某个公开数据项目。
- 生成器引用的外部 `untitled folder/Pack/Actor` 路径当前没有找到对应 378 个输入文件；本次没有恢复、下载或重新生成这些游戏数据。现有输出比对成功不等于生成流程已从原始输入完整复现。

待核验：输入获取及许可记录、Actor pack 筛选清单、中文译文/数据集合权利，以及维护输入和生成器应如何作为首选修改形式合法提供。不得以“公开下载”“事实常量”或“生成器写了 SPDX”代替核查。

## 本次读取的证据指纹

这些路径为维护者外层工作区的相对路径，除明确的 `native-adventure-kit/` 文件外，不表示它们随当前项目分发。哈希用于识别核查样本，不授予权利。

| 样本 | 字节数 | SHA-256 |
| --- | --- | --- |
| `tools/build/sync_native_mod_assets.py` | 2066 | `92b3838f633ce8a64995017b194521ac80dbc9cf4dba4bff9d59d32d348c7fb3` |
| `tools/data/generate_spawn_catalog.py` | 1525 | `ea826cd5a41a2276664ebd99791e6c62f2ea2def3be3522f21f434cf76919b17` |
| `mod/telemetry/equipment_defaults.hpp` | 9619 | `8f422e03e3d019695c3c200c429658ce589de4c5d6796a64f4d0e3fdd24a6b2e` |
| `mod/telemetry/spawn_items.hpp` | 7684 | `52f49b52b4ae3fdf55baf9d1edbe7a507bc3d30ed0ffde015ed714065919f64d` |
| `data/compendium/zhCN/ActorMsg/PouchContent.csv` | 277153 | `82e004a87bdb019986ff11468062829006539c6423feb8385aee630f6b3163e1` |
| `data/compendium/totk-actor-names.json` | 55458 | `9ad4982edaecca94a0ccc1188a7a2e063bca47380b85a95f176293453776cd22` |
| `native-adventure-kit/map-client/backend/spawn_catalog.py` | 21835 | `4e3c91918a120b21485fa7715374bb73978f9b91a21cb0e0b55bac82d6702f34` |

## 下一步与当前限制

1. 维护者补充实际来源 URL、固定版本、取得方式、原通知及转换记录，无法找到的继续保持待核验。
2. 区分可依法提供的生成器/维护输入与无权分发的游戏内容，再决定补充源码材料；此次没有擅自加入输入文件。
3. 数据值、actor 顺序或生成逻辑变动时重新核对 native 与地图目录及 hash，不通过更新快照掩盖来源缺口。

本记录没有将这些数据认证为原创、独立授权或法律合规。生成源是否完整随附仍是未关闭事项，见 [GPL 待办](gpl-components.md#本次补充与待办)。
