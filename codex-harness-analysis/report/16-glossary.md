# 全局术语表

本表定义的是 **Codex 0.144.5 本报告中的用法**。同一名词在产品 UI、Responses API 或其他 agent framework 中可能有不同边界；章节首次出现时应按这里的定义理解。

| 术语 | 精确定义 | 容易混淆但不等价的概念 | 主要证据 |
|---|---|---|---|
| Thread | 由 `thread_id` 标识、可跨 turn 和进程恢复或 fork 的逻辑会话身份；durable history 通过 `LiveThread`/rollout 保存。 | 不是当前 Rust 进程中的 session，也不拥有 workspace 快照。 | `D-004`, `S-018`, `X-006` |
| Session | 当前进程中处理某个 thread 的 live runtime，持有 event channel、provider、policy、services、context 和最多一个 active turn。 | 进程退出后不会原样持久化；resume 同一 thread 会创建新的 session。 | `S-002`, `S-022` |
| Turn | 一次任务的调度边界，从 `TurnStarted` 到 `TurnComplete` 或 `TurnAborted`；内部可以包含多次模型请求和工具调用。 | 不等于单次 Responses API request，也不等于整条 thread。 | `S-002`, `S-003`, `X-002` |
| Model request / sampling | turn 内一次把 prompt、history 和 tool specs 发送给 provider 并消费 stream 的操作。 | 一次 turn 可反复 sampling；tool feedback 后通常会产生下一 request。 | `S-003`, `X-002` |
| `StepContext` | 某次 sampling/tool invocation 固定使用的 model、cwd、approval、sandbox、tools 等请求级快照。 | 不是整个 session 的可变状态，也不是仅包含 message 的 context。 | `S-004`, `S-010` |
| Context | 后续模型请求可见的信息组合：base instructions、history、world-state 更新、当前输入及 tool specs。 | 不等于 rollout 全量，也不等于 workspace 文件内容。 | `S-004`–`S-006` |
| History | `ContextManager` 按 oldest-first 管理的模型可见 API items，包括 message、function call 与 tool output。 | 不包含每个内部 event；compaction 后的有效 history 也不等于原始 rollout 文本。 | `S-005`, `X-002` |
| World state | AGENTS、环境、subagent/apps/plugins 等带类型的运行环境状态，以 snapshot/RFC 7386 风格 diff 增量注入。 | 不是 git diff，也不是任意自然语言 memory。 | `D-007`, `S-006` |
| Compaction | token/window 条件触发的 history replacement；可在 turn 前或 tool follow-up 中发生，并区分 remote/local 实现。 | 不是简单删除最旧字符串，也不回滚 workspace 或 durable rollout。 | `S-007` |
| Long-term memories | 默认关闭的实验性两阶段 pipeline：从 rollout 提取记忆，再由专用 agent consolidation 到 durable 文件。 | 不等于每轮都执行的 compaction。 | `D-005`, `S-020` |
| Registry | 当前进程已经注册、router 能定位 handler implementation 的工具集合。 | 工具在 registry 中不表示本次模型请求可见。 | `S-009`, `S-011` |
| Exposure | 某次 turn/request 实际发送给模型的 tool schema 子集，由 provider capability、feature、depth 和 hidden/deferred 规则决定。 | 不等于 registry，也不等于工具一定会被模型调用。 | `S-009`, `X-005` |
| Tool spec | 发送给 provider 的工具名称、参数 schema 和调用形式描述。 | 它不是 handler 实现，也不授予副作用权限。 | `S-004`, `S-009` |
| Router / Registry / Handler | Router 解析 function/custom/namespace call 并绑定 context；registry 查找实现并运行 hooks；handler 执行具体能力。 | 三者是连续阶段，不是同一个“tool layer”。 | `S-010`, `S-011` |
| Dynamic / hosted tool | host 在运行时提供 schema 或回传结果的工具能力；dynamic handler 可等待 host response。 | 不应默认认为它与进程 exec 共享 approval/sandbox 路径。 | `S-026` |
| MCP | Model Context Protocol；Codex 可从 MCP server 合并工具，并通过专门 handler 调用。 | MCP 是能力来源/协议，不等于 Codex 内置 sandbox。 | `S-009`, `S-026` |
| Namespace tool | provider tool schema 中按 namespace 组织的一类调用形式；本版本 V1 multi-agent 使用它。 | 不等于普通 function tool；SiFlow 本轮接受后者但拒绝该 schema。 | `R-003`, `X-005` |
| Exec policy | 对真正启动进程的命令 segment 计算 `forbid/prompt/allow` requirement 的规则层。 | 不是 platform sandbox；也不能泛化为所有 handler 的副作用治理。 | `S-012` |
| Approval policy/cache | 决定何时可询问用户及是否在同一 session 复用批准；cache key 可由命令或目标路径构成。 | 批准不等于关闭 sandbox，也不是跨 session 的永久授权。 | `S-013`, `S-028` |
| Sandbox / permission profile | 把 filesystem/network 权限转换成 Linux、macOS 或 Windows 的实际执行约束。 | 不是布尔开关，也不是 approval 的同义词。 | `D-002`, `S-014` |
| `apply_patch` 专用路径 | shell/unified-exec 在普通 exec requirement 前识别补丁，交给 patch safety、按路径 approval 和可 sandbox 的 `ApplyPatchRuntime`。 | 它不是先启动 shell 再执行任意命令；也不证明补丁无需审批。 | `S-028` |
| Parallel / exclusive tool | `ToolCallRuntime` 对允许并行的 handler 使用读锁，对需独占的 handler 使用写锁。 | “模型一次返回多个调用”不表示所有调用必然并行。 | `S-025` |
| `AgentControl` | root agent tree 共享的 child registry、并发/深度限制、消息、interrupt 与 lifecycle 控制面。 | 不等于 child context；child 仍有独立 session/history。 | `S-015`–`S-017` |
| V1 / V2 multi-agent | 两个分离 feature gate；本版本默认 V1 开、V2 关。V2 额外有 session-scoped mailbox/preemption 语义。 | V1 动态结果不能直接证明 V2 行为。 | `S-015`, `S-027`, `X-005` |
| Mailbox | V2 session 内暂存 child completion 和 inter-agent message、供 parent 当前或下一 follow-up 消费的队列。 | 不等于操作系统 mailbox，也不是自动终止 parent session。 | `S-027` |
| `ThreadStore` / `LiveThread` | storage-neutral durable thread API 与活动持久化 handle，负责 create/resume/append/flush 等操作。 | 不负责把 workspace 还原到历史版本。 | `D-004`, `S-018` |
| Rollout | 按顺序追加 session items 的 durable JSONL 历史，供 resume/replay。 | 不等于 OTel trace，也不保证每次文件副作用可逆。 | `S-019`, `X-006` |
| Product events | TUI、`exec --json`、app-server 可消费的 thread/turn/item/tool 状态事件。 | 不等于完整内部 causal trace。 | `D-003`, `S-023` |
| OTel | OpenTelemetry logs/traces/metrics 输出层，用 conversation/turn/tool/call 等字段做关联。 | 不等于 rollout；本轮 exporter 关闭，只有静态证据。 | `D-006`, `S-021` |
| Provider dialect | endpoint 对 message role、tool schema、stream event 等具体 wire format 的兼容集合。 | endpoint 支持基础 Responses SSE 不表示兼容 stock Codex 完整请求。 | `S-024`, `R-002`, `R-003` |
| HIR | Harness Intermediate Representation：把入口、loop、context、tool、安全、持久化等恢复成带类型 nodes/edges 的机器可读图。 | HIR 是证据约束下的分析模型，不是源码 AST 或运行时 trace。 | [`hir.json`](../hir.json) |
