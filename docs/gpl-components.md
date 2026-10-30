# GPL 组件：许可、来源与修改记录

核对日期：2026-10-30。适用于 `upstream.lock.json` 锁定上游 `f1d00772df1ac3230268f3124bdeb6b7cc81a61c` 与当前 `patches/native-mod.patch`。补丁 SHA-256 为 `d140711ebe7ecbb12623fa9cb9f69ddac0c0ce3f2754342d3bbbb2f6808d1d57`。本次重新装配核验行号与文件哈希；保留既有许可与待核验事项，未将未知来源改为已授权。

[授权范围](../LICENSE_SCOPE.md) · [第三方声明](third-party-notices.md) · [使用说明](../使用协议.md) · [随附许可索引](../licenses/README.md)

结构化清单见 [gpl-components.json](gpl-components.json)，发布检查见[治理说明](release-governance.md)。生成数据的新增核验记录见[来源台账](generated-data-provenance.md)；旧附件另见[历史复核](historical-release-review.md)。这些记录未将待核验权利标为已关闭。

## 许可范围与当前发布形式

根 [MIT](../LICENSE) 继续用于作者有权许可的独立原创部分，不替代下列 GPL 声明及其他原始许可。8 个标记均为 `// SPDX-License-Identifier: GPL-2.0-only`，位于装配后文件第 1 行；不是测试字符串、引用示例或只包含许可名称的说明文件。它们是补丁实际引入的运行时代码/数据，在锁定上游文件树中不存在。

保留当前 GPL-2.0-only 声明，随附 [GNU GPL v2 正文](../licenses/GPL-2.0-only.txt)，不将其改为 MIT、双重许可或 GPL-or-later。SPDX 标记证明已有许可声明，不单独证明声明者拥有全部内容的权利。未知归属仍待人工核验。

当前发布项目源码、脚本、Skill、补丁和说明，不发行原生游戏 App。补丁中的实际源码仍属于分发内容，须核对 GPL v2 第 1、2 条的版权、免责、完整许可与修改通知。二进制第 3 条要求按实际对象码发行判断；用户在本机私下构建不自动使项目维护者成为该 App 的二进制发行者。

## 逐文件台账

所有目标路径均相对用户工作区装配出的 `MacNativeGames/`；补丁行号为一基物理行号。

| 补丁行 | 目标文件 | 声明 | 实际编译关系 |
| --- | --- | --- | --- |
| 8463 | `games/totk/runtime/camera_math.h` | GPL-2.0-only，第 1 行 | 相机数据解码、矩阵与方向校验；由 camera_probe.h 包含。 |
| 8498 | `games/totk/runtime/camera_probe.h` | GPL-2.0-only，第 1 行 | 有界对象扫描、虚表验证与缓存；由 telemetry.c:8 包含。 |
| 9095 | `games/totk/runtime/equipment_defaults.h` | GPL-2.0-only，第 1 行 | 默认耐久与余料耐久表；由 pouch_control.h:4 包含。 |
| 14750 | `games/totk/runtime/pouch_control.h` | GPL-2.0-only，第 1 行 | 武器、弓、盾字段读取、耐久恢复与锁定；由 native_control.c:60 包含。 |
| 14842 | `games/totk/runtime/quantity_control.h` | GPL-2.0-only，第 1 行 | 材料、料理、胶囊数组读取和数量 99 写入；由 native_control.c:61 包含。 |
| 15391 | `games/totk/runtime/spawn_catalog.h` | GPL-2.0-only，第 1 行 | 物品白名单、顺序及 catalog hash；由 spawn_control.h:7 包含。 |
| 15782 | `games/totk/runtime/spawn_control.h` | GPL-2.0-only，第 1 行 | 生成参数 ABI、游戏帧调用与结果观察；由 native_control.c:62 包含。 |
| 16833 | `games/totk/runtime/weather_control.h` | GPL-2.0-only，第 1 行 | 天气 setter、读回、锁定与状态清除；由 native_control.c:63 包含。 |

