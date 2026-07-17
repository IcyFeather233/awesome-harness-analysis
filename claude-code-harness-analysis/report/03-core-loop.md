# 共享核心循环

> **证据边界。** 本报告分析 source-only commit `16a676f`。其 1,884 个 TS/TSX 文件、关键 symbol 与 feature gates 和论文所述 Claude Code v2.1.88 corpus 强指纹一致，但缺少 package version、上游 tree hash、build manifest，不能视为已证明的 exact 官方 artifact。快照仍有 657 个无法解析的相对 import；除 SiFlow 协议探针外，主循环、安全、session 与 subagent 结论均为 static-only。官方材料只支持产品立场，五价值/十三原则是 analyst synthesis。[X: X-001–X-003] [D: D-001–D-008] [C: C-001, C-024–C-026] 首次遇到缩写或内部名词时，可查 [全局术语表](16-glossary.md)。


![Claude Code query loop](../diagrams/generated/assets/02-turn-flow.png)

*读者图问题：一次用户 query 如何跨多个 model request 与 tool call 迭代？ 这是 gpt-image-2 读者插图；当前实现边均为 static-only，结构化证据与排除项见 [图片元数据](../diagrams/generated/metadata.json)。*

[query/queryLoop](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/query.ts#L219) 初始化 messages、tool context、compaction tracking、recovery counters、stop-hook state、turnCount 和 transition，再进入 while(true)。[S: S-006]

## 一次 iteration 的九个语义阶段

| 顺序 | 阶段 | 本轮实际做什么 | 读者注意 |
|---|---|---|---|
| 1 | State snapshot | 从 live messages、tool/context state、turnCount、transition 和 recovery counters 读取本轮决策视图。 | 这不是磁盘 checkpoint；后续 tool result 或 attachment 仍会修改 live state。 |
| 2 | Boundary projection | 根据 compact boundary 和当前 parent chain 选择要送入 request 的有效 message chain。 | Durable JSONL 中的旧消息可能被 summary 代表，不能简单理解为“读取全部历史”。 |
| 3 | Ordered context shaping | 按源码顺序应用 tool-result budget、可选 `HISTORY_SNIP`、microcompact、可选 `CONTEXT_COLLAPSE`、autocompact。 | 这些 stage 粒度和启用条件不同；stage 顺序来自 source audit，不来自图示排版。 |
| 4 | Model request | 选择 provider/model，组装 system、messages、visible tool schemas、thinking/cache/beta headers，并启动 streaming request。 | 一次 iteration 通常对应一次模型请求，但 retry/fallback 可能增加网络尝试。 |
| 5 | Stream consumption | 逐块处理 provider 返回的 assistant content，并识别真正出现的 `tool_use` blocks。 | Stop reason 只是线索；follow-up 由实际 blocks 与 loop transition 共同决定。 |
| 6 | Tool scheduling | streaming-safe 工具可在完整 assistant 输出结束前启动；连续 concurrency-safe calls 可形成有上限批次，其余串行。 | “支持并发”不表示所有工具一起跑，也不表示完成顺序就是协议顺序。 |
| 7 | Governed execution | Router 做 lookup 和 schema/input validation，再进入 pre-hook、permission、可选 sandbox 和具体 `tool.call`。 | 这是 canonical tool path；startup、hook lifecycle、MCP server lifecycle 等仍需独立审计。 |
| 8 | Ordered reconciliation | 把 tool results、errors 和 context modifiers 按原 `tool_use` block 顺序合并回 message chain。 | 即使执行并发，模型看到的协议顺序仍应稳定，避免快完成的 tool 抢先污染上下文。 |
| 9 | Transition | 回填 `tool_result`/attachments 后 continue；或因 stop、turn/budget、hook stop、abort、不可恢复错误进入 terminal。 | Terminal 只结束当前用户 query，不表示进程退出、session 删除或 workspace 回滚。 |

该表是从 [query.ts](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/query.ts#L219) 的真实源码顺序恢复，不是把论文中的视觉顺序反写成事实。[S: S-006–S-009, S-014] [C: C-004, C-007]

## 九个阶段中的几个容易误解的词

**State snapshot** 不是把整个 session 写成磁盘快照，而是在本轮开始时读取当前 live messages、tool context、turn count 和 recovery counters，形成这一轮决策所使用的状态视图。随后这些 live objects 仍可能被 tool result 或 attachment 更新。

**Boundary projection** 是从 durable/live history 中选择“当前 request 仍然有效的 message chain”。compaction boundary 之前的原始消息可能被 summary 代表，因此 projection 不等于简单取 JSONL 的全部行。

**Stream consumption** 表示 Anthropic Messages response 是逐块到达的。`AsyncGenerator` 让 query loop 可以一边收到 provider event，一边向 REPL/SDK yield 进度；但 UI event 不会自动成为下一次模型 message，只有经过 message/result 组装的内容才会回填。

**Streaming-safe tool** 可以在模型尚未完全结束输出时提前启动；**concurrency-safe tool** 可以与相邻的同类 tool call 并发执行。这两个属性不同。并发完成顺序也不等于模型 block 顺序，因此 **ordered reconciliation** 会按原 `tool_use` 顺序合并 results/context modifiers。

**Transition** 是 loop 对下一步的显式决定：continue、stop、recover 或 abort。`terminal` 只表示当前 query 结束，不表示进程退出或 session 被删除。

`query()`/`queryLoop()` 是 `AsyncGenerator`：它同时承载流式 UI 输出、model/tool events 和 terminal result；因此“流向界面的 event”与“写回下一轮模型的 message”是两个不同通道。Loop 以实际 `tool_use` blocks 决定 follow-up，而不只相信 stop_reason。[S: S-006–S-008]

并行也不是“所有工具一起跑”：连续 concurrency-safe calls 形成有上限批次，不安全工具串行；同批某些失败会取消 sibling，但结果与 context modifier 仍按原 block 顺序归并，避免执行完成顺序污染模型协议。[S: S-009, S-022]

unknown/schema/permission error 通常变为 model-facing tool_result；provider 失败由 retry 层处理；context overflow 可触发 reactive compaction；abort 会补 interruption result，避免协议悬空。这些均为 static-only。[技术证据图](../diagrams/turn-flow.svg)
