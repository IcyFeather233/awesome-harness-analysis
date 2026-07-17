# 全局术语表

本表定义的是 **Pi v0.80.7 本报告中的用法**。Pi 的 package、产品层和迁移中 API 有同名近义对象，必须结合“谁拥有生命周期”和“是否 durable”来区分。

| 术语 | 精确定义 | 容易混淆但不等价的概念 | 主要证据 |
|---|---|---|---|
| Pi / Coding Agent | 面向用户的 coding agent 产品，组合 `pi-ai`、`agent-core`、session/resource/extension/UI 层。 | 不是单指 low-level `Agent` class，也不是模型本身。 | `D-001`, `S-012`, `S-013` |
| `pi-ai` Provider | 拥有 provider id、auth、base URL/header、model catalog 和 stream 实现的模型适配边界。 | “OpenAI-compatible”不保证 request body、thinking flag 或 stream 细节完全相同。 | `S-012`, `R-005` |
| Model | provider catalog 中带 id、context window、capability 等元数据的可选模型记录。 | 不等于 Provider；多个 model 可由同一 provider 运行。 | `S-012` |
| Low-level `Agent` | 持有 context/model/tools/queues 并调用 `runAgentLoop()` 的通用运行对象。 | 不是 Coding Agent 的 `AgentSession`，不拥有完整产品 session/retry/resource lifecycle。 | `S-001` |
| `runAgentLoop()` | provider sampling、tool batch、steering、follow-up 和 stop 的 canonical low-level 双层循环。 | 不内置 planner，也不负责 Coding Agent 全部 compaction/retry/session persistence。 | `S-001`, `R-002` |
| Agent run | 一次 low-level loop 从 `agent_start` 到 `agent_end` 的执行，可含多次 turn。 | `agent_end` 不必表示产品已 settled。 | `S-001`, `S-002` |
| Turn | 一次 provider request/assistant message 及其 tool batch 的循环单位，以 `turn_start/end` 表达。 | 一个用户 prompt 可因 tool feedback、steering、retry 等包含多个 turn。 | `S-001`, `R-002` |
| `agent_settled` | Coding Agent 产品层确认没有 pending retry、compaction 或 queued continuation 后的空闲事件。 | 不等于低层 `agent_end`；后者之后产品层仍可继续编排。 | `S-002`, `R-001`, `R-002` |
| Steering | agent run 尚在进行时排入、在内层 loop 中优先形成下一 turn 的输入。 | 不等于 follow-up；follow-up 在当前 run 本可结束时由外层 loop 消费。 | `S-001` |
| Follow-up | 当前 tool/steering loop 已空后，由外层 loop 消费并启动下一 turn 的排队输入。 | 不等于新建 session，也不等于产品 retry。 | `S-001` |
| `AgentSession` | v0.80.7 Coding Agent 当前产品路径，拥有 prompt expansion、extensions、auto retry/compaction、JSONL session events 和 settled。 | 不等于迁移中的 generic `AgentHarness`。 | `S-002`, `S-009`, `S-010` |
| `AgentHarness` | 正在开发的通用 orchestration 层，直接调用相同 low-level loop，以 phase、turn snapshot、pending writes 和 save point 管理状态。 | 本版本尚未替代 Coding Agent；auto-compaction/retry/migration 不完整。 | `D-003`, `D-008`, `S-011` |
| Turn snapshot | `AgentHarness` 在一次 in-flight turn 中固定使用的配置/状态视图。 | 不是 durable session checkpoint；next-state 只在安全点应用。 | `D-003`, `S-011` |
| Save point | `AgentHarness` 可以提交 pending session writes、刷新 next-state 的确定性阶段边界。 | 不表示 workspace 或 provider stream 可恢复。 | `D-003`, `X-002` |
| `AgentSessionRuntime` | 由 main 创建的 cwd-bound 产品 runtime，组合 settings、auth、model registry、resource loader 和 `AgentSession`。 | 不等于 durable session file；switch/fork 时会重建。 | `S-013`, `S-014` |
| `SessionManager` | 管理 JSONL v3 header/entries、current leaf、branch/fork/open/migration 和 context rebuild 的持久化组件。 | 不管理 workspace snapshot。 | `S-008`, `R-004` |
| JSONL v3 session | 首行 header，后续用 `id/parentId` 形成 tree 的 append-oriented durable 文件。 | 不是平铺 chat log，也不是数据库事务或 OTel trace。 | `S-008` |
| Entry / parentId | message、model/thinking change、custom、compaction、branch summary 等 durable record及其父边。 | 文件行顺序不单独定义 active conversation；需结合 parent chain/leaf。 | `S-008` |
| Leaf / active branch | 当前选中的 tree 末端和从 header/root 到该 leaf 的 parent path。 | 切换 leaf 不会把 workspace 回滚到该 branch 当时状态。 | `S-008` |
| Resume | 重新打开 JSONL，迁移/索引 entries，选择 leaf 并用 `buildSessionContext()` 重建上下文。 | 不恢复旧进程、in-flight provider stream 或文件系统 checkpoint。 | `S-008`, `R-003`, `R-004` |
| Fork | 创建新 session header，记录 `parentSession`，复制 selected history/active path并为目标 cwd 重建 runtime。 | 不等于在原 session 内移动 leaf，也不自动复制 workspace。 | `S-008`, `S-014` |
| Context | 每次 provider request 可见的 system prompt、active transcript 和经过 extension transform 的消息。 | 不等于 JSONL 全量 entries，也不等于 workspace 内容。 | `S-001`, `S-004`, `S-005` |
| Context file | AGENTS.md/CLAUDE.md 等被 resource loader 加到 project instructions 的文件。 | AGENTS/CLAUDE 不受 project trust；`.pi/SYSTEM.md` 等项目资源受 trust。 | `S-004`, `S-006` |
| Skill | 以 metadata 暴露、在 `/skill:name` 时 lazy 展开 full body 的资源。 | 不是 extension executable，也不是内置 MCP。 | `S-004` |
| `transformContext` / `convertToLlm` | 每次 request 前先允许 context hook 变换，再把 AgentMessage 转成 provider message。 | toolResult 不能绕过这两步直接调用模型。 | `S-001`, `S-005` |
| Tool registry | 合并 built-in、extension、SDK custom tool 和 allow/deny 配置后的 name -> definition map。 | 注册不等于有 sandbox；同名 conflict/override 受加载顺序影响。 | `S-003` |
| toolUse / toolResult | assistant 提出的命名调用及 handler 执行/拒绝后回填的模型可见结果。 | `tool_execution_end` event 的完成顺序可与 toolResult transcript 顺序不同。 | `S-001`, `R-002` |
| Parallel / sequential batch | 默认批次并发；任一 tool 的 `executionMode=sequential` 会使整个 batch 串行。 | sequential 不是只让该一个 call 排队；并发结果仍按原 call index 写回。 | `S-001`, `X-001` |
| Extension | 在 host Node 进程内注册 tools、commands、hooks、UI 和 provider/session 行为的 TypeScript 能力。 | 不是隔离 plugin VM；与 Pi 进程拥有相同 OS 权限。 | `D-002`, `S-003` |
| Hook | input/context/tool/provider/session 等生命周期注入点，可观察、变换或在局部阶段 block。 | 可选 `tool_call` hook 不是不可绕过的全局 permission plane。 | `S-003`, `S-003`, `S-017` |
| Project trust | 对 project-local settings/extensions/skills/SYSTEM 等启动资源的 persisted path decision。 | 不限制运行期 read/write/edit/bash；AGENTS/CLAUDE 仍可进入 context。 | `D-002`, `S-006` |
| Protected paths | 示例 extension 通过 `tool_call` hook 拦截特定路径的可选策略。 | 不是默认核心功能，也不覆盖 extension 直接 fs/process/network。 | `S-017` |
| Sandbox | OS/container/VM 对整个或部分执行面的能力隔离。Pi 默认内置工具不自动进入 sandbox。 | 不等于 project trust 或 tool confirmation UI。 | `D-002`, `D-007` |
| Gondolin routing | 示例 extension 把选定 built-ins 和 `!` command 路由到 guest 的选择性隔离。 | 未被 delegate 的 custom extension tool 仍可在 host 执行。 | `D-007` |
| Whole-process isolation | 在 Docker/OpenShell/VM 中运行 Pi 整个进程树，覆盖 extensions、shell、language servers 等。 | bind-mounted workspace/agent dir 仍按挂载权限影响 host。 | `D-007` |
| `--no-session` | 不建立普通 durable session 的运行模式，用于一次性 print/JSON 或示例 child。 | 不表示没有 live transcript，也不提供更强权限隔离。 | `S-015`, `R-001`, `R-002` |
| Compaction | 用 summary + kept suffix 替换后续有效 context，并把 summary/firstKept/tokens 记录为一等 session entry。 | 不等于删除 JSONL 历史，也不恢复 workspace。 | `S-009`, `X-003` |
| Overflow / threshold compaction | overflow 在错误/窗口超限时可 compact-and-retry 一次；threshold 在接近窗口时压缩但不重答已完成 turn。 | 两者触发和重答语义不同，不能合写成统一 retry。 | `S-009`, `X-003` |
| Faux provider | 测试中按脚本返回 message/tool/error 的可控 provider，用于区分 controller 分支。 | 不是真实模型质量评估。 | `X-001`–`X-003` |
| JSON mode / RPC mode | JSON 把 header/events 输出到 stdout；RPC 以 LF-delimited commands/responses 加并行 events/UI request 交互。 | 两者是 adapter，不是独立 agent loop。 | `D-005`, `S-013` |
| Agent events | run/turn/message/tool/queue/compaction/retry/settled 的结构化生命周期事件。 | 默认没有统一 traceId/spanId，也未自动 redaction。 | `D-005`, `R-001`, `R-002` |
| OTel/Sentry adapter notes | 仓库对 stable vendor-neutral events 映射到外部观测系统的设计文档。 | 不是 v0.80.7 默认 exporter 实现。 | `D-009` |
| Subagent extension | 示例 `subagent` tool，以独立 `pi --mode json --no-session` 子进程运行任务并回收结果。 | 不是默认核心 delegation primitive；默认共享 cwd/env。 | `D-006`, `S-015` |
| Orchestrator | experimental supervisor，为每个 instance 管理独立 RPC Pi process、events/UI 和 metadata。 | 它是多 session process supervisor，不是 `runAgentLoop` 内的 parent/child tool protocol。 | `D-010`, `S-016` |
| HIR | Harness Intermediate Representation：把入口、loop、context、tool、安全、session 等恢复为 typed nodes/edges。 | 是证据约束的分析模型，不是源码 AST 或 runtime trace。 | [`hir.json`](../hir.json) |