### 来源和逐文件修改记录

以下本地原生 Git 记录中的提交者字段均为 **Kailous**，只是导入/修改记录，不等于原作者版权证明，也不据此改写任何版权声明。日期是记录中的提交日期，不是最初创作日期。当前各文件未见独立的原作者版权行；不能把 GPL 正文的 FSF 文本版权当作这些代码的作者。

#### camera_math.h

- 来源：外层 mod/telemetry/camera_math.hpp 已标 GPL-2.0-only，注明 Lotuskit camera.hpp / 59dcfcc。通用数学、布局数据及实现表达需要分别判断。
- 修改记录：3395a20，2026-10-20，首次导入。
- 当前装配文件 SHA-256：`087105770bcf56906f01baa9801b6bd55c43a3e78f73d21f14dc0a2fd2ef7c32`。
- 作者与授权边界：具体原作者、逐段贡献与有效授权链待人工核验；保留现有标记和已知来源。

#### camera_probe.h

- 来源：本地新增相机发现实现，包含 camera_math.h 与运行时接口；未核实逐段外部原件，不能据关联关系把整个文件归给 Lotuskit。
- 修改记录：3395a20 首次导入；0e7ac62、f3936e9 于 2026-10-20 更新版本支持与相机适配。
- 当前装配文件 SHA-256：`f2685431c9e8f69f61dc7a496b7ab3beb9f1433cff6dd499045df3fa591ead88`。
- 作者与授权边界：具体原作者、逐段贡献与有效授权链待人工核验；保留现有标记和已知来源。

#### equipment_defaults.h

- 来源：外层 sync_native_mod_assets.py 从 equipment_defaults.hpp 生成；本次内存生成结果逐字一致。源注明来自归档 save editor，旁附 Marc Robledo MIT 通知。
- 修改记录：3395a20，2026-10-20，导入生成结果。
- 当前装配文件 SHA-256：`1e11884ee6c4f1c228a0fe633a6bec52bec91a87b07f0ace348b45b2e53bbeda`。
- 作者与授权边界：装备源通知为 Marc Robledo，生成和适配部分的完整作者链及数据权利待人工核验。

#### pouch_control.h

- 来源：本地导入的控制实现，依赖 equipment_defaults.h；完整原始创作/借鉴链未核实。
- 修改记录：3395a20 首次导入；0e7ac62 于 2026-10-20 更新控制适配。
- 当前装配文件 SHA-256：`56ba0320b04cfedc2f6f51b084d352c50c98fc10269a02c154fbdd530e08a8ca`。
- 作者与授权边界：具体原作者、逐段贡献与有效授权链待人工核验；保留现有标记和已知来源。

#### quantity_control.h

- 来源：本地导入实现，使用 pouch_control.h 的数组解析函数；逐段外部原件与作者链未核实。
- 修改记录：3395a20 首次导入；0e7ac62 于 2026-10-20 更新控制适配。
- 当前装配文件 SHA-256：`2d7d464f91e680c2e7b975f4b825495d2c1fb5dd3491f33ea3ebd40028eb6981`。
- 作者与授权边界：具体原作者、逐段贡献与有效授权链待人工核验；保留现有标记和已知来源。

#### spawn_catalog.h

- 来源：外层 sync_native_mod_assets.py 从 spawn_items.hpp 生成，逐字一致；输入无 SPDX，GPL 标记由生成器写入。更早生成流程读取名称 CSV、actor JSON 与 Actor pack 存在性，原始数据授权未核实。
- 修改记录：3395a20，2026-10-20，导入生成结果。
- 当前装配文件 SHA-256：`b8412049f5bbc4386f6ed0e18e84da209e5b1f8be1202ce857f6edd703ee3e1d`。
- 作者与授权边界：具体原作者、逐段贡献与有效授权链待人工核验；保留现有标记和已知来源。

#### spawn_control.h

