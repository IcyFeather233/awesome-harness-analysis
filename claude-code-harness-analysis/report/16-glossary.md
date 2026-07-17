# 全局术语表

> **证据边界。** 本报告分析 source-only commit `16a676f`。其 1,884 个 TS/TSX 文件、关键 symbol 与 feature gates 和论文所述 Claude Code v2.1.88 corpus 强指纹一致，但缺少 package version、上游 tree hash、build manifest，不能视为已证明的 exact 官方 artifact。快照仍有 657 个无法解析的相对 import；除 SiFlow 协议探针外，主循环、安全、session 与 subagent 结论均为 static-only。官方材料只支持产品立场，五价值/十三原则是 analyst synthesis。[X: X-001–X-003] [D: D-001–D-008] [C: C-001, C-024–C-026]


这份术语表用于快速回查；正文第一次依赖某个关键概念时仍应在局部解释，不能只把读者送到这里。

## Harness 与控制循环

- **Agent harness**：包围模型的非模型基础设施，负责 context、模型调用、tools、permissions、state、delegation、recovery 和 observability。模型决定“想做什么”，harness 决定“看到什么、能做什么、如何执行、怎样留下状态”。
- **CLI / REPL / SDK**：CLI 是 command-line interface；REPL 是 Read-Eval-Print Loop 式连续终端交互；SDK 是供程序调用的 Software Development Kit 接口。
- **Surface**：用户或外部程序进入系统的接口，例如 REPL、`--print`、SDK、server 或 bridge。
- **Headless / structured I/O**：headless 表示没有交互式终端 UI；structured I/O 用 JSON/event records 等机器可解析格式交换输入输出。
- **Adapter**：把某个 surface 的输入、输出和 live state 转成共享 core 所需 messages、tools 和 callbacks 的层。
- **Bootstrap**：进程启动后的最小分发层，先处理 version、help、feature fast path 或子命令选择，再决定是否加载完整 main/runtime。它不等于 agent loop。
- **AppState**：交互式进程中的 live mutable state，包括当前消息、任务、agent、permission context、渲染状态和回调。它可能被写入 transcript 的结果影响，但本身不是 durable transcript。
- **QueryGuard**：REPL 入口的并发保护，决定当前主 query 是否获得执行权、后续输入是否排队或变成 attachment；它保护 live state，不是模型安全策略。
- **QueryEngine**：`--print`/SDK/headless 侧的 controller，负责 structured I/O、非交互 permission 语义和事件消费，然后调用共享 `query()`。
- **Core/query loop**：在 model request、tool execution、result feedback 和 stop/recovery 之间迭代的控制器。
- **Session**：横跨多个用户提交的会话容器，具有 session ID、live state 和可选 durable transcript。
- **User query**：一次用户提交从进入 `query()` 到 terminal transition 的范围。
- **Agentic iteration**：query loop 的一次循环；通常构造一次 model request，并可能执行一组 tools，再决定 continue 或 terminal。
- **Model/API request**：对模型 provider 的一次调用边界。retry/fallback 可能让一次 iteration 或 query 出现额外网络尝试，因此不能把 iteration 数和 HTTP request 数机械画等号。
- **AsyncGenerator**：可以在函数尚未结束时不断 yield event/result 的异步迭代器；Claude Code 用它连接 streaming core 与 REPL/SDK consumer。
- **Terminal transition**：当前 query 明确停止、失败或中断；不等于进程退出或 session 删除。

## Context 与压缩

- **Context**：本轮模型实际收到的 system content、messages、tool schemas 和动态附件，不只是“聊天历史”。
- **CLAUDE.md**：用户或项目维护的 instruction 文件，可按 managed/user/project/local/目录层级进入 context；它不是 transcript。
- **Context window**：模型一次 request 可处理的 token 容量上限。
- **System prompt/system context/user context**：分别表示高优先级系统指令、harness 计算的环境/模式信息，以及以 user-side context 带入的项目规则、memory 和附件。
- **Startup / lazy / per-turn**：分别表示 session 建立时加载、触发时按需加载、当前提交/iteration 产生。
- **Carry-forward**：已经进入 live message chain 并继续带到后续 request，直到被 projection/compaction 替换。
- **Durable**：写到进程外介质，重启后仍可能读取；不保证每轮都进入模型。
- **Provenance**：一段 context 的来源和作用域，例如 managed/user/project CLAUDE.md、skill 或 tool result。
- **Attachment**：harness 在用户文本之外追加的 runtime context，例如 diagnostics、task notification 或 MCP/agent delta。
- **Tool-result budget**：优先限制旧工具输出占用的 token 预算，不等于总结完整对话。
- **Snip / microcompact / collapse**：从局部剪除历史，到细粒度压缩，再到 feature-gated 的较大结构折叠，粒度和条件不同。
- **Autocompact**：达到阈值后生成摘要边界，并重注入仍需保留的文件、plan、skill 和动态状态。
- **Boundary/survivor**：boundary 指摘要开始代表旧历史的位置；survivor 指压缩后仍保留或重注入的信息。

## Tools 与扩展

