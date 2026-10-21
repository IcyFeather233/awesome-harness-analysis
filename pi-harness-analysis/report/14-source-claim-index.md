# 源码与结论索引

结论沿用历史编号，仅列当前 AgentSession 路径采用的记录。完整条件和反例检查保存在 [claims.jsonl](../evidence/claims.jsonl)。

## C-001

Pi 的产品入口由同一 Coding Agent runtime 支撑交互式 TUI、print/JSON 与 RPC 模式，底层能力拆分为 ai、agent、coding-agent、tui 等包。

- [D-001](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/README.md#L13)：根 README 将 Pi 定义为 agent harness，并列出 coding-agent、agent-core、ai、tui 的职责。
- [S-012](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/ai/src/models.ts#L24)：pi-ai Models 将 provider catalog、auth resolution 与 stream dispatch 统一在运行时 collection。
- [S-013](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/main.ts#L650)：main 根据 appMode 分派 RPC、interactive 或 print/JSON，并共享 createAgentSessionRuntime。
- [S-014](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session-runtime.ts#L67)：AgentSessionRuntime 在 session switch/fork/import 时 teardown 并重建 cwd-bound services。
- [S-033](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/modes/interactive/interactive-mode.ts#L2765)：运行中的普通文本按 Enter 提交时显式传 streamingBehavior=steer；Alt+Enter 对应 followUp。AgentSession 按参数分流，不由 LLM 按语义分类。

范围：v0.80.7 monorepo and CLI。状态：supported；置信度：high。

## C-002

通用 runAgentLoop 是 Pi 的核心模型-工具循环：模型响应后执行工具、追加 toolResult，再决定继续、注入 steering/follow-up 或退出。

- [S-001](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/src/agent-loop.ts#L95)：runAgentLoop 实现双层循环、模型流、toolUse、steering/follow-up、并行/串行工具、length-stop 拒绝执行与 hooks。
- [R-001](../traces/normalized/R-001-text-only.normalized.jsonl)：真实 SiFlow 文本场景观察到 session -> agent/turn -> assistant stream -> turn_end -> agent_end -> settled，最终 PI_TEXT_OK。
- [R-002](../traces/normalized/R-002-read-tool.normalized.jsonl)：真实 read 场景观察到两次 turn、read start/end、toolResult 回填与最终值 314159。
- [X-001](../runtime-tests.md)：agent-core 定向 Vitest：agent-loop.test.ts 与 agent.test.ts 共 39/39 通过。
- [X-004](../traces/checks/20261020/X-004.vitest.json)：2026-10-20 agent 定向测试：39 passed，0 failed，0 skipped；exit=0。
- [S-033](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/modes/interactive/interactive-mode.ts#L2765)：运行中的普通文本按 Enter 提交时显式传 streamingBehavior=steer；Alt+Enter 对应 followUp。AgentSession 按参数分流，不由 LLM 按语义分类。
- [S-034](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/tools/bash.ts#L395)：内置 bash 将非零退出码或执行超时转为异常；工具执行器捕获后生成错误 toolResult，供后续模型决策，不直接进入 AgentSession 的 assistant error 重试分类。
- [I-002](../evidence/observations.jsonl)：Haochuan 从交互角度区分 steering 与 follow-up；本报告将其理解为两个消费时机，而非两个立即中断工具的接口。

范围：agent-core low-level loop。状态：supported；置信度：high。

## C-003

Coding Agent 的模型上下文由持久化分支消息、system prompt、项目指令、skills、工具清单及 extension hook 注入共同形成，并在模型边界前转换。

- [S-002](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L1023)：AgentSession prompt pipeline 处理 extension command/input、skill/template、queue、auth、pre-prompt compaction 与 before_agent_start。
- [S-004](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/system-prompt.ts#L27)：buildSystemPrompt 注入工具说明、project context、skills 与 cwd。
- [S-005](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/resource-loader.ts#L330)：DefaultResourceLoader 先以不信任状态加载 bootstrap extensions，再解析 trust 并加载最终资源集合。
- [R-001](../traces/normalized/R-001-text-only.normalized.jsonl)：真实 SiFlow 文本场景观察到 session -> agent/turn -> assistant stream -> turn_end -> agent_end -> settled，最终 PI_TEXT_OK。
- [S-022](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/messages.ts#L146)：convertToLlm 将 custom/bashExecution/summary 转为 user messages，excludeFromContext 的 bashExecution 被过滤，普通 user/assistant/toolResult 原样保留。
- [D-011](../evidence/observations.jsonl)：Mario 的设计回顾强调对模型上下文和交互过程的控制，并说明分离工具返回内容与界面数据。

范围：coding-agent default runtime。状态：supported；置信度：medium。

## C-004

内置、扩展与 SDK 工具被合并为运行时 registry；tool_call/tool_result hooks 位于实际 execute 前后，可阻断或改写结果。

- [S-003](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L415)：AgentSession 把 extension tool_call/tool_result 安装为 agent before/afterToolCall，并动态刷新统一 tool registry。
- [S-017](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/examples/extensions/protected-paths.ts#L1)：protected-paths example 通过可选 tool_call hook 阻断 write/edit，表明权限策略属于 extension。
- [R-002](../traces/normalized/R-002-read-tool.normalized.jsonl)：真实 read 场景观察到两次 turn、read start/end、toolResult 回填与最终值 314159。
- [X-001](../runtime-tests.md)：agent-core 定向 Vitest：agent-loop.test.ts 与 agent.test.ts 共 39/39 通过。
- [X-005](../traces/checks/20261020/X-005.vitest.json)：2026-10-20 coding-agent 定向测试：12 passed，0 failed，5 skipped；exit=0。5 项真实模型 e2e 因未提供凭据跳过；通过项包含 settlement、动态工具、网络错误重试与压缩后队列。
- [S-023](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L467)：AgentSession 在 prepareNextTurn 阶段用当前 system prompt、tools、model 和 thinking level 刷新下一次模型请求。
- [S-027](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L2490)：AgentSession.reload 先发 shutdown，再刷新设置、provider registry 与资源，重建 runner/tool registry，最后在绑定存在时发 session_start。
- [S-030](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/tools/index.ts#L83)：内置 ToolName/allToolNames 定义七个工具名称；SDK 默认 active set 取 read/bash/edit/write。
- [I-001](../evidence/observations.jsonl)：Armin 的使用经验把扩展状态、热重载和会话分支联系为可持续修改工具的工作流。

范围：coding-agent tool system。状态：supported；置信度：high。

## C-005

Pi 没有默认的逐工具权限审批管线；permission popup 与路径保护属于可选 extension，默认工具直接以进程权限执行。

- [D-002](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/docs/security.md#L3)：安全文档明确 project trust 不是 sandbox，默认工具和 extensions 以 Pi 进程权限运行。
- [D-004](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/README.md#L489)：Coding Agent 产品哲学明确无内置 MCP、subagents、permission popups、plan mode 与 background bash。
- [S-003](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L415)：AgentSession 把 extension tool_call/tool_result 安装为 agent before/afterToolCall，并动态刷新统一 tool registry。
- [S-017](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/examples/extensions/protected-paths.ts#L1)：protected-paths example 通过可选 tool_call hook 阻断 write/edit，表明权限策略属于 extension。

范围：default coding-agent configuration。状态：supported；置信度：high。

## C-006

Project trust 只控制项目 settings/resources/extensions 的加载，不是工具权限或执行 sandbox；非交互模式无 UI 时默认 ask 会落到不信任。

- [D-002](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/docs/security.md#L3)：安全文档明确 project trust 不是 sandbox，默认工具和 extensions 以 Pi 进程权限运行。
- [S-005](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/resource-loader.ts#L330)：DefaultResourceLoader 先以不信任状态加载 bootstrap extensions，再解析 trust 并加载最终资源集合。
- [S-006](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/project-trust.ts#L46)：resolveProjectTrusted 优先 override/extension/store，default ask 且无 UI 时返回 false。

范围：project resource bootstrap。状态：supported；置信度：high。

## C-007

默认 bash backend 在当前 cwd 以继承环境启动本地 shell；timeout 是可选且无默认值，abort/timeout 会终止进程树。

- [D-002](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/docs/security.md#L3)：安全文档明确 project trust 不是 sandbox，默认工具和 extensions 以 Pi 进程权限运行。
- [D-007](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/docs/containerization.md#L3)：容器文档把隔离分成 whole-process 与 tool-routing；host extensions 可能仍绕过 VM。
- [S-007](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/tools/bash.ts#L27)：内置 bash 使用 cwd、继承环境和 detached process group；timeout 无默认值，abort/timeout kill process tree。

范围：built-in bash tool。状态：supported；置信度：high。

## C-008

Coding Agent session 是版本化 append-only JSONL 树，id/parentId 与 leaf 表示分支；恢复时重建 compaction-aware active context。

- [S-008](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/session-manager.ts#L322)：SessionManager 实现 v3 append-only JSONL tree、active leaf、分支选取、entry 到应用消息的转换、compaction-aware context、restore 与 fork。
- [S-014](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session-runtime.ts#L67)：AgentSessionRuntime 在 session switch/fork/import 时 teardown 并重建 cwd-bound services。
- [R-003](../traces/normalized/R-003-session-create.normalized.jsonl)：第一个独立 Pi 进程创建持久化 session 并写入合成 token，最终 ACK。
- [R-004](../traces/normalized/R-004-session-resume.normalized.jsonl)：第二个独立 Pi 进程恢复同一 session-id，并在未重给 token 的情况下返回 PI_RESUME_2718。
- [X-003](../runtime-tests.md)：Coding Agent 定向 Vitest：compaction、network retry、session context 共 31/31 通过。
- [X-006](../traces/checks/20261020/X-006.vitest.json)：2026-10-20 coding-agent 定向测试：46 passed，1 failed，0 skipped；exit=1。失败发生于 CLI 子进程模块解析；46 项进程内 context/tree 测试通过，后续 X-010 加载器对照单独记录。
- [X-010](../traces/checks/20261020-cli/X-010.vitest.json)：2026-10-20 coding-agent 定向测试：1 passed，0 failed，0 skipped；exit=0。
- [X-009](../traces/checks/20261020-followup/X-009.vitest.json)：2026-10-20 coding-agent 定向测试：5 passed，0 failed，16 skipped；exit=0。仅选择 setSessionFile 组，16 项未选用；5 项空文件/非法文件处理检查通过。
- [S-020](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/session-manager.ts#L788)：新会话先在内存追加 entry；首次 assistant entry 触发整批写入，之后逐条追加；已有空文件和格式迁移有明确重写路径。
- [I-001](../evidence/observations.jsonl)：Armin 的使用经验把扩展状态、热重载和会话分支联系为可持续修改工具的工作流。

范围：coding-agent sessions v3。状态：supported；置信度：high。

## C-009

AgentSession 分别处理有界普通重试与自动压缩：错误 overflow 最多 compact-and-retry 一次；已完成 stop 响应的 usage 越界不重答；threshold 压缩后仍可消费排队输入。

- [S-009](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L1890)：AgentSession 把 overflow 与 threshold 分开处理，overflow 最多一次 compact-and-retry，并持久化 compaction entry 后重建 context。
- [S-010](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L2573)：普通 retryable assistant error 使用受 maxRetries 限制的指数退避，error 留在 session 但从 live context 移除。
- [X-003](../runtime-tests.md)：Coding Agent 定向 Vitest：compaction、network retry、session context 共 31/31 通过。
- [X-005](../traces/checks/20261020/X-005.vitest.json)：2026-10-20 coding-agent 定向测试：12 passed，0 failed，5 skipped；exit=0。5 项真实模型 e2e 因未提供凭据跳过；通过项包含 settlement、动态工具、网络错误重试与压缩后队列。
- [X-008](../traces/checks/20261020-followup/X-008.vitest.json)：2026-10-20 coding-agent 定向测试：15 passed，0 failed，0 skipped；exit=0。
- [S-021](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L1890)：已完成 stop 响应即使 usage 越界也只压缩、不重答；错误 overflow 有一次恢复限制；threshold 后存在 queued messages 时仍继续处理队列。
- [S-031](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/ai/src/utils/retry.ts#L1)：isRetryableAssistantError 要求 stopReason=error 且有 errorMessage；先排除配额/账单限制，再匹配临时服务或传输错误文本，不调用模型判断。
- [S-032](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/settings-manager.ts#L795)：产品层自动重试默认开启，maxRetries 默认 3，baseDelayMs 默认 2000；实际退避由 AgentSession._prepareRetry 计算。

范围：coding-agent AgentSession。状态：supported；置信度：high。

## C-011

真实 SiFlow 场景观察到 read 工具形成两轮 turn：模型 toolUse、read 执行、toolResult 回填、第二次模型调用、最终退出。

- [R-002](../traces/normalized/R-002-read-tool.normalized.jsonl)：真实 read 场景观察到两次 turn、read start/end、toolResult 回填与最终值 314159。

范围：R-SCENARIO-002。状态：supported；置信度：high。

## C-012

持久化 session 能跨独立 Pi 进程恢复对话上下文。

- [S-008](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/session-manager.ts#L322)：SessionManager 实现 v3 append-only JSONL tree、active leaf、分支选取、entry 到应用消息的转换、compaction-aware context、restore 与 fork。
- [R-003](../traces/normalized/R-003-session-create.normalized.jsonl)：第一个独立 Pi 进程创建持久化 session 并写入合成 token，最终 ACK。
- [R-004](../traces/normalized/R-004-session-resume.normalized.jsonl)：第二个独立 Pi 进程恢复同一 session-id，并在未重给 token 的情况下返回 PI_RESUME_2718。

范围：R-SCENARIO-003 and R-SCENARIO-004。状态：supported；置信度：high。

## C-013

核心 Coding Agent 不内置 MCP 或 subagent；仓库提供的 subagent 是可选 extension，通过独立 pi --mode json --no-session 子进程隔离上下文，并共享指定 cwd。

- [D-004](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/README.md#L489)：Coding Agent 产品哲学明确无内置 MCP、subagents、permission popups、plan mode 与 background bash。
- [D-006](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/examples/extensions/subagent/README.md#L1)：可选 subagent example 文档说明独立 Pi 进程、隔离 context、并行/chain、abort 与共享 cwd。
- [S-015](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/examples/extensions/subagent/index.ts#L239)：subagent example 注册 extension tool，以 pi --mode json --no-session 子进程执行并通过 cwd 共享 workspace。
- [D-012](../evidence/observations.jsonl)：Mario 用浏览器脚本和按需读取说明展示 CLI 组合方式；这是具体案例与设计立场。

范围：default core plus example extension。状态：supported；置信度：high。

## C-014

Pi 已提供稳定的 agent/message/tool/compaction/retry 事件及 JSON/RPC 输出，但 OTel 风格 trace/span 仍是设计稿，不是 v0.80.7 的默认核心实现。

- [D-005](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/docs/json.md#L1)：JSON mode 文档列出 session、agent、turn、message、tool、compaction 与 retry 事件。
- [D-009](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/docs/observability.md#L3)：Observability Design Notes 要求 vendor-neutral events，并把 trace/span adapter 描述为目标设计而非已完成 API。
- [R-001](../traces/normalized/R-001-text-only.normalized.jsonl)：真实 SiFlow 文本场景观察到 session -> agent/turn -> assistant stream -> turn_end -> agent_end -> settled，最终 PI_TEXT_OK。
- [R-002](../traces/normalized/R-002-read-tool.normalized.jsonl)：真实 read 场景观察到两次 turn、read start/end、toolResult 回填与最终值 314159。
- [I-003](../evidence/observations.jsonl)：Scott 的实践区分运行故障与已结束但答错；这为解释事件完成和任务验收的边界提供了使用者视角。

范围：observability surfaces。状态：supported；置信度：medium。

## C-015

工具默认并行；全局 sequential 或任一命中工具声明 executionMode=sequential 会使整批串行。并行结果按模型调用顺序生成 toolResult，再由 AgentSession 接入持久化。

- [S-001](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/src/agent-loop.ts#L95)：runAgentLoop 实现双层循环、模型流、toolUse、steering/follow-up、并行/串行工具、length-stop 拒绝执行与 hooks。
- [X-001](../runtime-tests.md)：agent-core 定向 Vitest：agent-loop.test.ts 与 agent.test.ts 共 39/39 通过。
- [X-004](../traces/checks/20261020/X-004.vitest.json)：2026-10-20 agent 定向测试：39 passed，0 failed，0 skipped；exit=0。
- [S-018](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/src/agent-loop.ts#L375)：工具开始事件先于 preflight；length、unknown、blocked 路径可返回错误而不调用 execute；整批结果都 terminate 才停止工具 follow-up。

范围：agent-core tool execution。状态：supported；置信度：high。

## C-017

扩展可以实现工具阻断，但此控制点是应用可选 hook，不是不可绕过的全局安全边界。

- [S-003](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L415)：AgentSession 把 extension tool_call/tool_result 安装为 agent before/afterToolCall，并动态刷新统一 tool registry。
- [S-017](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/examples/extensions/protected-paths.ts#L1)：protected-paths example 通过可选 tool_call hook 阻断 write/edit，表明权限策略属于 extension。
- [D-002](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/docs/security.md#L3)：安全文档明确 project trust 不是 sandbox，默认工具和 extensions 以 Pi 进程权限运行。

范围：extension tool hooks。状态：supported；置信度：high。

## C-018

orchestrator 是实验性的多 Pi RPC 进程 supervisor，负责 spawn、事件复用、session 元数据和退出清理；它不是默认 Coding Agent 内的 subagent 机制。

- [D-010](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/orchestrator/README.md#L1)：Orchestrator README 将包标为 experimental、API/行为不稳定。
- [S-016](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/orchestrator/src/supervisor.ts#L63)：OrchestratorSupervisor 为每个 instance 创建独立 RPC Pi 进程、转发 events、同步 session metadata 并处理退出。

范围：packages/orchestrator。状态：supported；置信度：medium。

## C-019

Coding Agent 通过 ModelRegistry 解析模型与请求凭据，再调用 pi-ai/compat.streamSimple；compat 根据内置模型与 API 覆盖条件选择 Models 或 API registry。

- [S-024](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/ai/src/compat.ts#L209)：Coding Agent SDK 使用 ModelRegistry 和 compat.streamSimple；匹配内置模型且 API 未覆盖时转 compatModels，否则按 model.api 查 API registry。
- [S-012](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/ai/src/models.ts#L24)：pi-ai Models 将 provider catalog、auth resolution 与 stream dispatch 统一在运行时 collection。
- [R-005](../runtime-tests.md)：Pi --list-models 成功解析自定义 SiFlow models.json，显示 qwen3.6-35ba3b、262.1K context 与 16.4K max output。
- [R-001](../traces/normalized/R-001-text-only.normalized.jsonl)：真实 SiFlow 文本场景观察到 session -> agent/turn -> assistant stream -> turn_end -> agent_end -> settled，最终 PI_TEXT_OK。

范围：v0.80.7 current Coding Agent model request path。状态：supported；置信度：high。

## C-020

恢复策略按错误类型分层：context overflow 走 compaction，其他 retryable provider error 走指数退避，truncated tool-call 参数则拒绝执行并回送错误。

- [S-001](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/src/agent-loop.ts#L95)：runAgentLoop 实现双层循环、模型流、toolUse、steering/follow-up、并行/串行工具、length-stop 拒绝执行与 hooks。
- [S-009](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L1890)：AgentSession 把 overflow 与 threshold 分开处理，overflow 最多一次 compact-and-retry，并持久化 compaction entry 后重建 context。
- [S-010](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L2573)：普通 retryable assistant error 使用受 maxRetries 限制的指数退避，error 留在 session 但从 live context 移除。
- [X-001](../runtime-tests.md)：agent-core 定向 Vitest：agent-loop.test.ts 与 agent.test.ts 共 39/39 通过。
- [X-003](../runtime-tests.md)：Coding Agent 定向 Vitest：compaction、network retry、session context 共 31/31 通过。
- [X-004](../traces/checks/20261020/X-004.vitest.json)：2026-10-20 agent 定向测试：39 passed，0 failed，0 skipped；exit=0。
- [X-005](../traces/checks/20261020/X-005.vitest.json)：2026-10-20 coding-agent 定向测试：12 passed，0 failed，5 skipped；exit=0。5 项真实模型 e2e 因未提供凭据跳过；通过项包含 settlement、动态工具、网络错误重试与压缩后队列。
- [X-008](../traces/checks/20261020-followup/X-008.vitest.json)：2026-10-20 coding-agent 定向测试：15 passed，0 failed，0 skipped；exit=0。
- [S-018](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/src/agent-loop.ts#L375)：工具开始事件先于 preflight；length、unknown、blocked 路径可返回错误而不调用 execute；整批结果都 terminate 才停止工具 follow-up。
- [S-031](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/ai/src/utils/retry.ts#L1)：isRetryableAssistantError 要求 stopReason=error 且有 errorMessage；先排除配额/账单限制，再匹配临时服务或传输错误文本，不调用模型判断。
- [S-034](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/tools/bash.ts#L395)：内置 bash 将非零退出码或执行超时转为异常；工具执行器捕获后生成错误 toolResult，供后续模型决策，不直接进入 AgentSession 的 assistant error 重试分类。

范围：coding-agent and agent-core failure paths。状态：supported；置信度：high。

## C-021

tool_execution_start 标记工具调用进入处理流程；unknown、hook block 与 length-stop 路径也会发出该事件，因此单靠它不能确认 handler 已执行。

- [S-018](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/src/agent-loop.ts#L375)：工具开始事件先于 preflight；length、unknown、blocked 路径可返回错误而不调用 execute；整批结果都 terminate 才停止工具 follow-up。

范围：Pi v0.80.7 pinned mechanism recheck。状态：supported；置信度：medium。

## C-022

message_end 由 Agent 先更新内存消息，再等待产品层 extension 和持久化处理；异步 extension 不应使 assistant 与对应 toolResult 的记录顺序颠倒。

- [S-019](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L547)：Agent 先处理 message_end 更新 live state，再等待 AgentSession；extension message_end 可就地替换消息，之后通知外部监听者并追加 session entry。
- [X-005](../traces/checks/20261020/X-005.vitest.json)：2026-10-20 coding-agent 定向测试：12 passed，0 failed，5 skipped；exit=0。5 项真实模型 e2e 因未提供凭据跳过；通过项包含 settlement、动态工具、网络错误重试与压缩后队列。

范围：Pi v0.80.7 pinned mechanism recheck。状态：supported；置信度：high。

## C-023

新建持久会话通常在首条 assistant entry 出现后才创建并写入文件；内存已有 user entry 或已分配 sessionFile 路径并不保证文件已经存在。

- [S-020](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/session-manager.ts#L788)：新会话先在内存追加 entry；首次 assistant entry 触发整批写入，之后逐条追加；已有空文件和格式迁移有明确重写路径。
- [X-006](../traces/checks/20261020/X-006.vitest.json)：2026-10-20 coding-agent 定向测试：46 passed，1 failed，0 skipped；exit=1。失败发生于 CLI 子进程模块解析；46 项进程内 context/tree 测试通过，后续 X-010 加载器对照单独记录。

范围：Pi v0.80.7 pinned mechanism recheck。状态：supported；置信度：high。

## C-024

压缩后的 continuation 取决于响应状态与队列：已完成 stop 的 overflow 不重答，threshold 后有 queued messages 时可继续处理新输入，旧边界前的 usage 不重复触发压缩。

- [S-021](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L1890)：已完成 stop 响应即使 usage 越界也只压缩、不重答；错误 overflow 有一次恢复限制；threshold 后存在 queued messages 时仍继续处理队列。
- [X-008](../traces/checks/20261020-followup/X-008.vitest.json)：2026-10-20 coding-agent 定向测试：15 passed，0 failed，0 skipped；exit=0。
- [X-005](../traces/checks/20261020/X-005.vitest.json)：2026-10-20 coding-agent 定向测试：12 passed，0 failed，5 skipped；exit=0。5 项真实模型 e2e 因未提供凭据跳过；通过项包含 settlement、动态工具、网络错误重试与压缩后队列。
- [S-036](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/modes/interactive/interactive-mode.ts#L3990)：终端将压缩期间的普通输入暂存在 compactionQueuedMessages；压缩结束后，无待重试时第一条普通输入作为 prompt，余下按类型入队，有待重试时按 steering/follow-up 类型转交。

范围：Pi v0.80.7 pinned mechanism recheck。状态：supported；置信度：high。

## C-025

Coding Agent 的应用消息与 provider messages 不是同一集合；custom、bashExecution 和 summary 在 convertToLlm 中映射为 user，标记 excludeFromContext 的 bashExecution 被过滤。

- [S-022](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/messages.ts#L146)：convertToLlm 将 custom/bashExecution/summary 转为 user messages，excludeFromContext 的 bashExecution 被过滤，普通 user/assistant/toolResult 原样保留。
- [S-008](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/session-manager.ts#L322)：SessionManager 实现 v3 append-only JSONL tree、active leaf、分支选取、entry 到应用消息的转换、compaction-aware context、restore 与 fork。

范围：Pi v0.80.7 pinned mechanism recheck。状态：supported；置信度：medium。

## C-026

Coding Agent 的 active tools、system prompt、model 和 thinking level 可在 prepareNextTurn 边界更新到下一请求；registry 与 active set 分开维护。

- [S-023](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L467)：AgentSession 在 prepareNextTurn 阶段用当前 system prompt、tools、model 和 thinking level 刷新下一次模型请求。
- [X-005](../traces/checks/20261020/X-005.vitest.json)：2026-10-20 coding-agent 定向测试：12 passed，0 failed，5 skipped；exit=0。5 项真实模型 e2e 因未提供凭据跳过；通过项包含 settlement、动态工具、网络错误重试与压缩后队列。

范围：Pi v0.80.7 pinned mechanism recheck。状态：supported；置信度：medium。

## C-027

工具返回值区分 content 和 details。当前所检查的两个 provider 序列化路径使用 content 构造模型结果，details 仍可供应用消息、持久化和 UI 使用。

- [S-025](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/src/types.ts#L350)：AgentToolResult 把模型内容 content 与日志/界面 details 分开定义。
- [S-026](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/ai/src/api/openai-completions.ts#L1026)：已检查的 OpenAI Completions 与 Anthropic 消息构造路径从 tool result 的 content 组织文本/图像，没有自动展开 details。
- [D-011](../evidence/observations.jsonl)：Mario 的设计回顾强调对模型上下文和交互过程的控制，并说明分离工具返回内容与界面数据。

范围：v0.80.7 current AgentSession path。状态：supported；置信度：medium。

## C-028

AgentSession.reload() 刷新配置、provider 与资源并重建 extension runner/tool registry；本方法继续使用当前 sessionManager，session_start 通知受 bindings 条件控制。

- [S-027](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L2490)：AgentSession.reload 先发 shutdown，再刷新设置、provider registry 与资源，重建 runner/tool registry，最后在绑定存在时发 session_start。

范围：v0.80.7 current AgentSession path。状态：supported；置信度：medium。

## C-029

reserveTokens 与 keepRecentTokens 控制不同阶段：默认 16384 用于压缩触发阈值，默认 20000 用于估算保留片段；切点选择还受消息类型约束。

- [S-028](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/settings-manager.ts#L773)：默认 reserveTokens=16384，keepRecentTokens=20000；两者由不同 getter 提供。
- [S-029](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/compaction/compaction.ts#L176)：shouldCompact 使用窗口减 reserveTokens；findCutPoint 按 keepRecentTokens 向后估算保留量并选择合法切点，toolResult 不作为切点。
- [S-035](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/compaction/compaction.ts#L441)：默认压缩先按切点准备旧历史与可能存在的长任务前缀，再由模型生成结构化摘要；split turn 将历史摘要与前缀摘要合并，末尾附上代码提取的文件操作路径。

范围：v0.80.7 current AgentSession path。状态：supported；置信度：medium。

## C-030

Pi 的请求适配与服务端的模型输入编码是不同阶段：前者组织 API 字段，后者可按模型模板将角色、内容和工具说明编码为 token 序列。所查 Qwen3.8-27B 与 DeepSeek V4 Flash 公开源码展示了不同的角色标记和工具调用格式。

- [S-001](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/src/agent-loop.ts#L95)：runAgentLoop 实现双层循环、模型流、toolUse、steering/follow-up、并行/串行工具、length-stop 拒绝执行与 hooks。
- [S-037](../evidence/observations.jsonl)：Pi 的 OpenAI Completions 适配器将 systemPrompt 按兼容配置转为 system/developer 消息，将工具 name/description/parameters 放入独立 tools 字段。
- [S-038](../evidence/observations.jsonl)：查阅的 Qwen3.8-27B 模板将工具 schema 与调用格式说明写入 system 段，再接应用 system 文本；用 im_start/im_end 分隔消息，工具调用使用 XML 风格，tool 结果包装为 user 段的 tool_response。
- [S-039](../evidence/observations.jsonl)：DeepSeek V4 Flash 参考编码器将 system 内容与工具 schema 写入输入前部，用专有角色标记组织序列；DSML 表达工具调用，工具结果预处理为 user 内容中的 tool_result，再解析生成内容回结构化消息。
- [D-013](../evidence/observations.jsonl)：Transformers 官方文档说明聊天消息由模型对应模板转换为带控制标记的序列，再分词为 token 输入；不同模型可以使用不同对话格式。

范围：Pinned Pi openai-completions adapter plus separately dated external template examples。状态：supported；置信度：high。
