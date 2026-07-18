#!/usr/bin/env python3
"""Regenerate the curated report for the pinned Pi analysis bundle."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "report"
REPORTS: dict[str, str] = {}

REPORTS["00-design-space-and-running-example.md"] = r"""# 00 设计空间与贯穿案例

Pi 的架构不能只用“有哪些 package”来解释。更有区分度的问题是：推理放在哪里、产品编排由谁拥有、默认信任边界在哪里、上下文和持久状态如何增长，以及扩展能力由核心还是用户定义。

## 六个设计问题

| 设计问题 | Pi `v0.80.7` 的当前机制 | 关键边界/部署条件 | 可选设计 | 证据与置信度 | 最小反证 |
|---|---|---|---|---|---|
| 推理与控制放在哪里？ | 模型决定下一步；`runAgentLoop()` 只负责 model/tool/queue/stop 的确定性循环 | planner、任务状态和产品 retry 不在 low-level loop 中 | harness 内置 planner、typed graph 或 task state machine | `D-001`, `S-001`, `R-002`, `X-001`；高 | 找到另一个绕过 `runAgentLoop()` 的产品级 model/tool loop |
| 产品编排由谁拥有？ | 当前由 Coding Agent `AgentSession` 拥有；通用 `AgentHarness` 是迁移目标 | v0.80.7 两者共享 low-level loop，但不是叠加调用；新 harness 尚缺 auto-compaction/retry/migration | 单一 controller，或每个产品分别包装 low-level loop | `D-003`, `D-008`, `S-002`, `S-011`, `X-002`；高 | 证明 Coding Agent 已默认实例化 `AgentHarness` 并行为等价 |
| 默认安全姿态是什么？ | read/write/edit/bash 与 extensions 继承 Pi 进程权限；project trust 只保护启动资源加载 | unattended/untrusted 部署必须另加 whole-process container、VM 或完整工具路由 | deny-first 逐工具授权、强制进程内 policy、默认容器隔离 | `D-002`, `D-007`, `S-006`, `S-017`；高 | 找到不可绕过且默认启用的全局 tool permission/sandbox gate |
| 扩展面如何划分？ | tool registry 合并 built-ins/custom/extensions，hooks 可改 input/context/tool/provider/session；MCP/subagent 不进入核心假设 | extension 与 host 同权限；不同 extension 可定义不一致的安全和 delegation 语义 | 固定内置能力，或统一 capability/plugin protocol | `D-004`, `S-003`, `S-015`；高 | 证明 MCP/subagent 是默认 registry 的强制内建能力 |
| 什么状态是 durable 的？ | append-only JSONL v3 tree 保存 message、branch、compaction 等 entry；workspace 独立持久 | resume/fork 恢复 conversation branch，不恢复文件系统 checkpoint | mutable database row、完整 checkpoint、event sourcing + workspace snapshot | `S-008`, `R-003`, `R-004`；高 | 新进程不读取 JSONL 也能恢复相同 active branch，或 fork 自动回滚 workspace |
| 失败如何恢复？ | truncated tool call 拒绝执行；provider retry、overflow compaction 与 threshold compaction 分层 | retry budget、是否重答及 durable error 处理由产品层决定；真实 crash/半持久 turn 未覆盖 | fail-fast、统一 retry、每轮 checkpoint 回滚 | `S-001`, `S-009`, `S-010`, `X-001`, `X-003`；高 | 注入同类错误后观察到无界 retry、截断 call 被执行或统一回滚 |

这些是“设计选择及其实现”，不是对作者动机的自由推测。仓库文档明确说明 minimal harness、aggressive extensibility 和外部隔离边界；“为什么选 JSONL 而不是数据库”等未文档化原因只作为可观察权衡讨论。[D: D-001, D-002, D-004]

![Pi design space](../diagrams/generated/pi-design-space.png)

> 图 A（gpt-image-2 读者插图）：左列是文档化产品立场，中列是源码恢复出的机制，右列是分析者根据实现和失败边界归纳的权衡；点线表示分析推断，不代表作者声明。图像 provenance 与语义审查见[生成图 metadata](../diagrams/generated/metadata.json)；设计映射来自[story spec](../diagrams/story-specs.json)和下列 Evidence IDs。Evidence: `D-001`, `D-002`, `D-003`, `D-004`, `D-007`, `D-008`, `S-001`, `S-003`, `S-007`, `S-008`, `S-011`, `S-017`, `R-004`, `X-002`。

## 贯穿案例：一次真实 read turn

本报告以 `R-SCENARIO-002` 作为贯穿案例，而不是构造一条未运行的“理想路径”。场景在隔离 HOME 和合成 workspace 中启动 Pi JSON mode，只开放 `read`，要求读取 `fixture.txt` 并回答其内容。SiFlow `qwen3.6-35ba3b` 实际走过：

1. `main()` 进入共享 Coding Agent runtime；
2. `AgentSession` 解析输入并启动 turn；
3. `runAgentLoop()` 用 active session、system prompt 和 read schema 形成第一次 provider request；
4. 模型返回一个 `read` tool call；
5. registry dispatch read，事件流发出 `tool_execution_start` 与 `tool_execution_end`；
6. `314159` 作为 toolResult 追加到 transcript/context；
7. 第二次 provider request 带上先前 assistant message 和 toolResult；
8. 模型返回最终文本，不再请求工具；
9. low-level loop 发出 `agent_end`，产品层随后发出 `agent_settled`。[R: R-002] [S: S-001, S-002]

![Observed Pi turn](../diagrams/generated/pi-observed-turn.png)

> 图 B（gpt-image-2 读者插图）：严格展示同一次真实 read trace 的两轮迭代、`314159` 回填，以及 `agent_end -> agent_settled`；未把 retry、compaction 或 resume 伪装成该场景发生的分支。图像 provenance 与语义审查见[生成图 metadata](../diagrams/generated/metadata.json)；运行事实来自 `R-SCENARIO-002` 和下列 Evidence IDs。Evidence: `S-001`, `S-002`, `S-008`, `S-009`, `S-010`, `R-002`, `R-003`, `R-004`, `X-003`。

## 这个案例不能证明什么

该 trace 没有启用 extensions、skills、context files 或 project approval，也没有执行 bash/write/edit。因此它能证明 model -> read -> toolResult -> second model call -> settled 至少发生过一次，不能证明：

- 所有工具都经过 permission gate；Pi 默认不存在这样的全局 gate；
- deny 之后没有文件、进程或网络副作用；本轮没有做 deny fault injection；
- compaction、retry、subagent 或 session resume 在这一次 read turn 中发生；这些由其他实验或静态证据支撑；
- 真实用户任务中的路径频率、成本分布或长期正确性。

后续章节会沿用这个案例解释 loop、context、tool result 和 event stream；对于它没有覆盖的安全、恢复与持久化路径，会显式切换到对应的 `S`、`R` 或 `X` 证据。
"""

REPORTS["01-scope-method.md"] = r"""# 01 范围与方法

## 冻结对象

- Repository：`https://github.com/earendil-works/pi`
- Tag：`v0.80.7`
- Commit：`818d67457cdd6b60bce6b121d16b23141c252dd8`
- Worktree：detached HEAD，分析开始和结束时目标代码无 tracked changes
- Runtime：Linux x86_64；临时 Node `22.19.0`；npm `10.9.3`；Vitest `4.1.9`
- Real model：`siflow/qwen3.6-35ba3b`，OpenAI-compatible endpoint；无 API key

完整配置见 [manifest.json](../manifest.json)。

## 证据等级

| 标记 | 证据来源 | 可以建立 | 不能单独建立 | 本报告实例 |
|---|---|---|---|---|
| `D` | 固定 commit 的仓库文档 | 明确产品边界、公开设计立场、已知未完成项 | 代码一定实现文档描述，或生产默认启用 | security、extension、AgentHarness lifecycle 文档 |
| `S` | 固定 commit 源码与测试 contract | 类型、控制流、condition 和可到达路径 | 该路径在本轮运行过，或生产出现频率 | `runAgentLoop`、`AgentSession`、JSONL v3 |
| `R` | 真实 SiFlow + official Pi runtime | 命名配置下一次确实发生的路径和事件顺序 | 其他 provider/mode/tool/platform 等价 | text、read-tool、跨进程 resume |
| `X` | faux provider/定向 test suite | controller 分支、顺序、反例和失败 contract | 真实模型质量或部署安全 | 39 + 61 + 31 tests |
| `I` | 多条 D/S/R/X 的分析综合 | 明示 tradeoff、风险和下一步实验 | 作者意图或 HIR 中的直接事实 | workspace/session 缺少共同 checkpoint 的后果 |

每条 claim 都有 falsification test；每个 HIR node/edge 都有 evidence ID。严格 validator 结果为 `0 errors, 0 warnings`。

## 动态安全边界

所有真实 model runs 使用：

- `/tmp/pi-analysis-runtime/home` 作为独立 HOME；
- `/tmp/pi-analysis-runtime/fixture` 作为合成 workspace；
- `/tmp/pi-analysis-runtime/sessions` 作为合成 session store；
- `--no-extensions --no-skills --no-prompt-templates --no-context-files --no-approve`；
- 无工具或只开放 `read`；
- 不运行 write/edit/bash；
- raw trace 只包含合成内容，normalized trace 删除 prompt、thinking、工具参数和文件内容。

## 解释边界

`R` 只能证明某路径在指定模式中发生过一次，不能证明生产频率或所有配置。没有运行到的 path 仍可能存在；没有在源码中找到的行为也不能在 coverage 不完整时直接判定为不存在。设计“为什么”仅在文档明确说明时归为 documented intent，否则只讨论可观察 tradeoff。

## 覆盖

14 个 codebook 模块全部有状态：interfaces/core loop/model/tools/session/recovery 等为 analyzed；context、sandbox、subagents、observability 为 partial。详细文件与未覆盖面见 [coverage.json](../evidence/coverage.json)。
"""

REPORTS["02-interfaces-lifecycle.md"] = r"""# 02 入口与生命周期

## 入口收敛

`main()` 解析 CLI、session、trust、资源和模型，然后创建 `AgentSessionRuntime`。最终只有 UI 适配不同：RPC 进入 `runRpcMode()`，TUI 进入 `InteractiveMode`，print/JSON 进入 `runPrintMode()`；它们共享同一个 `AgentSession`。[S: S-012, S-013]

```text
CLI args / stdin
  -> main()
  -> SessionManager + cwd-bound services
  -> AgentSessionRuntime
  -> AgentSession
  -> interactive | print/json | rpc adapter
```

关键源码：`packages/coding-agent/src/main.ts:650-857`、`packages/coding-agent/src/core/agent-session-runtime.ts:67-353`。

## 生命周期

1. 选择/创建/恢复 `SessionManager`。
2. 以 effective cwd 创建 settings、auth、model registry、resource loader。
3. 解析 project trust 后装载最终 extension/resource 集合。
4. 创建 `AgentSession`，绑定目标 mode 的 extension UI/context。
5. prompt 后进入共享 loop；JSON/RPC 只是转发结构化 event。
6. session switch/new/fork/import 会先发 `session_shutdown`，再重建 cwd-bound runtime，而不是只替换 message array。[S: S-014]

## 模式差异

- Interactive 有 trust prompt 和完整 TUI。
- Print 输出最终 assistant text；JSON 输出每个 session event。
- RPC 用 LF-delimited JSON 收命令、回 response，并并行输出 agent events 与 extension UI request。
- 非交互模式没有 project trust UI；default `ask` 在无既有决策时等价于不信任项目资源。[S: S-006]