- **Capability**：harness 能向模型或内部流程提供的一项观察/行动能力。
- **Registry/tool pool**：registry 是已知能力集合；tool pool 是当前配置和 mode 下的候选集合。
- **Visible schema**：真正放入 model request 的 tool name/description/input schema。
- **Registered / eligible / visible / requested / authorized / executed**：registered 表示 loader 已发现能力；eligible 表示当前 mode/feature/policy 未过滤；visible 表示模型本轮看见 schema；requested 表示模型实际发出 `tool_use`；authorized 表示 hooks/permission 允许具体 input；executed 表示 backend 已产生或尝试产生副作用。
- **Dispatch/router**：根据 `tool_use` name 找实现、验证 input，并进入 hook/permission/execution 的过程。
- **MCP**：Model Context Protocol；外部 server 可以提供 tools、resources 或 prompts。server 已连接不代表每项能力都可见或获准执行。
- **Plugin**：跨 commands、agents、skills、hooks、MCP、LSP 等 component 的打包/分发格式，不是单一 execution backend。
- **Skill**：按需加载的 instruction/workflow/resource，主要改变 context；不是天然拥有副作用权限的进程。
- **Hook**：在 lifecycle event 上观察、修改或阻断行为的扩展；某些 hook 可执行外部命令，因此也属于审计面。
- **LSP**：Language Server Protocol，为代码符号、诊断等语言能力提供服务；不等于 MCP tool。
- **Provider / retry / fallback**：provider 是模型服务承载路径；retry 在相近配置上重试暂时失败；fallback 切换 request mode、model 或 provider path。
- **SSE**：Server-Sent Events；服务器通过一个持续 HTTP response 依次发送流式事件。

## 权限与执行边界

- **Permission rule**：针对 tool 与可选 input pattern 的 allow/ask/deny 规则，并带有 managed/user/project/CLI/session 等来源。
- **Permission mode**：一组默认决策策略，例如 `plan` 或 `dontAsk`；它仍与具体 rules 和 tool safety checks 组合。
- **Approval**：当 decision 为 ask 且 surface 可交互时，由人作出的单次或有作用域的决定。
- **Sandbox**：限制进程可访问的 filesystem/network 等 OS 边界；它不等于 approval，也不是事务式 rollback。
- **Fail closed**：权限判断失败、必要信息不足或无法询问时拒绝/停止，而不是默认允许。
- **PermissionGate**：本报告图中的读者概念，指 schema/input validation、hook、permission resolver 和可选 prompt 组成的治理段；它不是单个一定同名的源码类。
- **Classifier**：feature-gated auto mode 中辅助判断请求风险的模型化步骤；它不是 sandbox。
- **Canonical path**：证据最完整的主要执行路径。证明 canonical path 受控，不自动覆盖 startup、hook、MCP lifecycle 等所有副作用。
- **Trust freshness**：resume 后根据当前 settings/CLI 重新建立授权，而不是从旧 transcript 恢复 session-scoped grants。

## Delegation、状态与恢复

- **Subagent/child**：由 parent 委派、拥有独立或重建 context 的 agent execution；其 process/workspace/policy 是否隔离必须另行说明。
- **Sidechain**：child 使用的独立 transcript 分支，通常只把 summary/result 返回 parent。
- **Worktree**：Git 提供的独立工作目录，共享 repository object database 但有独立 checkout；不是 container。
- **AbortController**：JavaScript 取消信号对象。共享 controller 表示取消会传播，独立 controller 表示需要单独终止。
- **Teammate/mailbox**：团队成员运行机制及其文件式消息通道；mailbox 可跨进程持久化 unread message。
- **JSONL**：一行一个 JSON record 的追加式日志格式。
- **parentUuid**：message/record 指向逻辑父记录的 ID，用于恢复当前会话分支。
- **Resume / fork / rewind**：resume 继续会话 identity/history；fork 复制可恢复 history 到新 session identity；rewind 是范围有限的显式文件恢复。三者都不等于整个世界回滚。
- **Graceful shutdown**：按优先级 flush/persist、运行有界 hooks/analytics 并最终退出；graceful 不表示无限等待。

## 观测与证据

- **Event / metric / span / trace**：event 是离散记录；metric 是聚合数值；span 是有时间边界的操作；trace 是 parent-child spans 组成的执行树。
- **Profiler / Perfetto / OTel**：profiler 做本地阶段诊断；Perfetto 使用 Chrome trace 格式可视化时序；OpenTelemetry 提供通用 span/trace 语义和 exporter。
- **Sink / sampling / exporter**：sink/exporter 是 event 或 span 的接收端；sampling 是按比例或规则选择只记录一部分事件。它们影响“能观测到什么”，不改变 harness 本身的控制流。
- **TTFT / TTLT**：time to first token 与 time to last token，分别衡量请求到首个 token、请求到最后一个 token 的延迟；两者不能互相替代。
- **Redaction**：在 telemetry 中删除或替换 prompt、代码、路径等敏感内容。
- **D/S/R/X/I**：documented intent、static source、runtime observation、controlled experiment、analyst inference 五类证据。
- **Static-only / runtime-verified**：前者只在源码中恢复，后者至少有匹配 target runtime trace；二者不能混写。
- **Feature gate / DCE**：feature gate 控制路径是否加入或启用；DCE 会在构建时删除未选择分支。
- **Build graph / manifest / source map**：build graph 是模块依赖闭包；manifest/lock 记录版本和依赖；source map 把 bundle 位置映射回原始源码。三者缺失会阻止精确重建 external artifact。
- **Protocol probe / target runtime**：protocol probe 直接测试 provider endpoint 的 HTTP/SSE/tool-use 方言；target runtime 是 Claude Code 自身启动后的 loop、permission、tool 和 persistence 行为。前者不能替代后者。
- **callModel seam**：`query()` 与模型 provider 之间可被测试替身接管的依赖边界；用于 scripted model 实验，不表示生产路径里有第二套 loop。
- **Copy-on-write / VM checkpoint**：前者在首次写入时才复制私有数据；后者保存虚拟机状态。它们是比普通 session resume 更强的回滚基础设施。
- **Strong fingerprint / exact identity**：前者表示文件数、symbols、feature signatures 高度匹配；后者要求 package/tree hash 或字节级 artifact linkage。
- **Coverage / reachability**：coverage 说明检查了哪些 surface/config/scenario；reachability 说明一条 source path 在具体 build/config 中是否能实际到达。
