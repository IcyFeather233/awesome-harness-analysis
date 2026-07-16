#!/usr/bin/env python3
"""Write the Chinese architecture report from the validated Pi analysis model."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "report"
COMMIT = "818d67457cdd6b60bce6b121d16b23141c252dd8"


INDEX = """# Pi Agent Harness 架构恢复报告

分析对象：`earendil-works/pi` tag `v0.80.7`，commit `818d67457cdd6b60bce6b121d16b23141c252dd8`。

本报告不是文件树摘要。结论来自固定版本源码、官方仓库文档、4 个真实 SiFlow 场景和 3 组 faux-provider 定向测试，并通过 Harness Analysis validator 做了 claims/evidence/HIR 的交叉校验。

## 一句话结论

Pi 是一个“薄核心、强扩展、外部隔离”的 agent harness：`pi-ai` 统一 provider，`agent-core` 提供通用模型/工具循环，Coding Agent 的 `AgentSession` 负责当前产品级 compaction、retry、session、资源和 extension 编排；新的通用 `AgentHarness` 正在把这些职责下沉，但在 `v0.80.7` 还没有替代 `AgentSession`。[D: D-001, D-003, D-008] [S: S-001, S-002, S-011]

![Pi system overview](../diagrams/narrative/pi-system-story.svg)

> 图 1：正文级系统总览将当前产品主路径、`AgentHarness` 迁移分支、可选 tool gate 和外部 sandbox 分开。绿色实线是 `R-SCENARIO-001/002/004` 观察到的路径，绿色虚线是控制实验，灰色虚线是源码或文档可见但未运行的可选路径。详细 HIR 投影仍保留在 [技术总览](../diagrams/system-overview.svg)。Evidence: `S-001`, `S-002`, `S-008`, `S-012`, `S-013`, `S-017`, `R-001`, `R-002`, `R-004`, `X-002`, `X-003`。

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

| 场景 | 模式 | 结果 | 主要证明 |
|---|---|---|---|
| `R-SCENARIO-001` | SiFlow real model, no tools | `PI_TEXT_OK` | 最短 turn 与 settled 路径 |
| `R-SCENARIO-002` | SiFlow real model, read only | read start/end，两次 turn，`314159` | 真实 model -> tool -> context -> model loop |
| `R-SCENARIO-003/004` | 两个独立 Pi 进程 | 恢复 `PI_RESUME_2718` | JSONL session 跨进程恢复 |
| `X-SCENARIO-001` | faux provider | `39/39` | loop、并行/顺序、hooks、queue、终止 |
| `X-SCENARIO-002` | faux provider | `61/61` | 新 AgentHarness save point、session、compaction helper |
| `X-SCENARIO-003` | faux provider | `31/31` | Coding Agent compaction、network retry、context rebuild |

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
- [Claim index](claim-index.md)

结构化真值：[manifest](../manifest.json) · [HIR](../hir.json) · [claims](../evidence/claims.jsonl) · [evidence](../evidence/observations.jsonl) · [coverage](../evidence/coverage.json) · [scenarios](../scenarios/catalog.json)
"""


DESIGN_SPACE = """# 00 设计空间与贯穿案例

Pi 的架构不能只用“有哪些 package”来解释。更有区分度的问题是：推理放在哪里、产品编排由谁拥有、默认信任边界在哪里、上下文和持久状态如何增长，以及扩展能力由核心还是用户定义。

## 六个设计问题