本轮真实运行覆盖 JSON mode；TUI 与 RPC 源码已检查但未端到端启动。

## 对象与结束边界

| 对象/层 | 谁创建或拥有 | 生命周期 | Durable 内容 | 结束时发生什么 |
|---|---|---|---|---|
| CLI mode adapter | `main()` 按 interactive/print/JSON/RPC 选择 | 单进程 UI/transport 生命周期 | 自身不持久化 conversation | 断开 adapter 不等于删除 session 文件 |
| `AgentSessionRuntime` | main 的 cwd-bound runtime factory | 当前 cwd/session 组合 | settings/auth/resource decisions 由各自 store 持久 | session switch/new/fork/import 时先 shutdown，再重建服务 |
| `AgentSession` | 当前 Coding Agent 产品路径 | 可处理多次 prompt，直到 switch/shutdown | message/compaction 等通过 `SessionManager` 追加 JSONL | `agent_end` 后仍可能 retry/compact/queue；`agent_settled` 才是产品空闲 |
| Low-level `Agent` / `runAgentLoop` | `AgentSession` 每次 prompt 驱动 | 一次 agent run，可含多次 turn | transcript 由上层 session 选择是否保存 | 无工具、steering、follow-up 后发 `agent_end` |
| Session tree | `SessionManager` | 跨 prompt、进程、branch/fork | JSONL v3 header + parent-linked entries | resume 重建 active branch，不重建旧 workspace |
"""

REPORTS["03-core-loop.md"] = r"""# 03 核心循环与编排

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
"""

REPORTS["04-context-memory-compaction.md"] = r"""# 04 上下文、记忆与压缩

![Context lifecycle](../diagrams/generated/pi-context-lifecycle-v2.png)

> 图 3（gpt-image-2 读者插图）：startup/lazy、carry-forward 和 runtime 三类来源先汇入同一入口，再依次经过 `transformContext -> convertToLlm -> Per-request context -> Model request`；compaction 是虚线条件回路。第一版因错误画出 tool result 直达 model 而被拒绝，本图为修正并复审后的 v2。图像的 prompt、output hash 与语义审查见[生成图 metadata](../diagrams/generated/metadata.json)；context 数据流来自[Harness IR](../hir.json)和下列 Evidence IDs。Evidence: `S-001`, `S-002`, `S-004`, `S-005`, `S-008`, `S-009`, `R-001`, `R-002`, `R-004`, `X-003`。

## Context 来源

| 来源 | 首次装载/刷新时机 | 信任与持久性 | 进入模型的精确方式 | 本轮动态覆盖 |
|---|---|---|---|---|
| 默认/自定义 system prompt | startup；model/resource refresh 后重建 | 配置/CLI 来源；不作为 session message entry | `buildSystemPrompt()` 形成每次 request 的 system instructions | 最小 system prompt 路径运行；未做 source diff |
| AGENTS.md / CLAUDE.md | startup/reload，可用 flag 禁用 | context file；**不受 project trust gate** | 包装为 `<project_instructions>` 并入 system prompt | 真实场景显式 `--no-context-files`，仅静态确认 |
| `.pi/SYSTEM.md` / append prompt | trusted project resources 加载或 reload | 未信任项目时不加载 | resource loader 合并到 system prompt | 真实场景禁用，未动态加载 |
| Skills metadata | resource load/reload | global/project skill；project 部分受 trust | 有 read tool 时在 system prompt 列出可用 skill | 真实场景禁用 |
| `/skill:name` full body | 用户显式调用时 lazy expansion | body 在调用 turn 进入 transcript | 展开成 user-side invocation text | 未运行 skill invocation |
| Active session branch | open/resume/branch/fork 后重建 | JSONL v3 durable parent chain | `buildSessionContext()` 选择 active path/messages/summary | R-003/004 验证跨进程恢复 |
| ToolResult | 每个 tool batch 完成后 | 作为 message entry 可被 session 保存 | 先追加 transcript，再经 transform/convert 进入下一 request | R-002 直接观察 `314159` 回填 |
| Extension message/system override | 每个 prompt 开始 | extension 与 host 同权限；是否 durable 取决于 message API | `before_agent_start` 可加 custom message 或替换本轮 system prompt | X-001 hooks；真实 extensions 禁用 |
| Context hook transform | **每次 provider request** | transient，默认不回写原 session tree | `transformContext` 后再 `convertToLlm` | X-001 覆盖 hook contract；未做真实 payload diff |

[C: C-003] 的置信度为 medium，因为本轮没有部署 request proxy 做全部 source 的差分；真实场景只验证了最小路径和 toolResult 回填。

## Durable memory

Pi 没有独立向量 memory 层。核心 durable memory 是 session tree：message、model/thinking change、custom entry、compaction、branch summary 等都在 JSONL 中；active branch 通过 parent chain 与 leaf 计算。workspace 文件是另一条独立持久层，不会自动与 session rollback 保持一致。[S: S-008]

## Compaction

Coding Agent 分两类：

- **Overflow**：错误或 usage 超过当前 model window；删除 live context 中的 error，生成 summary，最多 compact-and-retry 一次。
- **Threshold**：接近窗口时压缩，但不自动重新回答已完成的 assistant turn。

Compaction entry 保存 summary、`firstKeptEntryId`、`tokensBefore` 和 details；随后重建 active context。[S: S-009] [X: X-003]

新 `AgentHarness.compact()` 已有手动结构操作和 compaction helpers，但 auto-compaction decision 尚未实现。[D: D-008]

| 路径 | 触发条件 | 操作顺序 | 是否自动重答 | Durable 结果 | 未验证边界 |
|---|---|---|---|---|---|
| Overflow compaction | provider 报 context overflow，或 usage 超出当前 model window | 从 live context 移除 error -> 生成 summary -> 追加 compaction entry -> 重建 active context -> 最多 retry 一次 | 是，最多一次 compact-and-retry | error 仍可留在 session；summary/firstKept/tokens 写入 JSONL | 真实超长 SiFlow request 未运行 |
| Threshold compaction | token usage 接近阈值，但当前 assistant turn 已正常完成 | 计算 summary -> 追加 compaction entry -> 重建后续 context | 否，不重新回答已完成 turn | compaction 成为 active branch 的一等 entry | summary 信息损失未做质量评估 |
| Manual `AgentHarness.compact()` | host 显式调用 helper | 在 phase/save-point 约束下准备并提交结构变更 | 由 host 决定后续 prompt | helper/session tests 验证 ordering | auto decision、产品迁移和半持久恢复尚未实现 |
"""

REPORTS["05-models-tools-extensions.md"] = r"""# 05 模型、工具与扩展

![Tool and extension surface](../diagrams/generated/pi-extension-surface.png)

> 图 4（gpt-image-2 读者插图）：三列分别回答模型看到什么、能调用什么、action 如何运行；默认 host path 与可选 gate/container 明确分离。图像的 prompt、output hash 与语义审查见[生成图 metadata](../diagrams/generated/metadata.json)；三类控制点来自[Harness IR](../hir.json)和下列 Evidence IDs。Evidence: `D-002`, `D-004`, `D-007`, `S-001`, `S-002`, `S-003`, `S-007`, `S-015`, `S-017`, `R-002`。

## Model boundary

`pi-ai` 的运行时单位是 Provider：id/name/base URL、auth、model catalog、`stream` 和 `streamSimple`。`ModelsImpl` 在每次请求前解析 provider auth，合并 base URL/header/env，再把 model/context 分派给拥有该 model 的 provider。[S: S-012]

本轮用隔离 `models.json` 注册 `siflow/qwen3.6-35ba3b`：`--list-models` 成功，随后真实 text/read 场景都通过相同 provider abstraction。[R: R-005, R-001, R-002]

## Tool registry

`AgentSession._refreshToolRegistry()` 合并：

- built-in tool definitions；
- extension `registerTool()`；
- SDK custom tools；
- CLI/settings allowlist 与 denylist。

extension/custom tool 同名时按 load/order 进入最终 map；resource loader 会产生 conflict diagnostic，但机制仍允许扩展覆盖/替换能力。[S: S-003]

## 固定版本的内置工具清单

