# Pi 报告插图

当前正文包含以下已复核插图：

| 图片 | 对应内容 |
|---|---|
| [read 流程](pi-observed-turn.png) | 历史真实场景中的两次模型处理 |
| [子代理拓扑](pi-subagent-topology.png) | 可选 extension 与实验性 orchestrator |
| [当前 Coding Agent 如何驱动模型与工具循环，并保存会话？](pi-system-overview-session-only.png) | 本次使用 gpt-image-2.5-flare 生成并复核 |
| [持久历史怎样变成本次模型请求，system prompt 和 tools 在哪里加入？](pi-context-views-v3.png) | 本次使用 gpt-image-2.5-flare 生成并复核 |
| [并行工具为何有执行完成顺序和回填顺序两种顺序？](pi-tool-order-v2.png) | 本次使用 gpt-image-2.5-flare 生成并复核 |
| [新会话什么时候真正创建文件，之后如何追加？](pi-session-first-write-v3.png) | 本次使用 gpt-image-2.5-flare 生成并复核 |

新图的文字、箭头和边界依据[图示约束](reader-contracts-20261020.json)核对；提示词、hash、尺寸和实际模型见 [metadata.json](metadata.json)。旧图片和早期接口失败记录仍保留供追溯。

此前端点的 Images 调用返回 HTTP 404。本次模型列表出现图像模型后，四张修订图均已生成并回填正文，原有阻塞已解除。

总览图当前版本从已生成图片裁去范围外的独立注释，保留全部当前产品组件与箭头；原图、原始提示词和裁剪参数均保留在 metadata 中。
