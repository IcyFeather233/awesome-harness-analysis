# Claim Index

| Claim | Statement | Confidence | Evidence | Coverage |
|---|---|---|---|---|
| `C-001` | Pi 的产品入口由同一 Coding Agent runtime 支撑交互式 TUI、print/JSON 与 RPC 模式，底层能力拆分为 ai、agent、coding-agent、tui 等包。 | high | `D-001`, `S-012`, `S-013`, `S-014` | `interfaces`, `orchestration` |
| `C-002` | 通用 runAgentLoop 是 Pi 的核心模型-工具循环：模型响应后执行工具、追加 toolResult，再决定继续、注入 steering/follow-up 或退出。 | high | `S-001`, `R-001`, `R-002`, `X-001` | `core_loop`, `orchestration` |
| `C-003` | Coding Agent 的模型上下文由持久化分支消息、system prompt、项目指令、skills、工具清单及 extension hook 注入共同形成，并在模型边界前转换。 | medium | `S-002`, `S-004`, `S-005`, `R-001` | `context_assembly` |
| `C-004` | 内置、扩展与 SDK 工具被合并为运行时 registry；tool_call/tool_result hooks 位于实际 execute 前后，可阻断或改写结果。 | high | `S-003`, `S-017`, `R-002`, `X-001` | `tools_extensions` |
| `C-005` | Pi 没有默认的逐工具权限审批管线；permission popup 与路径保护属于可选 extension，默认工具直接以进程权限执行。 | high | `D-002`, `D-004`, `S-003`, `S-017` | `permissions_safety` |
| `C-006` | Project trust 只控制项目 settings/resources/extensions 的加载，不是工具权限或执行 sandbox；非交互模式无 UI 时默认 ask 会落到不信任。 | high | `D-002`, `S-005`, `S-006` | `permissions_safety`, `context_assembly` |
| `C-007` | 默认 bash backend 在当前 cwd 以继承环境启动本地 shell；timeout 是可选且无默认值，abort/timeout 会终止进程树。 | high | `D-002`, `D-007`, `S-007` | `sandbox_execution`, `workspace` |
| `C-008` | Coding Agent session 是版本化 append-only JSONL 树，id/parentId 与 leaf 表示分支；恢复时重建 compaction-aware active context。 | high | `S-008`, `S-014`, `R-003`, `R-004`, `X-003` | `sessions_persistence` |
| `C-009` | 当前 Coding Agent AgentSession 实现自动 compaction 与有限自动 retry：overflow 最多 compact-and-retry 一次，普通可重试错误指数退避且受 maxRetries 限制。 | high | `S-009`, `S-010`, `X-003` | `compaction`, `recovery` |
| `C-010` | 新 packages/agent AgentHarness 是低层 loop 之上的通用编排层，但 v0.80.7 尚未替代 Coding Agent AgentSession，且自身自动 compaction、retry、完整 hooks 与半持久恢复仍未完成。 | high | `D-003`, `D-008`, `S-011`, `X-002` | `orchestration`, `compaction`, `recovery` |
| `C-011` | 真实 SiFlow 场景观察到 read 工具形成两轮 turn：模型 toolUse、read 执行、toolResult 回填、第二次模型调用、最终退出。 | high | `R-002` | `core_loop`, `tools_extensions`, `workspace` |
| `C-012` | 持久化 session 能跨独立 Pi 进程恢复对话上下文。 | high | `S-008`, `R-003`, `R-004` | `sessions_persistence`, `recovery` |
| `C-013` | 核心 Coding Agent 不内置 MCP 或 subagent；仓库提供的 subagent 是可选 extension，通过独立 pi --mode json --no-session 子进程隔离上下文，并共享指定 cwd。 | high | `D-004`, `D-006`, `S-015` | `subagents`, `tools_extensions` |
| `C-014` | Pi 已提供稳定的 agent/message/tool/compaction/retry 事件及 JSON/RPC 输出，但 OTel 风格 trace/span 仍是设计稿，不是 v0.80.7 的默认核心实现。 | medium | `D-005`, `D-009`, `R-001`, `R-002` | `observability` |
| `C-015` | 工具批次默认并行执行；全局 sequential 或任一工具声明 executionMode=sequential 会使整批串行，同时最终 toolResult 按模型源码顺序持久化。 | high | `S-001`, `X-001` | `core_loop`, `tools_extensions` |
| `C-016` | 新 AgentHarness 通过 turn snapshot 与 save point 隔离在途 provider request：运行时配置变化只在下一个安全点刷新，pending session writes 按序落盘。 | high | `D-003`, `S-011`, `X-002` | `orchestration`, `sessions_persistence` |
| `C-017` | 扩展可以实现工具阻断，但此控制点是应用可选 hook，不是不可绕过的全局安全边界。 | high | `S-003`, `S-017`, `D-002` | `permissions_safety`, `tools_extensions` |
| `C-018` | orchestrator 是实验性的多 Pi RPC 进程 supervisor，负责 spawn、事件复用、session 元数据和退出清理；它不是默认 Coding Agent 内的 subagent 机制。 | medium | `D-010`, `S-016` | `subagents`, `orchestration` |
| `C-019` | 模型抽象以 provider-owned model catalog、auth resolution 和 stream/streamSimple 为边界；自定义 models.json 可把 OpenAI-compatible endpoint 接入同一循环。 | high | `S-012`, `R-005`, `R-001` | `model_abstraction` |
| `C-020` | 恢复策略按错误类型分层：context overflow 走 compaction，其他 retryable provider error 走指数退避，truncated tool-call 参数则拒绝执行并回送错误。 | high | `S-001`, `S-009`, `S-010`, `X-001`, `X-003` | `recovery`, `compaction`, `core_loop` |

Each claim's falsification test and conditions are stored in `../evidence/claims.jsonl`. Figure-to-evidence mappings are stored in `../diagrams/metadata.json`.