- 来源：文件头明确指向 Lotuskit 59dcfcc 的 engineActor.hpp / bbBlackboard.hpp；已核对对应结构布局。必要 ABI 数据和可能派生表达的边界待人工核验。
- 修改记录：3395a20 首次导入；0e7ac62、f3936e9 于 2026-10-20 更新版本支持与生成适配。
- 当前装配文件 SHA-256：`08db9ace87e32136bf6f2b8157905030917b4800400595f771fc4944d080f4e0`。
- 作者与授权边界：具体原作者、逐段贡献与有效授权链待人工核验；保留现有标记和已知来源。

#### weather_control.h

- 来源：外层天气 ABI 检查工具有 Lotuskit WorldManagerModule 来源线索，但未确认完整实现的精确外部原件。
- 修改记录：802eec0 于 2026-10-20 首次导入；fba91a3 于 2026-10-21 修改。
- 当前装配文件 SHA-256：`30f1d5d62913679d2fef0e3ea555d92b75cfc96eddb1d2e70654db69ef8bfc95`。
- 作者与授权边界：具体原作者、逐段贡献与有效授权链待人工核验；保留现有标记和已知来源。

记录标识：`3395a20d60c82851bfe08f6a988bfc33cf665888`（导入）、`0e7ac6248500ea8d9955130ba71f81704576c47f`、`f3936e90e00b48e760d0154f7ea17fb1a5770950`、`802eec0caaba9f2c0ed380c5add75b9e980875c7`、`fba91a3a04396169348a4661229a1da66ecbd541`。这些是维护者本地原生历史的核查标识，不保证它们可从公共上游取得。以上不是全部 Git 历史或每行代码的来源证明，也不能替代对修改文件醒目通知要求的逐项核验。后续修改应记录实际修改者、日期和范围，并保留原声明。

## Lotuskit 来源和通知

