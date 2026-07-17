# 共享核心循环

> **证据边界。** 本报告分析 source-only commit `16a676f`。其 1,884 个 TS/TSX 文件、关键 symbol 与 feature gates 和论文所述 Claude Code v2.1.88 corpus 强指纹一致，但缺少 package version、上游 tree hash、build manifest，不能视为已证明的 exact 官方 artifact。快照仍有 657 个无法解析的相对 import；除 SiFlow 协议探针外，主循环、安全、session 与 subagent 结论均为 static-only。官方材料只支持产品立场，五价值/十三原则是 analyst synthesis。[X: X-001–X-003] [D: D-001–D-008] [C: C-001, C-024–C-026]


![Claude Code query loop](../diagrams/generated/assets/02-turn-flow.png)

*读者图问题：一次用户 query 如何跨多个 model request 与 tool call 迭代？ 这是 gpt-image-2 读者插图；当前实现边均为 static-only，结构化证据与排除项见 [图片元数据](../diagrams/generated/metadata.json)。*

[query/queryLoop](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/query.ts#L219) 初始化 messages、tool context、compaction tracking、recovery counters、stop-hook state、turnCount 和 transition，再进入 while(true)。[S: S-006]

## 一次 iteration 的九个语义阶段

| 顺序 | 阶段 | 关键事实 |
|---|---|---|
| 1 | State snapshot | 读取 mutable tool/context state、turnCount、transition 与 recovery counters |
| 2 | Boundary projection | 按 compact boundary 选择当前 message chain |
| 3 | Ordered context shaping | tool-result budget → 条件 HISTORY_SNIP → microcompact → 条件 CONTEXT_COLLAPSE → autocompact |
| 4 | Model request | 选择 provider/model，构造 system/messages/tools，启动 streaming request |
| 5 | Stream consumption | 逐块产出 assistant content，并识别实际 `tool_use` blocks |
| 6 | Tool scheduling | streaming-safe 工具可提前启动；连续 concurrency-safe calls 有界并发，其余串行 |
| 7 | Governed execution | lookup/schema → pre-hook → permission → 可选 sandbox → tool.call |
| 8 | Ordered reconciliation | 即使执行并发，tool results/context modifiers 仍按原 block 顺序合并 |
| 9 | Transition | tool_result/attachments 回填后 continue，或因 stop、budget、abort、不可恢复错误 terminal |

该表是从 [query.ts](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/query.ts#L219) 的真实源码顺序恢复，不是把论文中的视觉顺序反写成事实。[S: S-006–S-009, S-014] [C: C-004, C-007]

`query()`/`queryLoop()` 是 `AsyncGenerator`：它同时承载流式 UI 输出、model/tool events 和 terminal result；因此“流向界面的 event”与“写回下一轮模型的 message”是两个不同通道。Loop 以实际 `tool_use` blocks 决定 follow-up，而不只相信 stop_reason。[S: S-006–S-008]

并行也不是“所有工具一起跑”：连续 concurrency-safe calls 形成有上限批次，不安全工具串行；同批某些失败会取消 sibling，但结果与 context modifier 仍按原 block 顺序归并，避免执行完成顺序污染模型协议。[S: S-009, S-022]

unknown/schema/permission error 通常变为 model-facing tool_result；provider 失败由 retry 层处理；context overflow 可触发 reactive compaction；abort 会补 interruption result，避免协议悬空。这些均为 static-only。[技术证据图](../diagrams/turn-flow.svg)