Pi `v0.80.7` 的 Coding Agent 内置 registry 明确定义 **7 个名称**：`read`、`bash`、`edit`、`write`、`grep`、`find`、`ls`。新 session 未传 `--tools`/`--no-tools` 时，默认 active set 只有前四个；后三个已注册但默认不发给模型，可通过 `--tools` 或 SDK 显式启用。[源码：registry](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/tools/index.ts#L83) [源码：默认 active set](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/sdk.ts#L245) [C: `C-004`]

| 工具 | Registry | 默认 active | 作用与关键边界 |
|---|---|---|---|
| `read` | 内置 | 默认启用（新 session） | 按 path 读取文本或图片；支持 offset/limit 和输出截断。它是观察工具，但仍以 Pi 进程的 filesystem 权限访问。 |
| `bash` | 内置 | 默认启用（新 session） | 在当前 cwd 启动 shell，默认继承进程环境；timeout 可选且无默认值，abort/timeout 尝试终止进程树。[C: `C-007`] |
| `edit` | 内置 | 默认启用（新 session） | 用精确 old/new text replacement 修改已有文件；通过 mutation queue 协调文件写操作。 |
| `write` | 内置 | 默认启用（新 session） | 创建或覆盖文件，并在需要时创建父目录；不是 append-only session write。 |
| `grep` | 内置 | 默认不启用（需显式选择） | 在文件内容中搜索 pattern，并执行匹配数/输出长度截断；适合显式 read-only tool set。 |
| `find` | 内置 | 默认不启用（需显式选择） | 按 glob/pattern 枚举匹配路径；结果受 cwd、ignore 和截断设置限制。 |
| `ls` | 内置 | 默认不启用（需显式选择） | 列出目录内容；同样只拥有启动 Pi 的 OS user 可访问范围。 |

这里的三层必须分开：**registry** 是 7 个可配置定义，**active tools** 是本轮放进 `agent.state.tools` 的子集，**extension/SDK tools** 是随后按 name 合并的外部定义。Extension 或 SDK 同名定义会覆盖最终 definition/registry entry，因此“`read` 在 registry 中”仍不能证明当前执行目标必然是原始 built-in。`--no-tools` 清空全部 active tools，`--no-builtin-tools` 只移除 built-ins，`--exclude-tools`/`--tools` 再提供显式过滤。

## Hook 注入点

| 注入点 | 发生时机 | 能改变什么 | 失败/阻断语义 | 权限边界 |
|---|---|---|---|---|
| `input` | 用户输入进入产品层时 | 标记 handled，或变换输入 | handled 可短路普通 prompt；错误由 extension runtime 报告 | host 进程内 |
| `before_agent_start` | 每次 prompt 调 low-level loop 前 | 加 custom messages，或替换本轮 system prompt | 可改变该 run 的初始 context | host 进程内 |
| `context` | 每次 provider request 前 | 变换将要发送的 messages | 影响 request，不必改写 durable session | host 进程内 |
| `tool_call` | 参数 validation 后、`execute` 前 | block 调用并返回理由 | 可阻止该 tool handler；不是不可绕过的全局 gate | host 进程内、可选 |
| `tool_result` | handler 返回后 | 改 content、details、`isError` | 模型下一 request 看到变换后的结果 | host 进程内 |
| provider hooks | request/payload/response 边界 | 观察或修改 provider 交互 | 可能改变兼容性、日志和 redaction | host 进程内 |
| session/tree hooks | switch/fork/compact/tree 操作前后 | 观察、阻止或附加生命周期行为 | 部分 post-commit failure 不能回滚已提交状态 | host 进程内 |

这些 hooks 是控制面，不是被隔离的 plugin VM；extension TypeScript 与主进程同权限。`tool_call` block 只覆盖经过该 registry/hook pipeline 的调用，extension 自己直接访问 filesystem/process/network 不受它约束。[D: D-002]

## 不内置的协议

核心明确不内置 MCP。要么把 CLI + README 暴露成 skill，要么 extension 自行注册 MCP tool。因而 HIR 中没有把 MCPServer 画成现存核心组件。[D: D-004]
"""

REPORTS["06-permissions-sandbox-workspace.md"] = r"""# 06 权限、Sandbox 与 Workspace

![Permission pipeline](../diagrams/generated/pi-permission-boundaries.png)

> 图 5（gpt-image-2 读者插图）：中心实线是默认 side-effect path；startup-only project trust、可选 extension gate、外部 container/VM 和 custom-tool host path 被空间分离，不能读成全局强制审批。图像的 prompt、output hash 与语义审查见[生成图 metadata](../diagrams/generated/metadata.json)；边界结论来自[Harness IR](../hir.json)和下列 Evidence IDs。Evidence: `D-002`, `D-004`, `D-007`, `S-003`, `S-006`, `S-007`, `S-017`, `R-002`, `X-001`。

## 三个容易混淆的边界

1. **Project trust**：启动资源加载 gate。它防止仓库在未确认时加载 `.pi/settings.json`、extensions、skills、SYSTEM 等。它不限制模型之后调用 read/bash/write。[C: C-006]
2. **Tool hook**：可选 application policy。extension 可在 `tool_call` 返回 block；`protected-paths.ts` 是示例，不是默认策略。[C: C-017]
3. **Sandbox**：OS/container/VM 边界。Pi 默认没有；需要 whole-process Docker/OpenShell，或用 Gondolin extension 路由 built-in tools。[C: C-005]

## 边界对照

| 边界 | 默认启用 | 保护对象 | 不保护/可绕行面 | 合理部署用途 |
|---|---|---|---|---|
| Project trust | interactive 有 prompt；headless `ask` 无既有决策时不加载项目资源 | `.pi/settings.json`、project extensions/skills/SYSTEM 等 startup resources | AGENTS/CLAUDE context；之后的 read/write/edit/bash；extension 直接副作用 | 防止打开未知仓库时静默装载可执行扩展和配置 |
| `tool_call` hook / protected paths extension | 默认关闭；需用户安装并配置 | 经过 tool registry 的命名调用和参数 | extension 直接 fs/process/network；`!` command；未被路由的 custom backend | 交互确认、路径规则、组织策略原型 |
| Gondolin tool routing example | 默认关闭；需安装并启用该 extension | 被该 extension 覆盖的 built-ins 与 `!` command | 未 delegate 的 arbitrary extension tools；host resource loader/package install | 把选定 tool backend 放入隔离 guest |
| Whole-process Docker/OpenShell/VM | 否，由部署层提供 | Pi、extensions、shell、language server 等整个进程树 | bind mount 仍可写 host；挂载 agent dir 会暴露 session/settings/auth | unattended/untrusted workload 的主要隔离层 |
| Host OS user/ACL | 是，取决于启动用户 | 用户权限不允许访问的资源 | 该用户本来可读写的 workspace、credentials、network | 所有模式的最终基础边界 |

## 默认 side-effect path

内置 bash 在 cwd 启动 shell，默认继承进程环境；timeout 参数可选且无默认值。Unix 使用 detached process group，abort/timeout 会 kill tree。extension 代码、package install、language server 与 shell 子进程都处于同一用户权限边界。[C: C-007]

## 外部隔离的绕行风险

Gondolin example 覆盖内置 tools 与 `!` command，但其他 custom extension tools 仍在 host，除非自己 delegate。Whole-process container 更完整，但 bind-mounted workspace 仍会写回 host；挂载 host agent dir 还会暴露 sessions/settings/auth。[D: D-007]

## 本轮没有做什么

没有触发 bash/write/edit，也没有声称验证了 deny 后“零副作用”。这是安全限制，不是系统具备 deny gate 的证据。要验证部署安全，需要在 disposable VM 中跑 tool/extension/`!`/subagent 的 side-effect matrix。
"""

REPORTS["07-subagents-delegation.md"] = r"""# 07 Subagent 与 Delegation

![Subagent topology](../diagrams/generated/pi-subagent-topology.png)

> 图 6（gpt-image-2 读者插图）：核心默认无 subagent；可选 subagent extension 与 experimental orchestrator 是两条不同条件路径。Child 隔离 context/process 但共享 cwd/workspace，orchestrator 不是 loop delegation。图像的 prompt、output hash 与语义审查见[生成图 metadata](../diagrams/generated/metadata.json)；topology 结论来自[Harness IR](../hir.json)和下列 Evidence IDs。Evidence: `D-004`, `D-006`, `D-010`, `S-015`, `S-016`。

## 默认核心

Coding Agent README 明确写出 “No sub-agents”。默认 tool registry 不会自动出现 delegation，也没有父子 context/session 协议。[C: C-013]

## 示例 extension

`examples/extensions/subagent` 注册一个 `subagent` tool：

- single、parallel（最多 8 task、并发 4）和 chain；
- 每个 child 为独立 `pi --mode json -p --no-session` 进程；
- system prompt 写入 mode `0600` 临时文件并 append；
- child 默认 cwd 与 parent 相同，可覆盖；
- 解析 child JSON events，聚合 usage/tool calls/final output；
- abort 先 SIGTERM，5 秒后尝试 SIGKILL；
- parallel 返回每 task 最多 50KB 到 parent context，完整值留在 details。

因此隔离的是 **context/process**，不是 workspace 或权限。child 默认继承进程环境，工具能力由 agent definition 的 model/tools 字段控制。[S: S-015]

| 属性 | Parent -> example child 的默认关系 | 可配置点 | 安全含义 |
|---|---|---|---|
| Process | 独立 `pi --mode json -p --no-session` 子进程 | agent definition 可改 model/tools/cwd | process crash/context 隔离；仍通常是同一 OS user |
| Context/history | child 新建 transcript，不继承 parent 全量 history | system prompt 临时文件、task/chain 前序输出显式传入 | parent 中间 history 不自动泄漏；传入文本仍可能含敏感信息 |
| Session | `--no-session`，child 不写普通 durable session | 示例实现固定 | child 结果靠 parent toolResult 回收；无法靠 child session resume |
| Cwd/workspace | 默认与 parent 相同 | agent definition 可覆盖 cwd | 并行 child 可竞争同一文件；context 隔离不等于 workspace 隔离 |
| Environment/credentials | 继承启动进程环境 | 需由容器或 spawn env 显式收窄 | child 可能拥有与 parent 相同 provider key 和主机能力 |
| Tool surface | agent definition 的 `tools` allowlist | 每个 agent 可不同 | 限制模型可调用的命名工具，但不构成 OS sandbox |
| Concurrency | parallel 最多 8 tasks、并发 4 | 示例常量/模式 | 控制资源量，不解决共享文件冲突 |
| Cancellation | abort -> SIGTERM；5 秒后尝试 SIGKILL | 固定示例行为 | 可清理进程树，但未证明所有 child 副作用可回滚 |
| Return to parent | final/tool usage/details；parallel 每 task context 最多 50KB | 完整结果保留在 details | 控制 parent context 体积，不等于 durable artifact store |

Project-local agent prompt 是 repo-controlled；interactive mode 可确认，但 headless 退化路径本轮未验证。

## Experimental orchestrator

`OrchestratorSupervisor` 创建一个 RPC Pi child per instance，复用 events/UI request，持久化 instance/session metadata，并在意外退出时标 error/清理 Radius presence。restart recovery 只是把原 online/starting 记录标 stopped，没有恢复 in-flight child。[C: C-018]

它更像 multi-session process supervisor，不是 agent loop 中的 parent/child delegation primitive。
"""

REPORTS["08-sessions-persistence-recovery.md"] = r"""# 08 Session、持久化与恢复

![Persistence lifecycle](../diagrams/generated/pi-persistence-lifecycle.png)

> 图 7（gpt-image-2 读者插图）：主轴展示 live branch 的 append、JSONL persistence、resume 和 context rebuild；compaction 是条件路径，workspace 明确不随 session branch 回滚。图像的 prompt、output hash 与语义审查见[生成图 metadata](../diagrams/generated/metadata.json)；持久化关系来自[Harness IR](../hir.json)和下列 Evidence IDs。`R-SCENARIO-003/004` 观察到 create/persist/restore；compaction/retry 来自定向 tests。Evidence: `S-008`, `S-009`, `S-010`, `S-014`, `R-003`, `R-004`, `X-003`。

## JSONL v3

首行是 session header：version、session id、timestamp、cwd、可选 parentSession。后续每个 entry 有短 id、parentId、timestamp；append 作为 current leaf 的 child 并推进 leaf。类型包括 message、model/thinking/tool changes、custom、compaction、branch summary、label、session info 等。[S: S-008]

读取时 Pi 流式解析 JSONL，单个 malformed line 会被跳过；非空文件如果最终没有合法 Pi header 则拒绝打开。v1/v2 会迁移到 v3并重写文件。中间 entry 损坏是否造成可接受但错误的 branch 仍是开放风险。

| 状态 | Live owner | Durable 表示 | Resume/fork 行为 | 不随 session 恢复的内容 |
|---|---|---|---|---|
| Active conversation branch | `AgentSession` + `SessionManager` current leaf | JSONL entry 的 `id/parentId` tree 与 leaf | resume 选择 active leaf；branch navigation/fork 选择或复制 path | workspace 文件、外部进程、网络服务状态 |
| Model/thinking choice | session runtime | model/thinking change entries | `buildSessionContext()` 重放到 active path 的有效配置 | provider 端连接/stream |
| Message/tool transcript | low-level Agent context | message entries，包括 assistant toolUse 与 toolResult | 重建为下一 request 的 carry-forward context | tool 已造成的副作用不会重放或撤销 |
| Compaction | Coding Agent orchestration | summary、`firstKeptEntryId`、`tokensBefore`、details | active context 用 summary + kept suffix 重建 | 被 summary 丢失的细节不能从有效 context 自动恢复 |
| Retry/error | `AgentSession` recovery state | provider error 可留 session；live context 可移除 | reopen 可看到 durable entry，但不会恢复中断的 provider stream | backoff timer、in-flight HTTP stream |
| Workspace | OS/filesystem | Pi session 外部的目录现实状态 | resume/fork 继续看到当前磁盘 | 没有 conversation leaf 对应的自动 snapshot/rollback |

## Resume 与 fork

- Resume/open：加载 entries、迁移、重建 index/leaf，再 `buildSessionContext()`。
- Branch navigation：移动 leaf，可对离开的 branch 生成 summary。
- Fork：新 header 指向 `parentSession`，复制 selected history 或 active path，并为目标 cwd 重建 runtime services。

## 跨进程实验

进程 A 使用 `session-id=analysis-resume-001` 收到“记住 `PI_RESUME_2718`”，返回 ACK 并退出。进程 B 只要求返回前一进程 token，成功返回 `PI_RESUME_2718`。raw session copy 位于 `traces/raw/R-004-session-state.jsonl`，normalized traces 不含 prompt/thinking。[R: R-003, R-004]

## Recovery 分层

- provider retryable error：指数退避、maxRetries 有界；error 留 durable session，从 live context 移除。
- context overflow：compaction path，不进入普通 retry；最多一次 compact-and-retry。
- length-truncated tool call：不执行，返回错误让模型重发。
- abort：low-level signal 传入 model/tool；Coding Agent 还负责清理 tracked detached children。
- 新 AgentHarness：半持久恢复尚在设计；provider stream 不可恢复，unfinished tool 是否可重试需要 idempotency 声明。[C: C-020]
"""

REPORTS["09-observability.md"] = r"""# 09 可观测性

## 已实现

Agent event vocabulary 包含：

- `agent_start`, `agent_end`, `agent_settled`；
- `turn_start`, `turn_end`；
- `message_start/update/end`；
- `tool_execution_start/update/end`；
- `queue_update`；
- `compaction_start/end`；
- `auto_retry_start/end`。

JSON mode 把 header + events 写到 stdout；RPC 在 command response 之外转发同一事件，并提供 extension UI request/response。[D: D-005] [R: R-001, R-002]

| 表面 | 面向谁 | 关联键/顺序 | 包含内容 | 缺口与敏感性 |
|---|---|---|---|---|
| In-process agent events | `AgentSession`、extensions、UI adapter | 单次 runtime 的 event sequence、message/tool 对象 | run/turn/message/tool/queue/compaction/retry/settled lifecycle | 默认没有全局 trace/span parent；payload 可含 prompt/tool data |
| JSON mode stdout | 自动化消费者、分析脚本 | header + 发出顺序 | 同一 session events 的结构化序列 | 原始输出含 assistant thinking、args/results；需要 redaction |
| RPC stream | 外部 host/UI | command response id + 并行 agent events | session control、events、extension UI request/response | command 与 event 因果关系需 host 自行维护 |
| JSONL session | resume/branch/fork | entry `id/parentId`、timestamp、file order | durable message/config/compaction/tree state | 不是低开销 telemetry；不包含完整内部 timing/span |
| OTel/Sentry adapter notes | 未来外部 adapter | 设计目标是 stable vendor-neutral event mapping | 文档化方向，不是默认 exporter | 本版本不能声明 collector delivery 或 trace propagation |
| 本分析 normalized trace | 复核者 | scenario id + sequence | role/type/length/model/usage/stop/tool lifecycle | 是分析产物，不是 Pi 产品 API；主动删除文本、thinking、args/results |

`R-SCENARIO-002` 归一化后可重建：

```text
session
  -> run.started
  -> turn.started
  -> user message
  -> assistant toolUse
  -> tool.started(read)
  -> tool.completed(read)
  -> toolResult
  -> turn.completed
  -> turn.started
  -> assistant stop
  -> run.completed
  -> run.settled
```

## 未实现为默认核心的部分

当前 event 没有统一 `traceId/spanId/parentSpanId`，也没有默认 OTel exporter。`packages/agent/docs/observability.md` 是 design notes：目标是 Pi 自己产 stable vendor-neutral events，外部 adapter 再映射到 OTel/Sentry。[D: D-009]

因此本分析通过 scenario id + sequence 做归一化 correlation，而没有把 JSON events 宣称成完整 distributed trace。[C: C-014]

## 数据敏感性

原始 JSON mode 会包含 prompt、assistant text/thinking、tool args/result。报告使用的 normalized trace 只保留角色、内容类型/长度、provider/model、usage、stop reason、tool name 与 lifecycle。生产接入应默认执行同类 redaction。
"""

REPORTS["10-design-decisions.md"] = r"""# 10 设计决策与权衡

本节把“实现了什么”和“作者为什么这样做”分开。文档明确的产品立场使用 D evidence；源码可见机制使用 S evidence；右侧收益和代价是根据边界与实验形成的分析综合，不自动等价于作者动机。

![Pi design space](../diagrams/generated/pi-design-space.png)

> 图 8（gpt-image-2 读者插图）：四行分别从 documented stance 映射到 recovered mechanism，再以橙色点线连接 analyst-synthesized tradeoff；右列不表示作者声明。图像 provenance 与语义审查见[生成图 metadata](../diagrams/generated/metadata.json)；设计映射来自[story spec](../diagrams/story-specs.json)和下列 Evidence IDs。Evidence: D-001, D-002, D-003, D-004, D-007, D-008, S-001, S-003, S-007, S-008, S-011, S-017, R-004, X-002。

## 决策记录

| 决策 | 当前机制 | 适用条件 | Documented intent | 收益 | 代价/风险 | Evidence / 置信度 | 最小反证 |
|---|---|---|---|---|---|---|---|
| 薄 low-level loop | `runAgentLoop` + callbacks | 所有使用 agent-core contract 的 host | agent-core 通用 runtime | 易嵌入、可用 faux provider 精确测试 | 产品 retry/session/settled 落到上层，形成两代 orchestration | `S-001`, `D-003`；高 | 找到产品主路径绕过它的独立 model/tool loop |
| 工具默认并行 | batch 并发；任一 sequential tool 使整批串行 | 同一 assistant message 的 toolUse batch | 文档/源码明确 | 降低互不依赖工具的 latency | completion event 与 transcript 顺序不同，错误分类会改变整批吞吐 | `S-001`, `X-001`；高 | 并发测试中 toolResults 按完成顺序而非原 call 顺序进入 context |
| 扩展优先而非内置工作流 | extensions/skills/packages + hooks | Coding Agent resource loader 启用相应资源时 | README 明确 aggressively extensible | core 小、用户可定制 MCP/subagent/policy | 行为和治理不统一；extension 与 host 同权限 | `D-004`, `S-003`；高 | 默认 registry 强制提供统一 MCP/subagent/policy contract |
| 无内置 sandbox/permission popup | 进程权限 + 外部隔离 | 默认 built-ins 与 extension runtime | security 文档明确 intentional | 直接使用本地 toolchain，不制造虚假边界 | unattended/untrusted 任务必须由部署层治理 | `D-002`, `D-007`；高 | 默认配置存在覆盖所有副作用 backend 的不可绕过 gate |
| Project trust 只守启动资源 | path-based persisted decision | project-local settings/extensions/skills/SYSTEM | security 文档明确 | 防止 repo 静默加载可执行扩展/配置 | AGENTS context 仍可注入 prompt；运行期 tools 不受限 | `D-002`, `S-006`；高 | 未信任项目时 read/bash 被 runtime policy 自动阻止 |
| Session 用 append-only tree | JSONL `id/parentId/leaf` | persistent session，非 `--no-session` | session 文档和实现 | branch/fork/compaction 保留历史 | workspace 不随 branch 回滚；中段损坏可造成错误 branch | `S-008`, `R-004`；高 | resume 不依赖 tree/leaf，或 fork 自动恢复旧文件状态 |
| Compaction 是一等 entry | summary + first kept + token metadata | Coding Agent overflow/threshold path | 机制明确；作者选择理由未单独记录 | 可重建 active context并保留压缩事件 | summary 有信息损失，增加模型调用和失败面 | `S-009`, `X-003`；高 | compact 后没有 durable entry 或 context 不经 summary 重建 |
| 新 Harness 用 snapshot/save point | in-flight immutable；next safe point refresh | 迁移中的 generic `AgentHarness`，非当前 Coding Agent 默认 | lifecycle 文档明确 | 热更新不污染当前 request，持久顺序明确 | phase/reentrancy/settled/auto recovery 仍在硬化 | `D-003`, `S-011`, `X-002`；中 | 当前 request 中途读到 next-state 配置，或 pending write 越过 save point |
| Provider owns auth + stream | `Models` runtime collection | 注册 provider/model 与 custom endpoint | 源码 contract | 多 provider 共用 loop | “compatible” endpoint 的 body/stream 方言仍泄漏，如 thinking flag | `S-012`, `R-005`；高 | provider 选择/auth 在 loop 内按 provider id 硬编码 |
| Event-first observability | structured lifecycle events | JSON/RPC/in-process consumers | design notes 明确不绑定 vendor | UI/host 易消费，可由 adapter 映射 | 缺默认 trace/span correlation、redaction 和 exporter | `D-005`, `D-009`；中 | 本版本默认发出完整 OTel spans 并传播 parent context |

## 跨决策张力

### 通用核心与产品一致性

薄 loop 让 agent-core 易嵌入，但 compaction、retry、session ordering 和 settled semantics 必须由上层拥有。新 AgentHarness 的出现说明可复用性问题已经从“能否调用 loop”转成“不同 orchestration 是否行为等价”。最有区分度的下一步不是更多单元测试，而是 AgentSession 与 AgentHarness 的 differential scenario suite。[C: C-010, C-016]

### 扩展自由与统一治理

registry/hooks 能把 subagent、MCP、permission UI 和自定义工具留给用户，但同样意味着不存在一个不可绕过的 application-level policy plane。若部署目标从本地交互式工具转向 unattended service，合理替代不是再加一个示例 hook，而是 whole-process isolation 或可证明覆盖所有 side-effect backend 的统一 capability boundary。[C: C-005, C-017]

### 可审计 session 与不可回滚 workspace

JSONL tree 完整保存 branch、compaction 和 resume 历史，却不为文件系统提供相同事务语义。用户可以回到旧 conversation leaf，但 workspace 仍是新状态。这不是 session bug，而是两个 durable subsystem 没有共同 checkpoint protocol 的结构性结果。[C: C-008, C-012]

没有文档化的作者动机不在表中伪装成事实。例如“为什么 JSONL 而非数据库”未找到直接说明，报告只陈述可观察 tradeoff。
"""

REPORTS["11-runtime-experiments.md"] = r"""# 11 运行实验

完整命令和结果见 [runtime-tests.md](../runtime-tests.md)，场景机器可读记录见 [catalog.json](../scenarios/catalog.json)。

| 场景组 | 执行对象 | 预声明断言 | 结果 | 主要 artifact | 解释边界 |
|---|---|---|---|---|---|
| R-001 | 真实 SiFlow text-only | 1 turn、0 tool、最终 settled | 通过，`PI_TEXT_OK` | `traces/normalized/R-001-text-only.normalized.jsonl` | 仅最短 JSON-mode 路径 |
| R-002 | 真实 SiFlow + read fixture | 必须先 toolUse，再带 toolResult 二次请求 | 通过，2 turns、1 tool、`314159` | `traces/normalized/R-002-read-tool.normalized.jsonl` | 只读；未覆盖 permission/sandbox |
| R-003/004 | 两个独立 Pi 进程 | 第二次 prompt 不重发 token仍可恢复 | 通过，`PI_RESUME_2718` | `traces/raw/R-004-session-state.jsonl` + normalized traces | 正常 JSONL 尾部；无 corruption |
| X-001 | agent-core faux provider | loop、双顺序、hooks、queue、length-stop contract | 39/39 passed | 固定 test files 见 `X-001` | 不评价真实模型行为 |
| X-002 | 新 `AgentHarness` | snapshot/save point、pending writes、helpers | 61/61 passed | 固定 test files 见 `X-002` | 不代表 Coding Agent 已迁移 |
| X-003 | Coding Agent recovery | compaction/retry/context rebuild 分层 | 31/31 passed | 固定 test files 见 `X-003` | 未注入 OS crash/真实长上下文 |

## R-SCENARIO-001：最短文本路径

- 配置：JSON mode、no session、no tools、禁 extensions/skills/templates/context files。
- 预期：一次 turn，无 tool event，最终 settled。
- 结果：通过，最终 `PI_TEXT_OK`；1 turn、0 tool。
- 证据：`R-001`；normalized trace `traces/normalized/R-001-text-only.normalized.jsonl`。

## R-SCENARIO-002：真实 read tool loop

- Fixture：`fixture.txt` 含合成未知值 `PI_FIXTURE_VALUE=314159`。
- 配置：只开放 `read`。
- 预期：模型必须 toolUse，result 回填后再次调用模型。
- 结果：通过；2 turn、1 tool start/end、最终 `314159`。
- 证据：`R-002`。

## R-SCENARIO-003/004：跨进程 resume

- 进程 A：持久 session `analysis-resume-001`，记忆合成 token。
- 进程 B：相同 session-id，不在 prompt 重复 token。
- 结果：A 返回 ACK，B 返回 `PI_RESUME_2718`。
- 证据：`R-003`, `R-004`。

## X-SCENARIO-001：agent-core faux provider

- Files：`agent-loop.test.ts`, `agent.test.ts`。
- 结果：2 files，39 tests passed。
- 覆盖：parallel/sequential、hooks、queue、termination、length stop、event settlement。

## X-SCENARIO-002：新 AgentHarness

- Files：`agent-harness.test.ts`, `session.test.ts`, `compaction.test.ts`。
- 结果：3 files，61 tests passed。
- 覆盖：save point refresh、pending write ordering、hooks、abort、session/compaction helpers。

## X-SCENARIO-003：Coding Agent recovery

- Files：`agent-session-compaction.test.ts`, network retry regression, session build-context。
- 结果：3 files，31 tests passed。
- 覆盖：overflow/threshold compaction、bounded retry、active context rebuild。

## 意外观察

自定义 model 声明 `reasoning:false` 且 `supportsReasoningEffort:false`，但 SiFlow 服务端仍流出 thinking block。此前直接 endpoint smoke test 通过 `chat_template_kwargs.enable_thinking=false` 可关闭；Pi 的 standard models.json path 本轮没有注入该 request body。该差异不否定 harness loop，但 raw trace 可能包含 reasoning，已在 normalized trace 中移除。
"""

REPORTS["12-failure-modes-open-questions.md"] = r"""# 12 失败模式与开放问题

## 已验证或源码明确的 failure path

| 失败/触发 | 当前行为 | 状态影响范围 | 可恢复条件 | 尚未验证的边界 | Evidence |
|---|---|---|---|---|---|
| Provider retryable error | 指数退避，`maxRetries` 有界；live context 移除 error，session 保留 entry | 当前 provider request/产品 prompt | 后续 retry 成功或用户再次 prompt | 真实断网、rate-limit header、进程重启时 budget 是否保留 | `S-010`, `X-003` |
| Context overflow | 生成 compaction；错误型 overflow 最多自动 retry 一次 | active context 与当前 prompt | summary 成功且 compact 后 request 可接受 | 真实长上下文、summary provider 失败、连续 model window 变化 | `S-009`, `X-003` |
| Length-truncated tool call | 全部拒绝执行，为每个 call 生成 error result | 当前 tool batch | 模型下一 turn 重发完整参数 | 部分工具已先产生 delta 时是否有额外 side effect surface | `S-001`, `X-001` |
| Tool exception | 转为 `isError` toolResult 并进入模型 context | 单个 call；batch 继续按 contract 汇总 | 模型可根据 error 自我修复 | extension 在抛错前已产生的主机副作用不能自动回滚 | `S-001`, `X-001` |
| Bash timeout/abort | kill detached process group/tree；保留输出和状态 | shell process tree | handler 返回后 session 可继续 | orphan/grandchild、不可中断 I/O、Windows 行为 | `S-007` |
| Session file 非空但无合法 header | 拒绝打开 | 整个 session file | 需人工修复/恢复合法 header | 中段 malformed line 被跳过后 branch 是否静默错误 | `S-008` |
| New AgentHarness hook failure | 归一化 `AgentHarnessError`；部分 post-commit failure 不回滚 | 当前 phase/save point | host 根据错误和 committed state 决定继续 | reentrancy、settled 与半持久 turn 仍 provisional | `D-003`, `S-011` |
| Orchestrator child exit | instance 标 error、reject pending、清理 resources | 单个 RPC Pi instance | supervisor 可新建/重启实例 | in-flight task、session 与外部副作用不能恢复 | `S-016` |

## 产品风险，不是分析器缺陷

- 默认无 permission/sandbox，对 untrusted/unattended workload 风险高。
- AGENTS/CLAUDE context 不受 project trust gate，prompt injection 是明确接受的本地 agent 风险。
- optional tool-routing sandbox 不自动覆盖 arbitrary extension tools。
- session branch 与 workspace filesystem 没有事务性一致性。
- subagent child 默认共享 cwd 与环境，context 隔离不等于 capability 隔离。

## 分析限制

- 未运行 write/edit/bash、Gondolin、Docker、OpenShell、subagent extension、orchestrator。
- 未做 corrupted session、SIGINT、tool timeout、child crash、long-context real model。
- 未获得 production feature flags、使用频率或 maintainer 访谈。
- 新 AgentHarness lifecycle 文档自己标记 phase/settled/reentrancy 仍 provisional。

## 优先实验

| 优先级 | 实验 | 要区分的假设 | 通过标准 | 仍不能推出 |
|---|---|---|---|---|
| P0 | `AgentSession` vs `AgentHarness` differential suite | 共享 low-level loop 是否足以保证产品行为等价 | 相同 scripted turns 对齐 messages、events、retry、compaction、writes 与 settled；差异有明确 contract | 单元场景一致不代表迁移已完成 |
| P0 | Container/VM permission bypass matrix | 可选 gate/路由是否覆盖所有副作用 backend | built-in、`!`、custom tool、extension direct process、subagent 分别记录 host/guest 文件、进程、网络副作用 | 单一 container 配置不代表所有 bind mount/credential 策略 |
| P1 | JSONL corruption matrix | parser 宽容跳行是否可能形成静默错误 branch | header/middle/tail/parent/compaction/leaf 注入后明确分类拒绝、修复或降级 | conversation 恢复不证明 workspace 一致 |
| P1 | Provider proxy context differential | 九类 context source 的装载和 request 时机是否符合静态结论 | 每次 request 保存 redacted type/hash diff，并对 trust/reload/hook 条件逐项开关 | 一个 provider 方言不覆盖其他 adapter |
| P2 | Orchestrator restart/crash | supervisor cleanup 与 durable session 能否恢复 in-flight child | crash 前后 instance/session/pending request/resource 状态可重放并有明确 terminal result | orchestrator 结果不能外推到 subagent extension |

机器可读问题清单见 [questions.json](../questions.json)。
"""

REPORTS["13-coverage-reproducibility.md"] = r"""# 13 覆盖与复现

## 产物

- 固定配置：[manifest.json](../manifest.json)
- 仓库 inventory：[inventory.json](../inventory.json)
- HIR：[hir.json](../hir.json)
- Claims：[claims.jsonl](../evidence/claims.jsonl)
- Evidence：[observations.jsonl](../evidence/observations.jsonl)
- Coverage：[coverage.json](../evidence/coverage.json)
- Scenarios：[catalog.json](../scenarios/catalog.json)
- Raw traces：`traces/raw/`
- Redacted normalized traces：`traces/normalized/`
- Diagram source models/metadata：`diagrams/`
- Narrative story spec：[story-specs.json](../diagrams/story-specs.json)
- Reader PNG/prompt/review metadata：`diagrams/generated/`

## 结构化规模

当前 bundle 包含 **29 个 HIR nodes、35 条 typed edges、20 个 supported claims 和 35 条 D/S/R/X evidence records**。这些计数描述可审计产物规模，不代表源码覆盖百分比或生产路径频率。

## 14 模块覆盖矩阵

`analyzed` 表示固定版本主机制和关键条件已静态恢复；`partial` 表示仍缺少会改变结论边界的平台、feature、真实 side effect 或故障注入。状态不是“读了多少行代码”。

| 模块 | 状态 | 已恢复机制 | 动态边界 | 未解决问题 |
|---|---|---|---|---|
| `compaction` | analyzed | overflow、threshold 与 AgentHarness manual compaction helper | 31 Coding Agent tests + AgentHarness helper tests；无真实长上下文 | 未用真实模型触发 262K 上下文 overflow。 |
| `context_assembly` | partial（关键运行或故障路径尚缺动态覆盖） | system/resources/session/toolResult/extensions/hooks 到 per-request context | 动态验证最小 prompt、toolResult、resume；资源/trust/hook payload 差分未跑 | 未代理捕获完整 provider request；未动态差分 skills/context files/extensions。 |
| `core_loop` | analyzed | runAgentLoop 的 provider/tool/steering/follow-up/stop 双层循环 | R-001/002 + 39 tests 覆盖 stop、tool feedback、queue、双顺序 | 无额外模块级未知项；仍受全局运行配置限制 |
| `interfaces` | analyzed | CLI interactive/print/JSON/RPC 收敛到 cwd-bound AgentSession runtime | 真实运行 JSON mode；TUI/RPC 仅静态检查 | 无额外模块级未知项；仍受全局运行配置限制 |
| `model_abstraction` | analyzed | pi-ai provider/model/auth/base URL/stream runtime contract | SiFlow model discovery/text/read 成功；未比较其他 provider | SiFlow 服务端默认 thinking 与 Pi reasoning=false 存在兼容差异。 |
| `observability` | partial（关键运行或故障路径尚缺动态覆盖） | agent events、JSON/RPC stream、session JSONL 与 adapter design notes | R-001/002 JSON events 可重建；无默认 OTel exporter | 默认没有 trace/span correlation IDs；OTel adapter 设计未实现。 |
| `orchestration` | analyzed | 当前 AgentSession 产品编排与迁移中 AgentHarness snapshot/save point | 当前 AgentSession 真实运行；AgentHarness 61 tests，未做差分迁移 | Coding Agent 迁移到新 AgentHarness 尚未完成。 |
| `permissions_safety` | analyzed | project trust、可选 tool gate、protected paths 与默认进程权限 | 只验证 trust/resource source；未运行 deny 或副作用工具 | 未执行破坏性 allow/deny side-effect 场景；结论主要来自明确文档与源码。 |
| `recovery` | analyzed | retry、overflow、truncated call、abort、hook/orchestrator failures | 定向 tests 覆盖逻辑分支；无 SIGINT、timeout、crash、半持久 turn | 未执行真实 SIGINT、tool timeout、进程 crash 或半持久 turn recovery。 |
| `sandbox_execution` | partial（关键运行或故障路径尚缺动态覆盖） | Gondolin selective routing 与 whole-process Docker/OpenShell/VM 边界 | Gondolin/Docker/OpenShell/VM 均未动态执行 | Gondolin 要求 Node >=23.6 与 QEMU，本轮 Node 22.19 环境未运行；Docker/OpenShell 未运行。 |
| `sessions_persistence` | analyzed | JSONL v3 parent tree、leaf、branch/fork/resume/migration | R-003/004 验证正常跨进程恢复；无 corruption/fork 动态矩阵 | 未做 corrupted JSONL 注入与跨版本 migration 动态测试。 |
| `subagents` | partial（关键运行或故障路径尚缺动态覆盖） | 默认无 subagent、示例 extension 子进程、experimental orchestrator | 示例和 orchestrator 仅源码；未创建 child | 核心无内置 subagent；可选 extension 与 experimental orchestrator 均未动态运行。 |
| `tools_extensions` | analyzed | built-in/custom/extension registry 与 input/context/tool/provider/session hooks | hooks/registry 有定向 tests；真实 runs 禁用 extensions | 未动态运行自定义 extension tool。 |
| `workspace` | analyzed | cwd、host filesystem、session branch 与共享 subagent workspace | 合成 read workspace 与 session resume；未测写入、branch drift、冲突 | 只验证只读 workspace；写/edit/bash 未动态执行。 |

## 关键复现命令

```bash
# 归一化 synthetic traces
python3 reproduce/normalize_pi_trace.py   traces/raw/R-002-read-tool.jsonl   traces/normalized/R-002-read-tool.normalized.jsonl   --scenario-id R-SCENARIO-002

# 重建 structured evidence/HIR
python3 reproduce/compile_analysis.py

# 严格校验
python3 ../../harness-analysis-skill/scripts/validate_analysis.py . --strict

# gpt-image-2 prompts 和发布图位于 diagrams/generated/；metadata 固定 prompt/output hash

# 重写报告
python3 reproduce/compile_report.py

# 检查 Markdown links、8 张正文 PNG、hash 与 semantic review metadata
python3 ../../harness-analysis-skill/scripts/audit_outputs.py . --strict
```

## 验证结果

- Analysis validator：`0 errors, 0 warnings`
- PNG decode/hash：8/8 reader figures valid
- Output audit：Markdown links、8 张 report-facing PNG、prompt/output hash 与 semantic review metadata 通过 strict
- Diagram density：overview 16 nodes；turn 11；context 9；permission 11；subagent 10；persistence 7
- Narrative density：system 12 nodes；observed turn 12；context 8；extension 11；design space 12
- Tests：39 + 61 + 31 = 131 passed
- Target `git status --short`：clean（依赖目录被 gitignore，不改变固定源码）

## Coverage statement

源码 inventory 共 1021 files，未达到 file/size scan limit。14 模块均有记录；partial 模块与 unresolved 条目不会被“未发现”等价成“不存在”。Runtime coverage 只代表 Linux/Node/JSON-mode/SiFlow 与命名 faux-provider tests。
"""

REPORTS["14-source-claim-index.md"] = r"""# 源码与 Claim 索引

本页把 20 条 supported claims 映射到固定 commit 的源码/文档锚点和命名运行场景。`S/D` 表示静态或文档约束，`R/X` 表示指定配置中的运行观察；两者都不表示生产频率。

| Claim | 可证伪结论 | 固定源码/文档锚点 | 动态证据 | Scope / 置信度 | 反证实验 |
|---|---|---|---|---|---|
| `C-001` | Pi 的产品入口由同一 Coding Agent runtime 支撑交互式 TUI、print/JSON 与 RPC 模式，底层能力拆分为 ai、agent、coding-agent、tui 等包。 | [D-001: README.md:13-33](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/README.md#L13)<br>[S-012: packages/ai/src/models.ts:24-369](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/ai/src/models.ts#L24)<br>[S-013: packages/coding-agent/src/main.ts:650-857](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/main.ts#L650)<br>[S-014: packages/coding-agent/src/core/agent-session-runtime.ts:67-353](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session-runtime.ts#L67) | 未做专项动态验证；当前由固定源码/文档支持 | v0.80.7 monorepo and CLI; `high`; `supported` | 从任一模式入口追踪到不同的核心循环实现；本轮源码检查和 JSON 模式运行均未发现。 |
| `C-002` | 通用 runAgentLoop 是 Pi 的核心模型-工具循环：模型响应后执行工具、追加 toolResult，再决定继续、注入 steering/follow-up 或退出。 | [S-001: packages/agent/src/agent-loop.ts:95-755](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/src/agent-loop.ts#L95) | `R-001`: [traces/normalized/R-001-text-only.normalized.jsonl](../traces/normalized/R-001-text-only.normalized.jsonl)<br>`R-002`: [traces/normalized/R-002-read-tool.normalized.jsonl](../traces/normalized/R-002-read-tool.normalized.jsonl)<br>`X-001`: [runtime-tests.md](../runtime-tests.md) | agent-core low-level loop; `high`; `supported` | 构造一次 toolUse 响应并检查是否不经过 runAgentLoop 的工具回填路径；真实轨迹与 faux-provider 测试均支持该循环。 |
| `C-003` | Coding Agent 的模型上下文由持久化分支消息、system prompt、项目指令、skills、工具清单及 extension hook 注入共同形成，并在模型边界前转换。 | [S-002: packages/coding-agent/src/core/agent-session.ts:1023-1223](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L1023)<br>[S-004: packages/coding-agent/src/core/system-prompt.ts:27-161](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/system-prompt.ts#L27)<br>[S-005: packages/coding-agent/src/core/resource-loader.ts:330-413](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/resource-loader.ts#L330) | `R-001`: [traces/normalized/R-001-text-only.normalized.jsonl](../traces/normalized/R-001-text-only.normalized.jsonl) | coding-agent default runtime; `medium`; `supported` | 分别禁用 context files、skills、extensions 并比较 provider request；本轮禁用配置验证了最小上下文路径，完整差分仍未执行。 |
| `C-004` | 内置、扩展与 SDK 工具被合并为运行时 registry；tool_call/tool_result hooks 位于实际 execute 前后，可阻断或改写结果。 | [S-003: packages/coding-agent/src/core/agent-session.ts:415-493](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L415)<br>[S-017: packages/coding-agent/examples/extensions/protected-paths.ts:1-29](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/examples/extensions/protected-paths.ts#L1) | `R-002`: [traces/normalized/R-002-read-tool.normalized.jsonl](../traces/normalized/R-002-read-tool.normalized.jsonl)<br>`X-001`: [runtime-tests.md](../runtime-tests.md) | coding-agent tool system; `high`; `supported` | 注册同名工具或让 hook 返回 block=false/true，检查最终执行目标和副作用；定向测试覆盖了 hook 与排序语义。 |
| `C-005` | Pi 没有默认的逐工具权限审批管线；permission popup 与路径保护属于可选 extension，默认工具直接以进程权限执行。 | [D-002: packages/coding-agent/docs/security.md:3-41](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/docs/security.md#L3)<br>[D-004: packages/coding-agent/README.md:489-503](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/README.md#L489)<br>[S-003: packages/coding-agent/src/core/agent-session.ts:415-493](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L415)<br>[S-017: packages/coding-agent/examples/extensions/protected-paths.ts:1-29](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/examples/extensions/protected-paths.ts#L1) | 未做专项动态验证；当前由固定源码/文档支持 | default coding-agent configuration; `high`; `supported` | 在无 extensions 的默认 CLI 中触发 bash/write 并寻找强制 ask/allow/deny 决策；源码未发现，官方文档明确否定。 |
| `C-006` | Project trust 只控制项目 settings/resources/extensions 的加载，不是工具权限或执行 sandbox；非交互模式无 UI 时默认 ask 会落到不信任。 | [D-002: packages/coding-agent/docs/security.md:3-41](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/docs/security.md#L3)<br>[S-005: packages/coding-agent/src/core/resource-loader.ts:330-413](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/resource-loader.ts#L330)<br>[S-006: packages/coding-agent/src/core/project-trust.ts:46-95](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/project-trust.ts#L46) | 未做专项动态验证；当前由固定源码/文档支持 | project resource bootstrap; `high`; `supported` | 在未信任项目放置 extension 与 AGENTS.md，验证 extension 被跳过而 context file 仍可加载；本轮以源码和文档确证，未执行含恶意资源的动态场景。 |
| `C-007` | 默认 bash backend 在当前 cwd 以继承环境启动本地 shell；timeout 是可选且无默认值，abort/timeout 会终止进程树。 | [D-002: packages/coding-agent/docs/security.md:3-41](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/docs/security.md#L3)<br>[D-007: packages/coding-agent/docs/containerization.md:3-43](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/docs/containerization.md#L3)<br>[S-007: packages/coding-agent/src/core/tools/bash.ts:27-148](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/tools/bash.ts#L27) | 未做专项动态验证；当前由固定源码/文档支持 | built-in bash tool; `high`; `supported` | 运行无 timeout 的长命令并观察是否存在隐藏上限，再发送 abort 检查子进程树；本轮因安全边界未执行 shell 动态场景。 |
| `C-008` | Coding Agent session 是版本化 append-only JSONL 树，id/parentId 与 leaf 表示分支；恢复时重建 compaction-aware active context。 | [S-008: packages/coding-agent/src/core/session-manager.ts:457-1540](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/session-manager.ts#L457)<br>[S-014: packages/coding-agent/src/core/agent-session-runtime.ts:67-353](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session-runtime.ts#L67) | `R-003`: [traces/normalized/R-003-session-create.normalized.jsonl](../traces/normalized/R-003-session-create.normalized.jsonl)<br>`R-004`: [traces/normalized/R-004-session-resume.normalized.jsonl](../traces/normalized/R-004-session-resume.normalized.jsonl)<br>`X-003`: [runtime-tests.md](../runtime-tests.md) | coding-agent sessions v3; `high`; `supported` | 跨进程恢复同一 session-id 并要求回忆前一进程 token；R-003/R-004 已通过。 |
| `C-009` | 当前 Coding Agent AgentSession 实现自动 compaction 与有限自动 retry：overflow 最多 compact-and-retry 一次，普通可重试错误指数退避且受 maxRetries 限制。 | [S-009: packages/coding-agent/src/core/agent-session.ts:1890-2161](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L1890)<br>[S-010: packages/coding-agent/src/core/agent-session.ts:2573-2637](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L2573) | `X-003`: [runtime-tests.md](../runtime-tests.md) | coding-agent AgentSession; `high`; `supported` | 使用 faux provider 连续返回 overflow 或网络错误，验证上限、事件与上下文保留；定向测试通过。 |
| `C-010` | 新 packages/agent AgentHarness 是低层 loop 之上的通用编排层，但 v0.80.7 尚未替代 Coding Agent AgentSession，且自身自动 compaction、retry、完整 hooks 与半持久恢复仍未完成。 | [D-003: packages/agent/docs/agent-harness.md:1-218](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/docs/agent-harness.md#L1)<br>[D-008: packages/agent/docs/agent-harness.md:291-411](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/docs/agent-harness.md#L291)<br>[S-011: packages/agent/src/harness/agent-harness.ts:314-616](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/src/harness/agent-harness.ts#L314) | `X-002`: [runtime-tests.md](../runtime-tests.md) | new AgentHarness migration state; `high`; `supported` | 检查 Coding Agent 创建路径是否实例化 AgentHarness，或 AgentHarness 是否包含 auto-compaction/retry decision；均未发现。 |
| `C-011` | 真实 SiFlow 场景观察到 read 工具形成两轮 turn：模型 toolUse、read 执行、toolResult 回填、第二次模型调用、最终退出。 | 没有独立源码锚点；结论限于列出的动态/推断证据 | `R-002`: [traces/normalized/R-002-read-tool.normalized.jsonl](../traces/normalized/R-002-read-tool.normalized.jsonl) | R-SCENARIO-002; `high`; `supported` | 将 fixture 值改为未知随机值并要求必须读取；本轮使用合成未知值 314159 且 trace 显示 read start/end。 |
| `C-012` | 持久化 session 能跨独立 Pi 进程恢复对话上下文。 | [S-008: packages/coding-agent/src/core/session-manager.ts:457-1540](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/session-manager.ts#L457) | `R-003`: [traces/normalized/R-003-session-create.normalized.jsonl](../traces/normalized/R-003-session-create.normalized.jsonl)<br>`R-004`: [traces/normalized/R-004-session-resume.normalized.jsonl](../traces/normalized/R-004-session-resume.normalized.jsonl) | R-SCENARIO-003 and R-SCENARIO-004; `high`; `supported` | 第二个进程不提供前一 token，仅恢复 session 后要求返回；已返回 PI_RESUME_2718。 |
| `C-013` | 核心 Coding Agent 不内置 MCP 或 subagent；仓库提供的 subagent 是可选 extension，通过独立 pi --mode json --no-session 子进程隔离上下文，并共享指定 cwd。 | [D-004: packages/coding-agent/README.md:489-503](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/README.md#L489)<br>[D-006: packages/coding-agent/examples/extensions/subagent/README.md:1-175](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/examples/extensions/subagent/README.md#L1)<br>[S-015: packages/coding-agent/examples/extensions/subagent/index.ts:239-698](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/examples/extensions/subagent/index.ts#L239) | 未做专项动态验证；当前由固定源码/文档支持 | default core plus example extension; `high`; `supported` | 默认启动后检查 tool registry 是否出现 MCP/subagent；源码与产品文档否定，extension 场景未动态执行。 |
| `C-014` | Pi 已提供稳定的 agent/message/tool/compaction/retry 事件及 JSON/RPC 输出，但 OTel 风格 trace/span 仍是设计稿，不是 v0.80.7 的默认核心实现。 | [D-005: packages/coding-agent/docs/json.md:1-76](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/docs/json.md#L1)<br>[D-009: packages/agent/docs/observability.md:3-169](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/docs/observability.md#L3) | `R-001`: [traces/normalized/R-001-text-only.normalized.jsonl](../traces/normalized/R-001-text-only.normalized.jsonl)<br>`R-002`: [traces/normalized/R-002-read-tool.normalized.jsonl](../traces/normalized/R-002-read-tool.normalized.jsonl) | observability surfaces; `medium`; `supported` | 搜索并运行默认 instrumentation，检查是否生成 traceId/spanId 或 exporter 调用；JSON trace 未包含，源码只发现设计说明。 |
| `C-015` | 工具批次默认并行执行；全局 sequential 或任一工具声明 executionMode=sequential 会使整批串行，同时最终 toolResult 按模型源码顺序持久化。 | [S-001: packages/agent/src/agent-loop.ts:95-755](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/src/agent-loop.ts#L95) | `X-001`: [runtime-tests.md](../runtime-tests.md) | agent-core tool execution; `high`; `supported` | 脚本化两个不同延迟工具并比较完成事件与持久化结果顺序；定向 agent-loop 测试已通过。 |
| `C-016` | 新 AgentHarness 通过 turn snapshot 与 save point 隔离在途 provider request：运行时配置变化只在下一个安全点刷新，pending session writes 按序落盘。 | [D-003: packages/agent/docs/agent-harness.md:1-218](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/docs/agent-harness.md#L1)<br>[S-011: packages/agent/src/harness/agent-harness.ts:314-616](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/src/harness/agent-harness.ts#L314) | `X-002`: [runtime-tests.md](../runtime-tests.md) | new AgentHarness; `high`; `supported` | 在 tool hook 中切换 model/tools 并检查当前 request 与下一 request；AgentHarness 定向测试覆盖该语义。 |
| `C-017` | 扩展可以实现工具阻断，但此控制点是应用可选 hook，不是不可绕过的全局安全边界。 | [S-003: packages/coding-agent/src/core/agent-session.ts:415-493](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L415)<br>[S-017: packages/coding-agent/examples/extensions/protected-paths.ts:1-29](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/examples/extensions/protected-paths.ts#L1)<br>[D-002: packages/coding-agent/docs/security.md:3-41](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/docs/security.md#L3) | 未做专项动态验证；当前由固定源码/文档支持 | extension tool hooks; `high`; `supported` | 枚举 built-in tools、user ! bash、extension custom tools 与直接进程调用，确认是否全部经过同一 hook；源码表明 extension 自身代码不受该 gate 约束。 |
| `C-018` | orchestrator 是实验性的多 Pi RPC 进程 supervisor，负责 spawn、事件复用、session 元数据和退出清理；它不是默认 Coding Agent 内的 subagent 机制。 | [D-010: packages/orchestrator/README.md:1-5](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/orchestrator/README.md#L1)<br>[S-016: packages/orchestrator/src/supervisor.ts:63-318](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/orchestrator/src/supervisor.ts#L63) | 未做专项动态验证；当前由固定源码/文档支持 | packages/orchestrator; `medium`; `supported` | 从默认 pi CLI 追踪是否自动创建 OrchestratorSupervisor；未发现，orchestrator 包明确标记 experimental。 |
| `C-019` | 模型抽象以 provider-owned model catalog、auth resolution 和 stream/streamSimple 为边界；自定义 models.json 可把 OpenAI-compatible endpoint 接入同一循环。 | [S-012: packages/ai/src/models.ts:24-369](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/ai/src/models.ts#L24) | `R-005`: [runtime-tests.md](../runtime-tests.md)<br>`R-001`: [traces/normalized/R-001-text-only.normalized.jsonl](../traces/normalized/R-001-text-only.normalized.jsonl) | pi-ai and coding-agent model registry; `high`; `supported` | 通过 models.json 注册 SiFlow 并运行 --list-models 与文本请求；两者均成功。 |
| `C-020` | 恢复策略按错误类型分层：context overflow 走 compaction，其他 retryable provider error 走指数退避，truncated tool-call 参数则拒绝执行并回送错误。 | [S-001: packages/agent/src/agent-loop.ts:95-755](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/src/agent-loop.ts#L95)<br>[S-009: packages/coding-agent/src/core/agent-session.ts:1890-2161](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L1890)<br>[S-010: packages/coding-agent/src/core/agent-session.ts:2573-2637](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L2573) | `X-001`: [runtime-tests.md](../runtime-tests.md)<br>`X-003`: [runtime-tests.md](../runtime-tests.md) | coding-agent and agent-core failure paths; `high`; `supported` | 分别注入 length stop、overflow 与网络错误；定向测试覆盖三类分支。 |

## 使用边界

- 点击源码链接时应核对固定 commit，不要用当前默认分支替代版本事实。
- `R` 场景使用真实 SiFlow；`X` 使用 faux provider/定向 tests。`passed` 只表示预声明断言成立。
- 完整 conditions、counterevidence、coverage refs 和 record schema 以 [`claims.jsonl`](../evidence/claims.jsonl) 与 [`observations.jsonl`](../evidence/observations.jsonl) 为准。
"""

REPORTS["16-glossary.md"] = r"""# 全局术语表

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
"""

REPORTS["claim-index.md"] = r"""# Claim Index

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
"""

REPORTS["index.md"] = r"""# Pi Agent Harness 架构恢复报告

分析对象：`earendil-works/pi` tag `v0.80.7`，commit `818d67457cdd6b60bce6b121d16b23141c252dd8`。

本报告不是文件树摘要。结论来自固定版本源码、官方仓库文档、4 个真实 SiFlow 场景和 3 组 faux-provider 定向测试，并通过 Harness Analysis validator 做了 claims/evidence/HIR 的交叉校验。首次遇到内部类型、事件名或 provider/session 术语时，可查[全局术语表](16-glossary.md)。

## 一句话结论

Pi 是一个“薄核心、强扩展、外部隔离”的 agent harness：`pi-ai` 统一 provider，`agent-core` 提供通用模型/工具循环，Coding Agent 的 `AgentSession` 负责当前产品级 compaction、retry、session、资源和 extension 编排；新的通用 `AgentHarness` 正在把这些职责下沉，但在 `v0.80.7` 还没有替代 `AgentSession`。[D: D-001, D-003, D-008] [S: S-001, S-002, S-011]

![Pi system overview](../diagrams/generated/pi-system-overview.png)

> 图 1（gpt-image-2 读者插图）：六步主轴优先解释 Pi 的当前运行路径；迁移、可选 gate、durable state 和外部隔离被降为支路。图像经过标签、箭头、可选性和边界语义审查；它不是证据真值。图像的 prompt、output hash 与语义审查见[生成图 metadata](../diagrams/generated/metadata.json)；结构事实来自[Harness IR](../hir.json)和下列 Evidence IDs。Evidence: `S-001`, `S-002`, `S-008`, `S-012`, `S-013`, `S-017`, `R-001`, `R-002`, `R-004`, `X-002`, `X-003`。

## 阅读框架

先阅读[设计空间与贯穿案例](00-design-space-and-running-example.md)。它用六个 recurring design questions 解释 Pi 的选择，并以真实 `read -> toolResult -> second model call` trace 贯穿后续章节。Subsystem 章节提供机制细节；claim index、HIR 和技术投影负责审计，不要求正文图同时承担全部证据浏览任务。

## 核心发现

1. **真正的 canonical loop 很小。** `runAgentLoop()` 负责模型流、toolUse、toolResult、steering/follow-up 和退出。工具默认并行；任一工具声明 sequential 会让整批串行；结果仍按模型给出的 tool call 顺序进入 transcript。[C: C-002, C-015] [S: S-001] [X: X-001]

2. **当前有两层产品编排和一条迁移线。** `AgentSession` 是 Coding Agent 当前产品路径；新 `AgentHarness` 直接调用相同 low-level loop，通过 turn snapshot/save point 处理配置和持久化顺序，但 auto-compaction、retry、generic hooks、semi-durable recovery 与 Coding Agent migration 尚未完成。[C: C-010, C-016]

3. **安全边界不在进程内。** Project trust 只阻止未授权项目资源在启动时改变配置/extension；默认 read/write/edit/bash 与 extension 仍以 Pi 进程权限执行。逐工具确认、protected paths 和 subagent confirmation 都是可选 extension 策略，真正隔离依赖 container/VM/OS policy。[C: C-005, C-006, C-007, C-017]

4. **session 是 durable tree，不是平铺 chat log。** JSONL v3 entry 通过 `id/parentId` 形成树，leaf 选择 active branch；compaction summary 是一等 entry。跨两个独立 Pi 进程的恢复实验成功找回合成 token `PI_RESUME_2718`。[C: C-008, C-012] [R: R-003, R-004]

5. **核心不规定 MCP/subagent 工作流。** 默认没有 MCP 和 subagent；示例 subagent extension 通过独立 `pi --mode json --no-session` 进程获得隔离 context，但默认共享 cwd。另有 experimental orchestrator 管理独立 RPC Pi 实例，它不是默认 agent loop 的 delegation。[C: C-013, C-018]

6. **可观测性是事件流，不是完整 distributed trace。** JSON/RPC 暴露 message/tool/compaction/retry/settled 事件，足够重建一次运行；默认事件没有 traceId/spanId。仓库的 OTel/Sentry adapter 仍是 design notes。[C: C-014]

## 动态验证结果

| 场景 | 固定配置 | 区分性断言 | 结果与审计产物 | 能证明 | 不能推出 |
|---|---|---|---|---|---|
| `R-SCENARIO-001` | JSON mode；SiFlow；no session/tools/resources | 无工具时一次 provider turn 后是否进入 `agent_settled` | `PI_TEXT_OK`；`R-001-text-only.normalized.jsonl` | 最短真实模型生命周期至少成功一次 | 不证明 tool、session 或 retry 路径 |
| `R-SCENARIO-002` | JSON mode；只开放 `read`；合成 fixture | toolResult 是否进入第二次 provider request | read start/end、2 turns、`314159`；`R-002-read-tool.normalized.jsonl` | 真实 model -> tool -> context -> model 闭环 | 不证明 write/bash 的权限或隔离 |
| `R-SCENARIO-003/004` | 相同 session id；两个独立进程；无工具 | 新进程能否只靠 JSONL 恢复未重发 token | 恢复 `PI_RESUME_2718`；raw session copy + normalized events | 正常尾部写入后的跨进程恢复 | 不证明 corruption、半写入或 workspace rollback |
| `X-SCENARIO-001` | faux provider；agent-core tests | loop、并行/顺序、hooks、queue、length-stop 分支是否满足 contract | `39/39`；测试文件固定在 `X-001` | controller 分支在定向测试中通过 | 不评价真实模型选择工具的质量 |
| `X-SCENARIO-002` | faux provider；新 `AgentHarness` tests | snapshot/save point、pending writes 和 helper 是否按设计工作 | `61/61`；`X-002` | 迁移中 harness 的现有 contract | 不代表已替代 Coding Agent `AgentSession` |
| `X-SCENARIO-003` | Coding Agent recovery tests | overflow/threshold compaction、retry、context rebuild 是否分层 | `31/31`；`X-003` | 当前产品路径的定向恢复行为 | 不证明真实 crash、SIGINT 或超长模型场景 |

## 最高价值未知项

- 新 `AgentHarness` 与 Coding Agent `AgentSession` 的迁移/差分一致性尚未证明。
- Gondolin、Docker、OpenShell 和 extension custom tools 的完整 side-effect matrix 未运行。
- 损坏 JSONL、真实 SIGINT/tool timeout/进程 crash、半持久 turn recovery 未做故障注入。
- SiFlow 服务端仍默认输出 thinking，Pi 的 `reasoning:false` 没有关闭服务端 chat template；不影响循环验证，但属于 provider compatibility gap。

## 报告导航

- [设计空间与贯穿案例](00-design-space-and-running-example.md)
- [范围与方法](01-scope-method.md)
- [入口与生命周期](02-interfaces-lifecycle.md)
- [核心循环与编排](03-core-loop.md)
- [上下文、记忆与压缩](04-context-memory-compaction.md)
- [模型、工具与扩展](05-models-tools-extensions.md)
- [权限、sandbox 与 workspace](06-permissions-sandbox-workspace.md)
- [Subagent 与 delegation](07-subagents-delegation.md)
- [Session、持久化与恢复](08-sessions-persistence-recovery.md)
- [可观测性](09-observability.md)
- [设计决策与权衡](10-design-decisions.md)
- [运行实验](11-runtime-experiments.md)
- [失败模式与开放问题](12-failure-modes-open-questions.md)
- [覆盖与复现](13-coverage-reproducibility.md)
- [与 2604.14228 的质量对照](quality-comparison-2604.14228.md)
- [源码与 Claim 索引](14-source-claim-index.md)
- [全局术语表](16-glossary.md)
- [兼容 Claim index](claim-index.md)

结构化真值：[manifest](../manifest.json) · [HIR](../hir.json) · [claims](../evidence/claims.jsonl) · [evidence](../evidence/observations.jsonl) · [coverage](../evidence/coverage.json) · [scenarios](../scenarios/catalog.json)
"""

REPORTS["quality-comparison-2604.14228.md"] = r"""# 与 2604.14228 的质量对照

基准：[Dive into Claude Code: The Design Space of Today's and Future AI Agent Systems](https://arxiv.org/html/2604.14228)，v2，2026-07-02。本页评价的是报告方法与表达，不把 Claude Code 和 Pi 的产品复杂度直接等同。

## 维度对照

| 维度 | 2604.14228 | 初版 Pi 报告 | 本轮改进后 | 仍然缺少 |
|---|---|---|---|---|
| 证据可追溯 | A/B/C tiers，正文引用文件/函数 | D/S/R/X/I + claim/HIR，严谨但阅读成本高 | 保留机器证据，正文图和设计问题仍可回到 ID | 源码链接还不是交互式 HTML tooltip |
| 动态验证 | 主要是固定源码快照和文档/社区材料 | 4 个 real-model 场景 + 131 个定向测试 | 不变，这是 Pi 报告相对更强的一项 | 缺 write/bash/sandbox/subagent/fault-injection 实跑 |
| 设计综合 | 五类 values -> 13 principles -> implementation | 以 subsystem 和事实为主，解释链较弱 | 新增六个 design questions 和 stance -> mechanism -> consequence | Pi 作者公开价值声明较少，不能安全复刻五价值框架 |
| 贯穿案例 | “Fix auth.test.ts” 跨 3-9 节反复出现 | 实验散落，没有统一阅读线 | 用 R-SCENARIO-002 贯穿 loop/context/tool/event | read-only 案例不足以覆盖写入、权限和恢复 |
| 系统总览图 | 7 个组件、单一主轴、图标和语义色 | 16 节点技术图，横向过宽、组序错误、回边交叉 | gpt-image 读者图将主路径压为六步，并以图标、短标签和虚线支路分离迁移/gate；HIR/story spec 保留证据 | 仍没有点击展开源码 |
| Turn flow 图 | 为每轮迭代定制纵向布局，读者快速理解循环 | 自动 HIR 分组把控制顺序打乱 | gpt-image 纵向图严格复现两轮 read trace；trace/HIR 保留完整状态投影 | 只覆盖一个代表 trace，不是全状态机 |
| 图与证据关系 | caption 和正文说明，图本身不携带结构化 evidence | 技术图/HIR metadata 强，但颜色几乎全被 evidence state 占用 | HIR + story spec + Mermaid source + 受事实约束的读者 PNG；prompt/hash/review metadata 可审计 | 需要 HTML viewer 才能把 metadata 变成可点交互 |
| 比较与外部有效性 | 对比 OpenClaw/Hermes，并连接相关工作与未来方向 | 单仓库深挖 | 新增 alternatives，但没有完整跨仓库 synthesis | 需要用相同 Skill 分析更多 harness 后再横向比较 |
| 失败与不确定性 | 有 limitations，但主要来自静态逆向边界 | 明确 blocked experiments、conditions 和最高价值 unknowns | 新章节继续保留，不被叙事图掩盖 | 高风险失败路径尚未在强隔离环境中执行 |
| 可复现性 | 论文源码和 figure assets 可用 | manifest/HIR/evidence/scenario/trace/scripts 完整 | 新增 story spec、reader prompts、link/PNG audit | 还没有 commit-to-commit architecture diff CI |

## 初版图片的具体问题

初版 8 张图是合格的 evidence views，但不适合直接作为论文正文图：

1. `attributes.layer` 按字符串排序，system overview 出现 context -> execution -> infrastructure -> interface 的阅读顺序。
2. 节点几乎全部是绿色 observed，状态编码压过了 interface/model/state/policy 等语义差异。
3. 所有 group 都是一列卡片，导致主路径弯折、toolResult 回边跨越多个 group。
4. 2000px 左右横图缩进 Markdown 后字体偏小，edge label 与 node/edge 局部相撞。
5. 节点显示 HIR type 对审计有用，对第一次阅读是额外噪声。
6. 自动图试图同时表达当前产品路径、新 Harness、恢复、状态和观测，没有单一视觉论点。

论文图更清楚的原因不是“更花哨”，而是每张图有不同的人工语义投影：system overview 只保留七个责任，turn flow 明确重复 iteration，extension 图围绕三个 injection points，context 图按加载时机和可变性组织。它没有把整个 call graph 交给一种布局算法。

## 本轮采用的改进

- 把 8 张 HIR 图定义为 technical evidence views，不再默认承担正文解释。
- 新增 `story-specs.json`，以人工语义选择 + 确定性 renderer 生成 5 张正文叙事图（总览、turn、context、extension、design space）。
- 新增 gpt-image-2 reader illustration 层，覆盖全部 8 张唯一正文图，以论文式图标、短标签和单一视觉论点降低阅读门槛；caption 直接链接 HIR、story spec 和 evidence metadata。
- 对生成图执行语义拒绝机制：context v1 因把 tool result 画成直达 model 而被隔离，收紧 prompt 后的 v2 才进入报告。
- 叙事图中的每个实现节点保留 `hir_ids`，每条材料边保留 `evidence_ids`；concept 节点必须有 claim/evidence。
- 使用责任语义色，证据状态改由实线、虚线、点线和 caption 表达。
- 加入六个 design questions、真实 running example 和跨决策张力。
- 新增 output audit，检查 Markdown links、PNG IHDR 尺寸、prompt/output 哈希、semantic review metadata 和极端 aspect ratio。
- 要求最终 raster inspection；XML 可解析不再等价于图像质量合格。

## 尚未追平论文的部分

1. **比较研究。** 当前只有 Pi 单项目，不能得出跨 harness recurring patterns；论文通过 OpenClaw/Hermes 对比解释 deployment context。
2. **文献与产品语境。** Pi 报告没有系统连接 coding-agent taxonomy、治理、长期开发者能力或实证研究。
3. **全路径 running example。** 当前例子真实但只读；论文案例可以在叙事上贯穿 permission、write、subagent 和 persistence，虽然不等于每条都动态验证。
4. **视觉出版物。** 当前是 Markdown + reader PNG + structured evidence model，仍没有统一的 HTML/PDF 排版、交叉引用编号、参考文献系统和响应式交互。
5. **强隔离故障实验。** 对 bash、write、tool timeout、container routing、subagent crash、JSONL corruption 的结论仍主要是静态或单元测试证据。

最合理的下一阶段不是继续增加自由文本，而是选择 disposable VM 中的真实 edit-and-test running example，补齐 side-effect/failure matrix，再用相同 codebook 独立分析第二、第三个 harness，最后做跨项目 design-space synthesis。
"""

RUNTIME_TESTS = r"""# Runtime Test Record

Pinned target: `v0.80.7` / `818d67457cdd6b60bce6b121d16b23141c252dd8`.

## Setup

- Official Node `v22.19.0` portable archive was SHA-256 verified and extracted under `/tmp`.
- `npm ci --ignore-scripts` installed 351 packages; audit reported 0 vulnerabilities.
- Warning: optional `@earendil-works/gondolin@0.12.0` declares Node `>=23.6.0`; Gondolin was not run.
- Isolated HOME and synthetic workspace were used. No API key was stored.

## Model Discovery

Command shape:

```bash
HOME=/tmp/pi-analysis-runtime/home ./pi-test.sh   --list-models siflow --no-extensions --no-skills   --no-prompt-templates --no-context-files
```

Result:

```text
provider  model           context  max-out  thinking  images
siflow    qwen3.6-35ba3b  262.1K   16.4K    no        no
```

## Real Model Scenarios

Common arguments: `--provider siflow --model qwen3.6-35ba3b --mode json --no-extensions --no-skills --no-prompt-templates --no-context-files --no-approve`.

| Scenario | Additional controls | Exit | Event summary | Final |
|---|---|---:|---|---|
| R-001 | `--no-session --no-tools` | 0 | 1 turn, 0 tool, settled | `PI_TEXT_OK` |
| R-002 | `--no-session --tools read` | 0 | 2 turns, read start/end, settled | `314159` |
| R-003 | persistent `analysis-resume-001`, no tools | 0 | JSONL created | `ACK` |
| R-004 | reopen same session in new process | 0 | prior messages restored | `PI_RESUME_2718` |

## Controlled Tests

```text
agent-core loop + Agent:              2 files, 39 passed, 954ms
new AgentHarness/session/compaction:  3 files, 61 passed, 1.26s
Coding Agent compaction/retry/session:3 files, 31 passed, 2.76s
```

Exact test files are recorded in `evidence/observations.jsonl` (`X-001` through `X-003`).

## Trace Handling

Raw traces contain only synthetic prompts/files but may include model thinking. Normalized traces intentionally omit prompt text, assistant text/thinking, tool arguments and tool results. The report and HIR cite normalized traces.
"""


def main() -> int:
    REPORT.mkdir(parents=True, exist_ok=True)
    for name, content in REPORTS.items():
        (REPORT / name).write_text(content.strip() + "\n", encoding="utf-8")
    (ROOT / "runtime-tests.md").write_text(RUNTIME_TESTS.strip() + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