| 设计问题 | Pi `v0.80.7` 的答案 | 可选设计 | 证据与置信度 |
|---|---|---|---|
| 推理与控制放在哪里？ | 模型决定下一步；`runAgentLoop()` 只负责 model/tool/queue/stop 的确定性循环 | harness 内置 planner、typed graph 或 task state machine | `D-001`, `S-001`, `R-002`, `X-001`；高 |
| 产品编排由谁拥有？ | 当前由 Coding Agent `AgentSession` 拥有；通用 `AgentHarness` 是尚未完成的迁移目标 | 一个统一 controller，或每个产品自己包装 low-level loop | `D-003`, `D-008`, `S-002`, `S-011`, `X-002`；高 |
| 默认安全姿态是什么？ | 明确继承 Pi 进程权限；project trust 只保护项目资源加载；工具 gate 与 sandbox 都是可选层 | deny-first 逐工具授权、强制进程内 policy、默认容器隔离 | `D-002`, `D-004`, `D-007`, `S-006`, `S-017`；高 |
| 扩展面如何划分？ | 统一 tool registry 加 extension hooks；MCP、subagent、permission UI 不进入核心产品假设 | 固定内置能力，或一个统一 plugin protocol 包办所有扩展 | `D-004`, `S-003`, `S-015`；高 |
| 什么状态是 durable 的？ | append-only JSONL v3 tree 保存 message、branch、compaction 等 entry；workspace 独立存在 | mutable database row、完整 checkpoint、event sourcing + workspace snapshot | `S-008`, `R-003`, `R-004`；高 |
| 失败如何恢复？ | truncated tool call 拒绝执行；provider retry、overflow compaction 与普通 threshold compaction 分层处理 | fail-fast、统一 retry、每轮 checkpoint 回滚 | `S-001`, `S-009`, `S-010`, `X-001`, `X-003`；高 |

这些是“设计选择及其实现”，不是对作者动机的自由推测。仓库文档明确说明 minimal harness、aggressive extensibility 和外部隔离边界；“为什么选 JSONL 而不是数据库”等未文档化原因只作为可观察权衡讨论。[D: D-001, D-002, D-004]

![Pi design space](../diagrams/narrative/pi-design-space.svg)

> 图 A：左列是文档化产品立场，中列是源码恢复出的机制，右列是分析者根据实现和失败边界归纳的权衡。灰色虚线表示 documented/static mapping，橙色点线表示分析推断，不代表作者声明。Evidence: `D-001`, `D-002`, `D-003`, `D-004`, `D-007`, `D-008`, `S-001`, `S-003`, `S-007`, `S-008`, `S-011`, `S-017`, `R-004`, `X-002`。

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

![Observed Pi turn](../diagrams/narrative/pi-observed-turn.svg)

> 图 B：绿色主路径来自同一次真实 trace；右侧 retry/compaction 来自 `X-SCENARIO-003`，session resume 来自独立进程的 `R-SCENARIO-003/004`，不伪装成 read 场景本身发生的分支。Evidence: `S-001`, `S-002`, `S-008`, `S-009`, `S-010`, `R-002`, `R-003`, `R-004`, `X-003`。

## 这个案例不能证明什么

该 trace 没有启用 extensions、skills、context files 或 project approval，也没有执行 bash/write/edit。因此它能证明 model -> read -> toolResult -> second model call -> settled 至少发生过一次，不能证明：

- 所有工具都经过 permission gate；Pi 默认不存在这样的全局 gate；
- deny 之后没有文件、进程或网络副作用；本轮没有做 deny fault injection；
- compaction、retry、subagent 或 session resume 在这一次 read turn 中发生；这些由其他实验或静态证据支撑；
- 真实用户任务中的路径频率、成本分布或长期正确性。

后续章节会沿用这个案例解释 loop、context、tool result 和 event stream；对于它没有覆盖的安全、恢复与持久化路径，会显式切换到对应的 `S`、`R` 或 `X` 证据。
"""

QUALITY_COMPARISON = """# 与 2604.14228 的质量对照

