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

`stopReason=length` 是特殊失败路径：即使 salvage 后参数能解析，Pi 也不会执行可能被截断的 tool call，而是为每个 call 生成 error result。[C: C-020]

## Tool batch 语义

默认 parallel。preflight/validation 顺序进行，允许的工具并发执行，`tool_execution_end` 按完成顺序出现，最终 toolResult message 按原始 tool call 顺序写入；任一工具为 sequential 则整批串行。[C: C-015] [X: X-001]

## 产品级编排

Coding Agent `AgentSession` 在 loop 外处理 prompt expansion、extension input、auth、auto retry、auto compaction、session event 和 settled。`_runAgentPrompt()` 在一次 `agent.prompt()` 后继续处理 retry/compaction/queued continuation，直到真正 settled。[S: S-002, S-009, S-010]

新 `AgentHarness` 也直接调用 `runAgentLoop()`，但用显式 phase、turn snapshot、pending session writes 和 save point 取代部分 `AgentSession` 机制。两者不是叠加调用关系，而是共享 low-level loop 的当前产品实现与迁移目标。[D: D-003, D-008] [S: S-011]
