# 03 核心循环与编排

![Observed runtime turn](../diagrams/generated/pi-observed-turn.png)

> 图 2（gpt-image-2 读者插图）：严格复现 `R-SCENARIO-002` 的两次模型迭代、`314159` tool result 回填，以及 `agent_end` 与 `agent_settled` 的分离；没有混入未发生的写入、审批、压缩或恢复路径。图像的 prompt、output hash 与语义审查见[生成图 metadata](../diagrams/generated/metadata.json)；事件顺序来自 `R-SCENARIO-002`、[Harness IR](../hir.json)和下列 Evidence IDs。Evidence: `S-001`, `S-002`, `S-008`, `S-009`, `S-010`, `R-002`, `R-003`, `R-004`, `X-003`。

## 贯穿案例中的循环

第一次 provider response 产生 `read` toolUse；工具结果 `314159` 进入 context 后触发第二次 provider request；第二个 response 没有 toolUse，low-level loop 发出 `agent_end`，随后产品层发出 `agent_settled`。这把“模型停止”和“产品真正 settled”区分为两个生命周期概念。[R: R-002]

## Low-level loop

`runAgentLoop()` 维护外层 follow-up loop 和内层 tool/steering loop。每次 assistant message：

1. `transformContext`，再 `convertToLlm`；
2. 调 provider stream，转发 text/thinking/toolcall delta；
3. error/aborted 立即 `turn_end -> agent_end`；
4. toolUse 执行工具并把 toolResult 追加到 context；
5. `prepareNextTurn` 可刷新 context/model/thinking；
6. 注入 steering；没有工具和 steering 后检查 follow-up；
7. 全部为空则 `agent_end`。[S: S-001]

| 顺序 | 阶段 | 输入/状态 | 产出或分支 | 所属边界 |
|---:|---|---|---|---|
| 1 | context transform | 当前 transcript、system prompt、model | extension `transformContext` 后转成 provider messages | 每次 model request |
| 2 | provider stream | model、converted context、tool schemas | text/thinking/toolUse deltas 或 error/abort | low-level turn |
| 3 | tool preflight | 完整 assistant toolUse list | 参数 validation、hook block、sequential 判定 | 同一 tool batch |
| 4 | tool execution | 允许执行的 calls | completion-order events；结果暂存在原 call index | tool runtime |
| 5 | transcript append | assistant message + ordered toolResults | 下一次 model request 可见的新 context | 同一 agent run |
| 6 | steering | loop 运行中排入的高优先输入 | 立即形成下一 turn | 内层 tool/steering loop |
| 7 | follow-up | 当前 run 即将结束时排入的后续输入 | 外层 loop 再启动 turn | 外层 follow-up loop |
| 8 | settle handoff | low-level `agent_end` | `AgentSession` 可继续 retry/compact/queue，最终发 `agent_settled` | 产品编排层 |

`stopReason=length` 是特殊失败路径：即使 salvage 后参数能解析，Pi 也不会执行可能被截断的 tool call，而是为每个 call 生成 error result。[C: C-020]

## Tool batch 语义

默认 parallel。preflight/validation 顺序进行，允许的工具并发执行，`tool_execution_end` 按完成顺序出现，最终 toolResult message 按原始 tool call 顺序写入；任一工具为 sequential 则整批串行。[C: C-015] [X: X-001]

| 批次条件 | 实际启动语义 | Event 顺序 | 写入 transcript 的顺序 | 为什么重要 |
|---|---|---|---|---|
| 所有 call 允许 parallel | validation 后并发执行 | `tool_execution_end` 可按实际完成先后交错 | `Promise.all` 返回值按原 call index 对齐，再按模型 call 顺序追加 | UI 可以先展示快工具完成，但模型下轮看到稳定顺序 |
| 任一 call 标记 sequential | 整批按模型 call 顺序串行 | start/end 与 call 顺序一致 | 同一 call 顺序 | sequential 是 batch-level 降级，不只是该工具单独排队 |
| call validation/hook block | 被拒 call 不进入 execute | 产生对应失败结束/结果事件 | 仍占原 call 的结果位置 | 后续 toolResult 必须与原 toolUse 一一对应 |
| `stopReason=length` | 批次中的截断 call 全部拒绝执行 | 产生 error results，不产生真实副作用 execution | error toolResults 按 call 顺序进入 context | 能解析出 JSON 不代表参数完整或可安全执行 |

## 产品级编排

Coding Agent `AgentSession` 在 loop 外处理 prompt expansion、extension input、auth、auto retry、auto compaction、session event 和 settled。`_runAgentPrompt()` 在一次 `agent.prompt()` 后继续处理 retry/compaction/queued continuation，直到真正 settled。[S: S-002, S-009, S-010]

新 `AgentHarness` 也直接调用 `runAgentLoop()`，但用显式 phase、turn snapshot、pending session writes 和 save point 取代部分 `AgentSession` 机制。两者不是叠加调用关系，而是共享 low-level loop 的当前产品实现与迁移目标。[D: D-003, D-008] [S: S-011]