固定来源：[aquacluck/totk-lotuskit@59dcfccd77b6d4bcfa718bff806bc55be640edb7](https://github.com/aquacluck/totk-lotuskit/tree/59dcfccd77b6d4bcfa718bff806bc55be640edb7)。

- [camera.hpp](https://github.com/aquacluck/totk-lotuskit/blob/59dcfccd77b6d4bcfa718bff806bc55be640edb7/src/program/util/camera.hpp)：相机布局来源线索；原文件有 `ty zeldar` 致谢，保留此贡献线索，其具体贡献范围待核验。
- [engineActor.hpp](https://github.com/aquacluck/totk-lotuskit/blob/59dcfccd77b6d4bcfa718bff806bc55be640edb7/src/program/structs/engineActor.hpp) 与 [bbBlackboard.hpp](https://github.com/aquacluck/totk-lotuskit/blob/59dcfccd77b6d4bcfa718bff806bc55be640edb7/src/program/structs/bbBlackboard.hpp)：生成 ABI 来源线索。
- 这些固定版文件的可读提交作者记录为 aquacluck，未见单独版权行或明确 only/or-later 文件头；不能仅凭 GitHub 自动检测和 GPL 附录的通用示例确定其版本选择。
- [原始 LICENSE](https://github.com/aquacluck/totk-lotuskit/blob/59dcfccd77b6d4bcfa718bff806bc55be640edb7/LICENSE)已逐字随附为 [Lotuskit-LICENSE](../licenses/Lotuskit-LICENSE)，其中含 GPL v2 及 Skyline MIT、字体和其他组件通知。保留全文不意味着这些组件全部被本项目引入，也不把它们的版权转记为 Lotuskit 或本项目作者。

文件声明、布局对应和提交记录尚不能证明全部表达的原始归属；嵌套来源、额外授权、ABI 与第三方派生表达边界继续待人工核验。

## 装备数据与 Marc Robledo MIT 通知

直接生成链：外层 `tools/build/sync_native_mod_assets.py` → `mod/telemetry/equipment_defaults.hpp` → 本补丁 `equipment_defaults.h`。生成器固定写入 GPL-2.0-only；输入也已有该标记。输入说明来自归档 zelda-totk save editor。

核对归档来源为 [marcrobledo/savegame-editors@b4db8cd11157c6d5ae54a0a5edc88dba82aebe9d](https://github.com/marcrobledo/savegame-editors/tree/b4db8cd11157c6d5ae54a0a5edc88dba82aebe9d) 的 `zelda-totk/zelda-totk.class.equipment.js`。当前去重后的 206 项默认耐久、128 项余料耐久均与该归档对应值相符；这不是精确导入提交或全部权利链的证明。

随附 [Marc-Robledo-equipment-MIT.txt](../licenses/Marc-Robledo-equipment-MIT.txt) 原样保留直接输入旁的通知：`Copyright (c) 2017-2023 Marc Robledo`，并保留原通知中的 Octicons / GitHub Inc. 声明。根 MIT 不替代它，生成结果的 GPL 标记也不撤销其条件。通知包含 Octicons 不代表装备头文件实际携带其图像。

适用的原 MIT 版权及许可通知应随实质复用部分继续保留。新增生成/适配表达、事实值、选择编排及游戏数据来源分别判断，不能把所有数值或整个数据集合笼统归项目作者或重新授予 GPL。精确导入过程和数据权利仍待人工核验。

## 生成源、链接和后续发行

另一个生成链为外层 `tools/data/generate_spawn_catalog.py` → `mod/telemetry/spawn_items.hpp` → sync 生成器 → `spawn_catalog.h`。输入没有 SPDX，输出的 GPL 标记由 sync 生成器写入；不能由此推导原始 actor 数据获得 GPL 授权。

上述外层生成器、维护输入和全部来源证据没有完整随本仓库分发。头文件可以直接查看和修改，但生成内容的首选修改形式、输入的数据许可和需要随附的材料仍待核验；本次补充通知不认证这些源码义务已经闭环。需要其他材料时应先核实权利，再决定如何提供，不擅自加入游戏数据。

构建链已核实：`telemetry.c` / `native_control.c` 通过直接包含使用这些头文件；`games/totk/Makefile` 的 runtime-v143 命令编译并链接为 `build/totk-native-v143`；上游 `build_app.py` 会将其放入 App。即使工具本身的独立部分用 MIT，也不能把这一运行时整体一概标 MIT。本次未重新构建或逐个检查历史二进制符号。

若另行发行包含这些代码的对象码，需核对 GPL v2 第 3 条的完整对应源码及适用提供方式，包括实际所含模块、接口定义、编译/安装脚本和生成输入的首选修改形式。“用户自己下载上游”或“补丁可重建”不自动证明履约。专有游戏代码、素材及其他组件的组合边界另需审查；GPL 不授予上传游戏代码的权利，不应以分发无权提供的内容来补足源码要求。

## 本次补充与待办

2026-10-26：仅新增许可正文、原始来源通知及本台账，更新 README、授权范围、使用说明和第三方声明；未改变补丁、文件头、程序功能、上游移植/转换/解密逻辑、锁定版本或历史附件。保留根 MIT 和已有版权声明，不新增商业/转载限制或 AI 许可前置条件。

- [ ] 补齐各文件逐段原作者及有效授权证据，不将提交者当作唯一版权人。
- [ ] 核实 Lotuskit 嵌套来源、camera 致谢、天气原件及 ABI 表达边界。
- [ ] 核实装备表精确导入、actor 数据来源、生成器/输入的首选修改形式与随附范围。
- [ ] 核对修改文件所需的醒目变更/日期通知是否充分；本台账不是自动认证。
- [ ] 对历史源码附件核对远端资产身份、全部通知和适用补充方式；当前补充不自动修复历史材料。
- [ ] 如发行对象码，按实际产物重新审查对应源码、链接依赖和专有内容分发权限。

以上待办未完成不应被描述为已获权利人许可或法律合规认证。许可补充后的历史清理已另获维护者明确授权，旧 Release 已移除，公开主线重建为源码初始提交；上列原始来源、版权及审查记录继续保留。清理不消除既往义务，保留来源与声明也不是对未授权内容的额外授权。
