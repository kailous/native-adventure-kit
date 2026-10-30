# 固定上游与 Mod 装配

本仓库不是上游源码镜像。`scripts/prepare_native.py` 读取 `upstream.lock.json`，下载固定 Git 提交，只导出清单中需要的文件，校验上游内容，应用 `patches/native-mod.patch`，再校验最终源码及可执行权限。

## 准备与验证

```sh
python3 scripts/prepare_native.py --work /absolute/work/native-adventure
python3 scripts/prepare_native.py --work /absolute/work/native-adventure --verify
```

输出目录必须在 kit 仓库外且尚不存在。脚本在同卷临时目录中装配，成功后才将成品工作区重命名到目标；失败会清理自己创建的临时目录，不更改已有工作区。源码位于 `--work/MacNativeGames/`，根 `.nak-workspace.json` 保存锁文件标识与素材哈希，不保存密钥或私人账号。源码内仅创建新的本地 Git 元数据供上游边界检查使用，不复制原作者历史、远程配置或凭据。

已有下载缓存时可用 `--upstream-cache /absolute/path/to/git-repository`。它只读取指定提交的 Git 对象，不 fetch、checkout、reset 或改动缓存；不会把缓存工作区中的未提交修改带入。没有缓存则自动从锁定的 HTTPS 地址 fetch。

`--verify` 只读验证现有输出，检测被修改/新增/缺失的源码、符号链接和可执行权限变化。新的 Git 元数据和已锁定 Python 源文件对应的 __pycache__ 缓存不属于源码哈希范围；不校验这些缓存的内容，不代表整个工作区可安全执行。它不更新或修复工作区；需要新版本时使用新的外部目录，不覆盖用户修改。它证明与当前锁一致，不证明功能或法律合规。

## 素材处理

原来的加载背景、页脚、游戏 Logo 与 Figma 来源素材不进入本仓库或补丁。默认由脚本生成中性纯色图片与 Native Adventure Kit 文本 Logo，原加载画面的视觉效果因此不同。

如有合法授权的自备素材，增加 `--loading-assets /absolute/authorized-assets`，目录包含非空普通文件 `background.png`、`logo.svg`、`footer.png`。脚本复制后记录哈希和用户输入来源，不自动认定素材已获授权。字体由系统回退，不携带字体文件。

## 实际游戏构建

在准备后的源码目录中查看 `build_app.py --help`。按上游要求安装环境；用户自行提供基础游戏、累计 1.4.3 更新、密钥，NSP 基础输入另需合法字体/固件来源。工作缓存与 App 都放在此源码目录之外：

```sh
python3.14 /absolute/work/native-adventure/MacNativeGames/build_app.py \
  /absolute/input/base.xci --update /absolute/input/update-1.4.3.nsp \
  -k /absolute/private/prod.keys \
  --work /absolute/cache/game-build \
  -o "/absolute/output/Native Adventure.app"
```

上游构建入口会自行准备 SPIRV-Cross、hactool 和 Python 依赖。Opus/libvpx、SDK 与工具链版本仍依本机环境；完整工具链不在本仓库，不保证 App 字节级复现。

可选 AI 辅助入口：`python3.14 AI接入/build_with_agreement.py --source /absolute/work/native-adventure/MacNativeGames -- <上面的游戏构建参数>`。它会提示确认风险；这是自选交互流程，不是 MIT 的附加许可条件。不会自动获取游戏/key或启动游戏验收。

## 失败与升级

- Git 下载失败：检查网络后重试新工作区；不要关闭 TLS 验证或换不明来源。
- 补丁/上游哈希不匹配：停止，核对锁文件与补丁；不要跳过校验、改目标哈希或让 AI 自动重写冲突。
- 目标已存在：先用 `--verify`，或选择新路径；脚本不覆盖、合并或清理旧路径。
- 新版上游：由维护者选择新固定提交、重新审查差异、更新输入/输出哈希与补丁并测试；不默认合并 main。
- 构建失败：先读取用户指定构建缓存的日志，区分装配、工具链和游戏输入错误；不删除游戏、存档或已安装 App。

当前补丁包含本地修改及已选择的上游改进，不能把所有差异归为本项目原创。补丁文本也受来源许可证约束，详见[第三方声明](third-party-notices.md)与[授权范围](../LICENSE_SCOPE.md)。

当前固定上游与候选验证范围见[2026-10-30源码更新](source-update-2026-10-30.md)。本机运行积累的派生着色器清单不进入补丁；装配使用单独锁定的兼容版上游shader_list.tsv，经锁定脚本规范化并校验目标摘要，用户构建时自行生成/补充缓存，不借此声称无卡顿。

清单行可用baseCommit指定独立固定兼容输入；当前仅shader_list.tsv锁到f3e2f661dfc05d7f6708c903ea513c297db195f1，避免新版管线键格式与本地运行时不一致。canonical-shader-list-v1通过已校验脚本规范化排序/重复项，不导入本机缓存；输出哈希仍在lock中固定。