基准：[Dive into Claude Code: The Design Space of Today's and Future AI Agent Systems](https://arxiv.org/html/2604.14228)，v2，2026-07-02。本页评价的是报告方法与表达，不把 Claude Code 和 Pi 的产品复杂度直接等同。

## 维度对照

| 维度 | 2604.14228 | 初版 Pi 报告 | 本轮改进后 | 仍然缺少 |
|---|---|---|---|---|
| 证据可追溯 | A/B/C tiers，正文引用文件/函数 | D/S/R/X/I + claim/HIR，严谨但阅读成本高 | 保留机器证据，正文图和设计问题仍可回到 ID | 源码链接还不是交互式 HTML tooltip |
| 动态验证 | 主要是固定源码快照和文档/社区材料 | 4 个 real-model 场景 + 131 个定向测试 | 不变，这是 Pi 报告相对更强的一项 | 缺 write/bash/sandbox/subagent/fault-injection 实跑 |
| 设计综合 | 五类 values -> 13 principles -> implementation | 以 subsystem 和事实为主，解释链较弱 | 新增六个 design questions 和 stance -> mechanism -> consequence | Pi 作者公开价值声明较少，不能安全复刻五价值框架 |
| 贯穿案例 | “Fix auth.test.ts” 跨 3-9 节反复出现 | 实验散落，没有统一阅读线 | 用 R-SCENARIO-002 贯穿 loop/context/tool/event | read-only 案例不足以覆盖写入、权限和恢复 |
| 系统总览图 | 7 个组件、单一主轴、图标和语义色 | 16 节点技术图，横向过宽、组序错误、回边交叉 | 12 节点叙事图，主轴、迁移、可选 gate、外部边界分离 | 仍是静态 SVG，没有点击展开源码 |
| Turn flow 图 | 为每轮迭代定制纵向布局，读者快速理解循环 | 自动 HIR 分组把控制顺序打乱 | 按真实 trace 画蛇形两轮流，并隔离旁支证据 | 只覆盖一个代表 trace，不是全状态机 |
| 图与证据关系 | caption 和正文说明，图本身不携带结构化 evidence | SVG/HIR metadata 强，但颜色几乎全被 evidence state 占用 | 技术图保留证据色；叙事图用语义色，metadata 保留 evidence | 需要 HTML viewer 才能把 metadata 变成可点交互 |
| 比较与外部有效性 | 对比 OpenClaw/Hermes，并连接相关工作与未来方向 | 单仓库深挖 | 新增 alternatives，但没有完整跨仓库 synthesis | 需要用相同 Skill 分析更多 harness 后再横向比较 |
| 失败与不确定性 | 有 limitations，但主要来自静态逆向边界 | 明确 blocked experiments、conditions 和最高价值 unknowns | 新章节继续保留，不被叙事图掩盖 | 高风险失败路径尚未在强隔离环境中执行 |
| 可复现性 | 论文源码和 figure assets 可用 | manifest/HIR/evidence/scenario/trace/scripts 完整 | 新增 story spec、叙事 renderer、link/SVG audit | 还没有 commit-to-commit architecture diff CI |

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
- 叙事图中的每个实现节点保留 `hir_ids`，每条材料边保留 `evidence_ids`；concept 节点必须有 claim/evidence。
- 使用责任语义色，证据状态改由实线、虚线、点线和 caption 表达。
- 加入六个 design questions、真实 running example 和跨决策张力。
- 新增 output audit，检查 Markdown links、SVG title/description、正文图 metadata、节点密度和极端 aspect ratio。
- 要求最终 raster inspection；XML 可解析不再等价于图像质量合格。

## 尚未追平论文的部分

1. **比较研究。** 当前只有 Pi 单项目，不能得出跨 harness recurring patterns；论文通过 OpenClaw/Hermes 对比解释 deployment context。
2. **文献与产品语境。** Pi 报告没有系统连接 coding-agent taxonomy、治理、长期开发者能力或实证研究。
3. **全路径 running example。** 当前例子真实但只读；论文案例可以在叙事上贯穿 permission、write、subagent 和 persistence，虽然不等于每条都动态验证。
4. **视觉出版物。** 当前是 Markdown + SVG，没有统一的 HTML/PDF 排版、交叉引用编号、参考文献系统和响应式交互。
5. **强隔离故障实验。** 对 bash、write、tool timeout、container routing、subagent crash、JSONL corruption 的结论仍主要是静态或单元测试证据。

最合理的下一阶段不是继续增加自由文本，而是选择 disposable VM 中的真实 edit-and-test running example，补齐 side-effect/failure matrix，再用相同 codebook 独立分析第二、第三个 harness，最后做跨项目 design-space synthesis。
"""

SCOPE = """# 01 范围与方法

## 冻结对象

- Repository：`https://github.com/earendil-works/pi`
- Tag：`v0.80.7`
- Commit：`818d67457cdd6b60bce6b121d16b23141c252dd8`
- Worktree：detached HEAD，分析开始和结束时目标代码无 tracked changes
- Runtime：Linux x86_64；临时 Node `22.19.0`；npm `10.9.3`；Vitest `4.1.9`
- Real model：`siflow/qwen3.6-35ba3b`，OpenAI-compatible endpoint；无 API key

完整配置见 [manifest.json](../manifest.json)。

## 证据等级

| 标记 | 含义 | 本报告用途 |
|---|---|---|
| `D` | 仓库文档 | 产品边界、明确意图、已知未完成项 |
| `S` | 固定 commit 源码 | 实现结构与可能路径 |
| `R` | 真实运行观察 | 命名配置下一次确实发生的路径 |
| `X` | 控制实验/定向测试 | controller 分支与反例验证 |
| `I` | 分析推断 | 本轮没有把纯推断写成 HIR 事实 |

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


INTERFACES = """# 02 入口与生命周期

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
"""


CORE_LOOP = """# 03 核心循环与编排

![Observed runtime turn](../diagrams/narrative/pi-observed-turn.svg)

> 图 2：正文图严格复现 `R-SCENARIO-002` 的两次模型迭代；右侧 recovery 与 durable session 是来自其他命名实验的旁支，不表示它们在 read trace 中发生。完整的 HIR 状态投影保留在[技术 turn flow](../diagrams/turn-flow.svg)。Evidence: `S-001`, `S-002`, `S-008`, `S-009`, `S-010`, `R-002`, `R-003`, `R-004`, `X-003`。

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
"""


CONTEXT = """# 04 上下文、记忆与压缩

![Context lifecycle](../diagrams/narrative/pi-context-assembly.svg)

> 图 3：上下文来源按 startup/lazy、carry-forward、runtime 和 compaction 分开，再汇聚到 per-request construction。实线来自命名 trace，灰色虚线是源码路径，绿色虚线来自 compaction 控制实验。完整节点级投影见[技术 context view](../diagrams/context-lifecycle.svg)。Evidence: `S-001`, `S-002`, `S-004`, `S-005`, `S-008`, `S-009`, `R-001`, `R-002`, `R-004`, `X-003`。

## Context 来源

| 来源 | 生命周期 | 进入方式 |
|---|---|---|
| 默认/自定义 system prompt | startup + refresh | `buildSystemPrompt()` |
| AGENTS.md / CLAUDE.md | startup/reload | `<project_instructions>`；不受 project trust 保护，除非禁用 context files |
| `.pi/SYSTEM.md` / append prompt | startup/reload | 受 project trust 保护 |
| Skills metadata | startup/reload | 有 read tool 时列在 system prompt |
| `/skill:name` full body | lazy, per invocation | 展开成 user-side invocation text |
| Active session branch | carry-forward | `buildSessionContext()` |
| ToolResult | per tool turn | 追加 transcript 后进入下一模型请求 |
| Extension messages/system override | per turn | `before_agent_start` |
| Context hook transform | per provider request | `transformContext` 后再 `convertToLlm` |

[C: C-003] 的置信度为 medium，因为本轮没有部署 request proxy 做全部 source 的差分；真实场景只验证了最小路径和 toolResult 回填。

## Durable memory

Pi 没有独立向量 memory 层。核心 durable memory 是 session tree：message、model/thinking change、custom entry、compaction、branch summary 等都在 JSONL 中；active branch 通过 parent chain 与 leaf 计算。workspace 文件是另一条独立持久层，不会自动与 session rollback 保持一致。[S: S-008]

## Compaction

Coding Agent 分两类：

- **Overflow**：错误或 usage 超过当前 model window；删除 live context 中的 error，生成 summary，最多 compact-and-retry 一次。
- **Threshold**：接近窗口时压缩，但不自动重新回答已完成的 assistant turn。

Compaction entry 保存 summary、`firstKeptEntryId`、`tokensBefore` 和 details；随后重建 active context。[S: S-009] [X: X-003]

新 `AgentHarness.compact()` 已有手动结构操作和 compaction helpers，但 auto-compaction decision 尚未实现。[D: D-008]
"""


TOOLS = """# 05 模型、工具与扩展

![Tool and extension surface](../diagrams/narrative/pi-extension-injection.svg)

> 图 4：Pi 的扩展面不是一个统一 plugin 入口，而是三类控制点：改变模型所见 context、改变模型可调用的 registry、改变 action 是否或在哪里执行。默认 host execution 与可选 gate/sandbox 被分开；完整证据投影见[技术 extension view](../diagrams/tool-extension-surface.svg)。Evidence: `D-002`, `D-004`, `D-007`, `S-001`, `S-002`, `S-003`, `S-007`, `S-015`, `S-017`, `R-002`。

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

## Hook 注入点

- `input`：handled 或 transform；
- `before_agent_start`：加 custom messages 或替换当轮 system prompt；
- `context`：模型边界前变换消息；
- `tool_call`：validated args 后、execute 前，可 block；
- `tool_result`：execute 后，可改 content/details/error；
- provider request/payload/response hooks；
- session switch/fork/compact/tree lifecycle hooks。

这些 hooks 是控制面，不是被隔离的 plugin VM；extension TypeScript 与主进程同权限。[D: D-002]

## 不内置的协议

核心明确不内置 MCP。要么把 CLI + README 暴露成 skill，要么 extension 自行注册 MCP tool。因而 HIR 中没有把 MCPServer 画成现存核心组件。[D: D-004]
"""


SECURITY = """# 06 权限、Sandbox 与 Workspace

![Permission pipeline](../diagrams/permission-pipeline.svg)

> 图 5：默认路径与可选 gate。绿色 loop -> read -> workspace 是真实观察；`Optional extension gate` 是有条件的静态/实验路径，不能读成全局强制审批。External sandbox 仅为文档化部署选项。Evidence: `D-002`, `D-004`, `D-007`, `S-003`, `S-006`, `S-007`, `S-017`, `R-002`, `X-001`。

## 三个容易混淆的边界

1. **Project trust**：启动资源加载 gate。它防止仓库在未确认时加载 `.pi/settings.json`、extensions、skills、SYSTEM 等。它不限制模型之后调用 read/bash/write。[C: C-006]
2. **Tool hook**：可选 application policy。extension 可在 `tool_call` 返回 block；`protected-paths.ts` 是示例，不是默认策略。[C: C-017]
3. **Sandbox**：OS/container/VM 边界。Pi 默认没有；需要 whole-process Docker/OpenShell，或用 Gondolin extension 路由 built-in tools。[C: C-005]

## 默认 side-effect path

内置 bash 在 cwd 启动 shell，默认继承进程环境；timeout 参数可选且无默认值。Unix 使用 detached process group，abort/timeout 会 kill tree。extension 代码、package install、language server 与 shell 子进程都处于同一用户权限边界。[C: C-007]

## 外部隔离的绕行风险

Gondolin example 覆盖内置 tools 与 `!` command，但其他 custom extension tools 仍在 host，除非自己 delegate。Whole-process container 更完整，但 bind-mounted workspace 仍会写回 host；挂载 host agent dir 还会暴露 sessions/settings/auth。[D: D-007]

## 本轮没有做什么

没有触发 bash/write/edit，也没有声称验证了 deny 后“零副作用”。这是安全限制，不是系统具备 deny gate 的证据。要验证部署安全，需要在 disposable VM 中跑 tool/extension/`!`/subagent 的 side-effect matrix。
"""


SUBAGENTS = """# 07 Subagent 与 Delegation

![Subagent topology](../diagrams/subagent-topology.svg)

> 图 6：核心默认没有 subagent；图中两条 delegation 都带条件。Subagent example 是可选 extension，OrchestratorSupervisor 属于 experimental package。本轮只做源码分析。Evidence: `D-004`, `D-006`, `D-010`, `S-015`, `S-016`。

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

Project-local agent prompt 是 repo-controlled；interactive mode 可确认，但 headless 退化路径本轮未验证。

## Experimental orchestrator

`OrchestratorSupervisor` 创建一个 RPC Pi child per instance，复用 events/UI request，持久化 instance/session metadata，并在意外退出时标 error/清理 Radius presence。restart recovery 只是把原 online/starting 记录标 stopped，没有恢复 in-flight child。[C: C-018]

它更像 multi-session process supervisor，不是 agent loop 中的 parent/child delegation primitive。
"""


PERSISTENCE = """# 08 Session、持久化与恢复

![Persistence lifecycle](../diagrams/persistence-lifecycle.svg)

> 图 7：live active branch、durable JSONL、compaction 与恢复。`R-SCENARIO-003/004` 观察到 create/persist/restore；compaction/retry 来自定向 tests。Evidence: `S-008`, `S-009`, `S-010`, `S-014`, `R-003`, `R-004`, `X-003`。

## JSONL v3

首行是 session header：version、session id、timestamp、cwd、可选 parentSession。后续每个 entry 有短 id、parentId、timestamp；append 作为 current leaf 的 child 并推进 leaf。类型包括 message、model/thinking/tool changes、custom、compaction、branch summary、label、session info 等。[S: S-008]

读取时 Pi 流式解析 JSONL，单个 malformed line 会被跳过；非空文件如果最终没有合法 Pi header 则拒绝打开。v1/v2 会迁移到 v3并重写文件。中间 entry 损坏是否造成可接受但错误的 branch 仍是开放风险。

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


OBSERVABILITY = """# 09 可观测性

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


DECISIONS = """# 10 设计决策与权衡

本节把“实现了什么”和“作者为什么这样做”分开。文档明确的产品立场使用 D evidence；源码可见机制使用 S evidence；右侧收益和代价是根据边界与实验形成的分析综合，不自动等价于作者动机。

![Pi design space](../diagrams/narrative/pi-design-space.svg)

> 图 8：四条主要立场经过实现机制形成可观察后果。左到中是文档/源码 mapping，使用灰色虚线；中到右是分析综合，使用橙色点线。Evidence: D-001, D-002, D-003, D-004, D-007, D-008, S-001, S-003, S-007, S-008, S-011, S-017, R-004, X-002。

## 决策记录

| 决策 | 当前机制 | Documented intent | 收益 | 代价/风险 | Evidence |
|---|---|---|---|---|---|
| 薄 low-level loop | `runAgentLoop` + callbacks | agent-core 通用 runtime | 易嵌入、可用 faux provider 测试 | 产品编排落到上层，出现两代 orchestration | `S-001`, `D-003` |
| 工具默认并行 | batch 并发，sequential tool 可降级整批 | 文档/源码明确 | 降低多工具 latency | completion order 与 transcript order 不同，hooks 要理解双顺序 | `S-001`, `X-001` |
| 扩展优先而非内置工作流 | extensions/skills/packages | README 明确“aggressively extensible” | core 小、用户可定制 | 安全、subagent、MCP 行为不统一 | `D-004`, `S-003` |
| 无内置 sandbox/permission popup | 进程权限 + 外部隔离 | security 文档明确 intentional | 可直接使用本地 toolchain，不制造虚假边界 | unattended/untrusted 任务必须由部署层治理 | `D-002`, `D-007` |
| Project trust 只守启动资源 | path-based persisted decision | security 文档明确 | 防止 repo 静默注入 extension/settings | AGENTS/context prompt injection 仍存在，工具不受限 | `D-002`, `S-006` |
| Session 用 append-only tree | JSONL id/parentId/leaf | 源码与 session 文档 | branch/fork/compaction 可保留历史 | workspace 不随 branch 回滚；损坏恢复更复杂 | `S-008`, `R-004` |
| Compaction 是一等 entry | summary + first kept + token metadata | 实现明确；作者意图未单独说明 | 可重建 context、保留审计历史 | summary 有信息损失，需要额外模型调用 | `S-009`, `X-003` |
| 新 Harness 用 snapshot/save point | in-flight immutable, next safe point refresh | lifecycle 文档明确 | 配置热更新不污染当前 request，持久顺序确定 | phase/reentrancy/settled 仍在硬化 | `D-003`, `S-011`, `X-002` |
| Provider owns auth + stream | `Models` runtime collection | 源码 contract | 多 provider 与 custom endpoint 共用 loop | compatible server 的细节仍可能泄漏（如 thinking） | `S-012`, `R-005` |
| Event-first observability | structured lifecycle events | design notes 明确不绑定 vendor | JSON/RPC 易消费 | 缺 trace/span correlation 与默认 redaction/exporter | `D-005`, `D-009` |

## 跨决策张力

### 通用核心与产品一致性

薄 loop 让 agent-core 易嵌入，但 compaction、retry、session ordering 和 settled semantics 必须由上层拥有。新 AgentHarness 的出现说明可复用性问题已经从“能否调用 loop”转成“不同 orchestration 是否行为等价”。最有区分度的下一步不是更多单元测试，而是 AgentSession 与 AgentHarness 的 differential scenario suite。[C: C-010, C-016]

### 扩展自由与统一治理

registry/hooks 能把 subagent、MCP、permission UI 和自定义工具留给用户，但同样意味着不存在一个不可绕过的 application-level policy plane。若部署目标从本地交互式工具转向 unattended service，合理替代不是再加一个示例 hook，而是 whole-process isolation 或可证明覆盖所有 side-effect backend 的统一 capability boundary。[C: C-005, C-017]

### 可审计 session 与不可回滚 workspace

JSONL tree 完整保存 branch、compaction 和 resume 历史，却不为文件系统提供相同事务语义。用户可以回到旧 conversation leaf，但 workspace 仍是新状态。这不是 session bug，而是两个 durable subsystem 没有共同 checkpoint protocol 的结构性结果。[C: C-008, C-012]

没有文档化的作者动机不在表中伪装成事实。例如“为什么 JSONL 而非数据库”未找到直接说明，报告只陈述可观察 tradeoff。
"""


EXPERIMENTS = """# 11 运行实验

完整命令和结果见 [runtime-tests.md](../runtime-tests.md)，场景机器可读记录见 [catalog.json](../scenarios/catalog.json)。

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


FAILURES = """# 12 失败模式与开放问题

## 已验证或源码明确的 failure path

| 失败 | 当前行为 | Evidence |
|---|---|---|
| Provider retryable error | 指数退避；maxRetries 有界；live context 移除 error，session 保留 | `S-010`, `X-003` |
| Context overflow | compact；错误型 overflow 最多自动 retry 一次 | `S-009`, `X-003` |
| Length-truncated tool call | 全部拒绝执行，返回 error result | `S-001`, `X-001` |
| Tool exception | 转为 `isError` toolResult，进入模型 context | `S-001`, `X-001` |
| Bash timeout/abort | kill process tree；输出保留并带状态 | `S-007` |
| Session file 非空但无合法 header | 拒绝打开 | `S-008` |
| New AgentHarness hook failure | 归一化 AgentHarnessError；某些 post-commit hook failure 不回滚 | `D-003`, `S-011` |
| Orchestrator child exit | instance 标 error、reject pending、清理 resources | `S-016` |

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

1. AgentSession vs AgentHarness differential scenario suite。
2. Container/VM 内的 permission bypass matrix：built-in、`!`、custom tool、extension direct process、subagent。
3. JSONL corruption matrix：header/middle/tail/parent/compaction/leaf。
4. Provider proxy capture：context source differential + redaction。
5. Orchestrator restart/crash 与 child cleanup。

机器可读问题清单见 [questions.json](../questions.json)。
"""


REPRO = """# 13 覆盖与复现

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
- Diagram sources/SVG/metadata：`diagrams/`
- Narrative story spec：[story-specs.json](../diagrams/story-specs.json)
- Narrative SVG/metadata：`diagrams/narrative/`

## 关键复现命令

```bash
# 归一化 synthetic traces
python3 reproduce/normalize_pi_trace.py   traces/raw/R-002-read-tool.jsonl   traces/normalized/R-002-read-tool.normalized.jsonl   --scenario-id R-SCENARIO-002

# 重建 structured evidence/HIR
python3 reproduce/compile_analysis.py

# 严格校验
python3 ../harness-analysis/scripts/validate_analysis.py . --strict

# 重渲染图
python3 ../harness-analysis/scripts/render_diagrams.py .

# 重渲染正文叙事图，并校验 HIR/claim/evidence 引用
python3 ../harness-analysis/scripts/render_story_diagrams.py .

# 重写报告
python3 reproduce/compile_report.py

# 检查 Markdown links、SVG accessibility、正文图密度与元数据
python3 ../harness-analysis/scripts/audit_outputs.py . --strict
```

## 验证结果

- Analysis validator：`0 errors, 0 warnings`
- XML parse：8/8 技术 SVG + 5/5 叙事 SVG valid
- Output audit：Markdown links、report-facing SVG 与 narrative metadata 通过 strict
- Diagram density：overview 16 nodes；turn 11；context 9；permission 11；subagent 10；persistence 7
- Narrative density：system 12 nodes；observed turn 12；context 8；extension 11；design space 12
- Tests：39 + 61 + 31 = 131 passed
- Target `git status --short`：clean（依赖目录被 gitignore，不改变固定源码）

## Coverage statement

源码 inventory 共 1021 files，未达到 file/size scan limit。14 模块均有记录；partial 模块与 unresolved 条目不会被“未发现”等价成“不存在”。Runtime coverage 只代表 Linux/Node/JSON-mode/SiFlow 与命名 faux-provider tests。
"""


RUNTIME_TESTS = """# Runtime Test Record

Pinned target: `v0.80.7` / `818d67457cdd6b60bce6b121d16b23141c252dd8`.

## Setup

- Official Node `v22.19.0` portable archive was SHA-256 verified and extracted under `/tmp`.
- `npm ci --ignore-scripts` installed 351 packages; audit reported 0 vulnerabilities.
- Warning: optional `@earendil-works/gondolin@0.12.0` declares Node `>=23.6.0`; Gondolin was not run.
- Isolated HOME and synthetic workspace were used. No API key was stored.

## Model Discovery

Command shape:

```bash
HOME=/tmp/pi-analysis-runtime/home ./pi-test.sh \
  --list-models siflow --no-extensions --no-skills \
  --no-prompt-templates --no-context-files
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


REPORTS = {
    "index.md": INDEX,
    "00-design-space-and-running-example.md": DESIGN_SPACE,
    "01-scope-method.md": SCOPE,
    "02-interfaces-lifecycle.md": INTERFACES,
    "03-core-loop.md": CORE_LOOP,
    "04-context-memory-compaction.md": CONTEXT,
    "05-models-tools-extensions.md": TOOLS,
    "06-permissions-sandbox-workspace.md": SECURITY,
    "07-subagents-delegation.md": SUBAGENTS,
    "08-sessions-persistence-recovery.md": PERSISTENCE,
    "09-observability.md": OBSERVABILITY,
    "10-design-decisions.md": DECISIONS,
    "11-runtime-experiments.md": EXPERIMENTS,
    "12-failure-modes-open-questions.md": FAILURES,
    "13-coverage-reproducibility.md": REPRO,
    "quality-comparison-2604.14228.md": QUALITY_COMPARISON,
}


def build_claim_index() -> str:
    claims = [json.loads(line) for line in (ROOT / "evidence" / "claims.jsonl").read_text(encoding="utf-8").splitlines() if line]
    rows = [
        "# Claim Index",
        "",
        "| Claim | Statement | Confidence | Evidence | Coverage |",
        "|---|---|---|---|---|",
    ]
    for item in claims:
        statement = item["statement"].replace("|", "\\|")
        rows.append(
            f"| `{item['id']}` | {statement} | {item['confidence']} | "
            f"{', '.join(f'`{value}`' for value in item['evidence_ids'])} | "
            f"{', '.join(f'`{value}`' for value in item['coverage_refs'])} |"
        )
    rows.extend(
        [
            "",
            "Each claim's falsification test and conditions are stored in `../evidence/claims.jsonl`. Figure-to-evidence mappings are stored in `../diagrams/metadata.json`.",
            "",
        ]
    )
    return "\n".join(rows)


def main() -> int:
    REPORT.mkdir(parents=True, exist_ok=True)
    for name, content in REPORTS.items():
        (REPORT / name).write_text(content.strip() + "\n", encoding="utf-8")
    (REPORT / "claim-index.md").write_text(build_claim_index(), encoding="utf-8")
    (ROOT / "runtime-tests.md").write_text(RUNTIME_TESTS.strip() + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
