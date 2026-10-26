# 地图与游戏相关素材清单

核对日期：2026-10-26。清单记录外层开发项目的素材来源和运行副本，不将图片、数据库或游戏数据复制到本仓库。完整逐文件列表见 [game-assets.json](game-assets.json)，物品/amiibo 中文名称及文件名见 [逐项名称清单](item-icons.md)。

## 分类汇总

| 类别 | 源位置 | 文件数 | 大小 MiB | 来源与处理建议 |
| --- | --- | ---: | ---: | --- |
| 游戏点位 SVG | `assets/game-icons` | 53 | 0.11 | 来源/授权待人工核验；暂不随源码导出 |
| 许愿物品原始图标 | `assets/item-icons` | 378 | 13.10 | 来源明确为 ROM 提取，应外置/替换或核实授权 |
| amiibo 官方商品图 | `assets/amiibo` | 32 | 0.39 | 官方图片，需独立核实再分发许可 |
| 品牌/界面素材：logos | `assets/branding/logos` | 6 | 1.10 | 来源/授权待人工核验；暂不随源码导出 |
| 品牌/界面素材：badges | `assets/branding/badges` | 3 | 0.34 | 来源/授权待人工核验；暂不随源码导出 |
| 品牌/界面素材：textures | `assets/branding/textures` | 1 | 0.24 | 来源/授权待人工核验；暂不随源码导出 |
| 品牌/界面素材：decorations | `assets/branding/decorations` | 2 | 19.40 | 来源/授权待人工核验；暂不随源码导出 |
| 品牌/界面素材：icons | `assets/branding/icons` | 18 | 0.02 | 来源/授权待人工核验；暂不随源码导出 |
| 品牌/界面素材：figma-sidebar | `assets/branding/figma-sidebar` | 14 | 0.50 | 来源/授权待人工核验；暂不随源码导出 |
| 品牌/界面素材：figma-map-ui | `assets/branding/figma-map-ui` | 22 | 0.20 | 来源/授权待人工核验；暂不随源码导出 |
| 品牌/界面素材：figma-navigation | `assets/branding/figma-navigation` | 20 | 0.02 | 来源/授权待人工核验；暂不随源码导出 |
| 品牌/界面素材：figma-game-control | `assets/branding/figma-game-control` | 21 | 0.08 | 来源/授权待人工核验；暂不随源码导出 |
| 旧版地图分类图标 | `webui/icons` | 22 | 0.11 | 来源/授权待人工核验；暂不随源码导出 |
| 通用 Reicon UI 图标 | `webui/icons/reicon` | 23 | 0.03 | 随附 MIT，可按许可保留；版本来源仍需核验 |
| 散列名界面图片 | `webui/ui-assets` | 120 | 0.47 | 来源/授权待人工核验；暂不随源码导出 |
| 离线攻略正文与图片 | `webui/offline` | 2459 | 110.15 | 来源/授权待人工核验；暂不随源码导出 |
| 图鉴图片 | `webui/compendium` | 644 | 58.33 | 来源/授权待人工核验；暂不随源码导出 |
| 原生游戏原加载素材（当前 kit 已剥离） | `MacNativeGames/games/totk/assets/branding/loading` | 3 | 3.52 | 来源/授权待人工核验；暂不随源码导出 |
| 生成的运行副本 | `webui/icons/game` | 53 | 0.11 | 生成副本，不重复维护 |
| 生成的运行副本 | `webui/item-icons` | 378 | 13.10 | 生成副本，不重复维护 |
| 生成的运行副本 | `webui/amiibo` | 32 | 0.39 | 生成副本，不重复维护 |
| 生成的运行副本 | `webui/branding` | 84 | 0.96 | 生成副本，不重复维护 |

## 已能确认的来源

- **378 张物品图标来自游戏 RomFS 提取**，项目记录指向 `RomFS/UI/Tex/Icon/`；不能统一说成 Wiki 获取。
- **32 张 amiibo 商品图来自 Nintendo 官方页面**，来源/URL/哈希记录在 `data/amiibo-images.json`；官方公开展示不等于允许再分发。
- **53 个游戏点位 SVG** 是维护源，包含克洛洛果实、破魔之根、神庙、鸟望台、怪物和个人标点等。制作/还原过程及各项权利仍需核验。
- Figma 快照、用户提供 Logo 和装饰有来源记录，但“用户提供”不能自动证明全部底层游戏图像已授权。
- Reicon 通用 UI 图标目录含 MIT 许可，版权声明为 `2025 REICON`；与游戏图片分开处理。

## 点位 SVG 逐项名称

