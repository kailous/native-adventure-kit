# 地图客户端源码

地图工具已加入 [map-client/](../map-client/README.md)，包含 Swift 客户端、Python 服务和网页 UI。构建入口为 `scripts/build_map_client.py`，详见源码目录说明。

不携带 DataPacks、原游戏图片或 Figma 素材；默认使用空的内容/匹配表与中性占位资源。已有合法数据包可经客户端导入，完整匹配和原视觉需单独提供有权使用的资源。原材料清单见 [素材清单](inventory/game-assets.md)。

旧 Release 及其地图成品已按维护者授权移除，未重新打包；本项目当前提供地图源码。处理记录见[历史复核](historical-release-review.md)，MCP 使用见 [接入教程](../AI接入/MCP_USER_GUIDE.md)。