- `个人标点 131.svg`
- `个人标点 132.svg`
- `个人标点 133.svg`
- `个人标点 134.svg`
- `个人标点 135.svg`
- `个人标点 136.svg`
- `主线剧情.svg`
- `井.svg`
- `人马（莱尼尔）.svg`
- `克洛洛果实 x2.svg`
- `克洛洛果实.svg`
- `升级素材.svg`
- `卡邦达立牌.svg`
- `古代研究所.svg`
- `地下.svg`
- `地洞入口.svg`
- `地面.svg`
- `大妖精之泉.svg`
- `天空.svg`
- `女神雕像.svg`
- `宝箱.svg`
- `岩石巨人.svg`
- `左纳乌制造机.svg`
- `弓与箭.svg`
- `怪物营地.svg`
- `情节挑战.svg`
- `旅馆.svg`
- `杂货店.svg`
- `村庄.svg`
- `武器.svg`
- `残旧的地图.svg`
- `洞穴入口.svg`
- `滑翔伞布料.svg`
- `烹饪点.svg`
- `特殊NPC.svg`
- `独眼巨人.svg`
- `珠宝店.svg`
- `盾牌.svg`
- `矿场.svg`
- `破魔之根.svg`
- `神庙.svg`
- `神殿.svg`
- `设计图石板.svg`
- `贤者的遗志.svg`
- `迷你挑战.svg`
- `通用地点.svg`
- `防具.svg`
- `防具店.svg`
- `集市.svg`
- `驿站.svg`
- `魔犹伊遗失物.svg`
- `鸟望台.svg`
- `龙之泪.svg`

## 需要优先人工查看的界面素材

| 文件 | 来源/疑问 |
| --- | --- |
| `assets/branding/logos/logo.svg` | 游戏标识、角色、纹理或设计素材可能混合；需看图及原始授权记录 |
| `assets/branding/logos/native-map-app.png` | 游戏标识、角色、纹理或设计素材可能混合；需看图及原始授权记录 |
| `assets/branding/logos/图文攻略.svg` | 游戏标识、角色、纹理或设计素材可能混合；需看图及原始授权记录 |
| `assets/branding/logos/图鉴.svg` | 游戏标识、角色、纹理或设计素材可能混合；需看图及原始授权记录 |
| `assets/branding/logos/攻略.svg` | 游戏标识、角色、纹理或设计素材可能混合；需看图及原始授权记录 |
| `assets/branding/logos/路书.svg` | 游戏标识、角色、纹理或设计素材可能混合；需看图及原始授权记录 |
| `assets/branding/decorations/desktop/badge.svg` | 游戏标识、角色、纹理或设计素材可能混合；需看图及原始授权记录 |
| `assets/branding/decorations/desktop/hero.png` | 游戏标识、角色、纹理或设计素材可能混合；需看图及原始授权记录 |
| `assets/branding/badges/01.svg` | 游戏标识、角色、纹理或设计素材可能混合；需看图及原始授权记录 |
| `assets/branding/badges/02.svg` | 游戏标识、角色、纹理或设计素材可能混合；需看图及原始授权记录 |
| `assets/branding/badges/03.svg` | 游戏标识、角色、纹理或设计素材可能混合；需看图及原始授权记录 |
| `assets/branding/textures/01.svg` | 游戏标识、角色、纹理或设计素材可能混合；需看图及原始授权记录 |

## 地图与数据包

- `webui/map-tiles.sqlite`：约 1.75 GiB 的地图瓦片数据库。
- `webui/surface.png`、`sky.png`、`depths.png`：地图底图。
- `webui/offline/`：缓存攻略文章及图片；`webui/compendium/`：图鉴图片。
- `dist/data-packs/hyrule-1.0.0.totkpack` 与 `guides-zh-CN-1.0.0.totkpack`：集合文件，内容与上述源及地形资源有重叠，当前 kit 不提供。
- 点位/任务/图鉴/存档匹配 JSON 也已列入完整清单，需区分程序匹配规则、事实数据、游戏派生数据和第三方文字内容，不能一律认定为原创代码。

## 程序内游戏名称与 ID 表

`backend/spawn_catalog.py` 与 `backend/amiibo_catalog.py` 含物品/amiibo 名称及 ID，用于协议和选择器。地图源码导出保留这两份代码表，不包含相应图片；不应将游戏名称和数据集合一概视为项目原创美术或已完成授权。它们也已列入完整 JSON 清单。

## 未发现与检查边界

在本次扫描的 assets/、webui/ 中未发现单独的字体、音频或视频文件；这不表示游戏、ROM、App 内嵌内容或外部目录没有这些资源。没有检查真实存档、密钥或 ROM。文件数、来源和许可判断均不构成合规认证。
