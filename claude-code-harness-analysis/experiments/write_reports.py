#!/usr/bin/env python3
"""Write the evidence-linked Chinese Claude Code harness report."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "report"
COMMIT = "16a676ffa36eadbfb28eec39007dff73941346b1"
SOURCE = f"https://github.com/IcyFeather233/claude-code/blob/{COMMIT}"


def src(path: str, line: int, label: str | None = None) -> str:
    return f"[{label or path}]({SOURCE}/{path}#L{line})"


GENERATED_FIGURES = {
    "claude-system-overview": "01-system-overview.png",
    "claude-turn-flow": "02-turn-flow.png",
    "claude-context-lifecycle": "03-context-lifecycle.png",
    "claude-tool-surface": "04-tools-extensions.png",
    "claude-permission-pipeline": "05-permission-pipeline.png",
    "claude-subagent-topology": "06-subagent-topology.png",
    "claude-persistence-lifecycle": "07-persistence-lifecycle.png",
    "claude-observability-recovery": "08-observability-recovery.png",
    "claude-layered-architecture": "09-layered-architecture.png",
    "claude-extension-injection": "10-extension-injection-points.png",
    "claude-values-mechanisms": "11-values-principles-mechanisms.png",
}

FIGURE_QUESTIONS = {
    "claude-system-overview": "canonical runtime path 是什么，哪些服务从主线分支？",
    "claude-turn-flow": "一次用户 query 如何跨多个 model request 与 tool call 迭代？",
    "claude-context-lifecycle": "哪些信息在什么时机进入模型，又经过哪些变换？",
    "claude-tool-surface": "能力如何变成模型可见 schema，再变成可执行 action？",
    "claude-permission-pipeline": "工具造成副作用之前经过哪些判断与边界？",
    "claude-subagent-topology": "有哪些 child 机制，它们分别隔离或共享什么？",
    "claude-persistence-lifecycle": "哪些状态 durable，resume/fork 实际恢复什么？",
    "claude-observability-recovery": "模型、工具、重试和退出如何被观测与恢复？",
    "claude-layered-architecture": "Surface、Core、Safety/Action、State 与 Backend 如何依赖？",
    "claude-extension-injection": "MCP、Plugins、Skills、Hooks 分别注入 loop 的哪个语义位置？",
    "claude-values-mechanisms": "first-party 产品立场如何经 analyst principle 映射到源码机制？",
}


def fig(name: str, alt: str) -> str:
    filename = GENERATED_FIGURES[name]
    asset = ROOT / "diagrams" / "generated" / "assets" / filename
    if not asset.is_file():
        return (
            f"> **读者图待生成。** 问题：{FIGURE_QUESTIONS[name]} "
            "evidence-grounded story spec 与 gpt-image-2 prompt 已生成；外部图像 API 尚未获本轮风险授权，"
            "因此当前不嵌入占位图或技术 SVG。"
        )
    image = f"![{alt}](../diagrams/generated/assets/{filename})"
    caption = (
        f"*读者图问题：{FIGURE_QUESTIONS[name]} "
        "这是 gpt-image-2 读者插图；当前实现边均为 static-only，结构化证据与排除项见 "
        "[图片元数据](../diagrams/generated/metadata.json)。*"
    )
    return f"{image}\n\n{caption}"


def tech(name: str) -> str:
    return f"[技术证据图](../diagrams/{name}.svg)"


NOTICE = "> **证据边界。** 本报告分析 source-only commit `16a676f`。其 1,884 个 TS/TSX 文件、关键 symbol 与 feature gates 和论文所述 Claude Code v2.1.88 corpus 强指纹一致，但缺少 package version、上游 tree hash、build manifest，不能视为已证明的 exact 官方 artifact。快照仍有 657 个无法解析的相对 import；除 SiFlow 协议探针外，主循环、安全、session 与 subagent 结论均为 static-only。官方材料只支持产品立场，五价值/十三原则是 analyst synthesis。[X: X-001–X-003] [D: D-001–D-008] [C: C-001, C-024–C-026] 首次遇到缩写或内部名词时，可查 [全局术语表](16-glossary.md)。\n"
GLOSSARY_NOTICE = NOTICE.replace(" 首次遇到缩写或内部名词时，可查 [全局术语表](16-glossary.md)。", "")

REPORTS: dict[str, str] = {}

REPORTS["index.md"] = f"""# Claude Code Harness 架构分析

{NOTICE}

## 核心结论

这个快照恢复出的核心不是一个“收到问题、调用一次模型、执行一个命令”的薄 CLI，而是共享、可递归的 `query()` 控制器。交互 REPL 与 print/SDK 各自准备 session、工具和 context，随后进入同一循环；循环可能在一个用户提交内发起多次 Anthropic Messages 请求，并在每次 `tool_use` 后经过验证、hook、权限、可选 sandbox、执行、`tool_result` 回填后继续。[S: S-004–S-009] [C: C-003–C-005]

{fig("claude-system-overview", "Claude Code 产品边界与 canonical path")}

**图怎么读。** 主线从左到右：界面进入 live session，session 调用 query loop，loop 调 Anthropic Messages，模型提出工具调用，Tool Router 再经过 Permission Gate 到执行后端。`Context Builder`、`Transcript JSONL` 和 `Subagents` 是主线的供给、持久化和递归分支。`Sandbox / Shell` 表示按配置选择 wrapper 后再执行，并不表示 sandbox 永远开启。{tech("system-overview")}

## 定义架构的五个选择

下面只是一页式结论索引；每个选项、替代设计和术语的完整解释位于[设计空间章节](00-design-space-and-running-example.md)。

| 设计问题 | 该快照中的答案 | 主要代价与读者注意 |
|---|---|---|
| 多界面是否共用控制器 | 交互 REPL、`--print`/SDK 等 surface 先各自处理 UI、structured I/O、permission callback 和 live state，然后都消费共享 `query()` generator。 | 核心 loop 语义更一致，但不同 surface 的 approval UI、ESC、中断、排队和输出格式仍不同；不能把“共享 core”读成“所有入口行为完全相同”。 |
| context 如何增长 | Startup、lazy、per-turn、carry-forward 与 durable 来源在每次 model request 前合流，再经过 tool-result budget、snip、microcompact、collapse/autocompact 等变换。 | 这种流水线节省无关 context，但来源、顺序和 compaction survivor 更难追踪；静态分析不能量化摘要损失。 |
| 工具如何受控 | 工具从 registered capability 到 visible schema、requested tool_use、validated dispatch、hook/permission、可选 sandbox 和 backend call，经过多级状态转换。 | canonical tool path 有 gate，不自动证明 startup、hook、MCP lifecycle、bridge/daemon 等副作用面都同等受控；这些仍是审计边界。 |
| child 如何隔离 | Agent child 重建自己的 context、tool pool 与 sidechain transcript；普通 child 默认共享 cwd/files，显式 worktree 才提供工作区隔离。 | “subagent”不是单一 process/isolation 语义，必须分别看 context、policy、workspace、process、cancellation 和 result channel。 |
| 什么是 durable state | Transcript JSONL、sidechain、team inbox、compaction boundary 和部分 metadata 可跨进程恢复；普通 workspace 文件属于外部持久状态。 | Resume/fork 恢复 conversational/session view，不是事务式 rollback；临时 session permission grants 也不会从旧 transcript 静默恢复。 |

{fig("claude-layered-architecture", "Claude Code 五层责任架构")}

**分层不是目录树。** Surface 负责输入与呈现，Core 拥有 query loop 和 compaction 转移，Safety/Action 决定能力是否以及如何执行，State 管理 context 与 durable transcript，Backend 承接 shell、sandbox、workspace 和外部服务。同一源码目录可能同时服务两层；图表达责任和依赖，不声称物理部署隔离。

## 阅读路径

1. [产品立场、设计原则与实现机制](00-values-principles.md)
2. [设计空间与静态 running example](00-design-space-and-running-example.md)
3. [范围、证据和方法](01-scope-and-method.md)
4. [入口与生命周期](02-interfaces-lifecycle.md)
5. [共享核心循环](03-core-loop.md)
6. [Context、memory 与 compaction](04-context-memory-compaction.md)
7. [模型、工具与扩展](05-models-tools-extensions.md)
8. [权限、sandbox 与 workspace](06-permissions-sandbox-workspace.md)
9. [Subagent 与团队协作](07-subagents-delegation.md)
10. [Session、持久化与恢复](08-sessions-persistence-recovery.md)
11. [观测与评估边界](09-observability-evaluation.md)
12. [设计决策与权衡](10-design-decisions.md)
13. [运行实验](11-runtime-experiments.md)
14. [失败模式与开放问题](12-failure-modes.md)
15. [覆盖率与复现](13-coverage-reproducibility.md)
16. [源码与 claim 索引](14-source-claim-index.md)
17. [与 arXiv 2604.14228v2 的对照](15-paper-benchmark.md)
18. [全局术语表](16-glossary.md)

结构化真值位于 [HIR](../hir.json)、[claims](../evidence/claims.jsonl)、[observations](../evidence/observations.jsonl)、[coverage](../evidence/coverage.json) 和 [scenarios](../scenarios/catalog.json)。
"""


REPORTS["00-values-principles.md"] = f"""# 产品立场、设计原则与实现机制

{NOTICE}

{fig("claude-values-mechanisms", "Claude Code 产品立场、分析原则与源码机制")}

## 先区分三层证据

这一章讨论“为什么某些机制值得存在”，因此最容易把作者原话、源码事实和分析者解释混在一起。本报告使用三层：

- **Product stance（D，产品立场）**：Anthropic first-party 材料明确表达的目标或约束，例如让人保留控制权、把 context 当作有限资源、让 memory 可检查。这一层回答“产品希望保护什么”。
- **Analyst principle（I，分析原则）**：分析者观察多份材料和多个源码机制后，为重复出现的设计模式取的名字，例如 `graduated trust`。它回答“这些机制共同体现了什么设计思路”，但不是 Anthropic 官方 taxonomy。
- **Mechanism（S，实现机制）**：固定 commit 中能够定位的控制流、数据结构和配置，例如 deny-first rule order、五阶段 compaction、JSONL sidechain。它回答“代码具体做了什么”。

一条可信解释链应写成 `官方立场 D → 分析原则 I → 源码机制 S`。D 不能直接证明某段源码为何写成当前形状；S 也不能反推出作者真实动机。[C: C-024, C-027]

## 五个产品立场：逐项解释

### 1. Human decision authority：人保留最终决定权

这里的 **authority** 不是说用户亲自批准每一个内部步骤，而是说，当 agent 将要扩大权限、修改文件、执行命令或访问敏感资源时，harness 应保留可识别的用户控制点：可以允许、拒绝、中断，或者要求重新确认。

报告使用的 **principal-aware oversight** 是分析者对 Constitution 相关内容的概括，不是源码中的类名。`principal` 指系统当前应当服务并对其负责的人或组织，例如部署/管理系统的组织以及发起具体任务的用户；`principal-aware` 表示模型需要考虑“谁有权提出这条指令、不同指令之间谁优先”；`oversight` 表示人能够观察、纠正、停止或重新授权。Constitution 是模型层的规范材料，不直接规定 Claude Code 必须有某个 `PermissionGate`。[D: D-001, D-008]

源码中的对应点是：默认权限路径区分 deny/ask/allow；用户可以中断 query；`bypassPermissions` 必须显式选择；resume/fork 不会把旧 session 的临时授权当作永久授权恢复。[S: S-023, S-024, S-044]

### 2. Safety, security, privacy：不仅防误操作，也限制可达范围

这三个词在这里不完全相同。**Safety** 关注 agent 诚实但做错事，例如命令范围过大；**security** 关注恶意输入、prompt injection 或绕过策略；**privacy** 关注代码、路径、prompt 和 telemetry 是否被不必要地发送或记录。官方 auto-mode 材料还把风险分成过度积极行为、普通错误、prompt injection 和更严重的不一致行为，并指出高频 approval 会产生 **approval fatigue**：用户因提示太多而机械点击允许。[D: D-003]

源码不是靠一个“安全开关”处理这些风险，而是叠加 tool 输入检查、deny/ask/allow rules、mode、classifier、hooks、可选 sandbox、telemetry redaction 和 resume 后重新建立 permission context。重要边界是：本报告只证明 canonical tool path 的这些层，尚未证明进程内所有 startup/hook/MCP 副作用都经过同一管线。[S: S-023–S-028, S-038–S-044] [C: C-014]

### 3. Reliable execution：任务结果可验证，失败路径有收束

**Reliable** 不是“模型永远回答正确”，而是 harness 尽量把一次长任务变成可检查、可恢复、不会轻易破坏协议的执行过程。官方材料建议给 agent 可验证的 outcome；源码则让同一 query loop 负责工具结果回填、provider retry、context overflow recovery、停止条件和有界 shutdown。[D: D-002, D-005] [S: S-006–S-009, S-014, S-018, S-041]

例如，工具失败通常不会让 Messages 协议留下孤立的 `tool_use`：harness 会构造模型可消费的 error/result；中断时也会补 interruption result。这里的可靠性更接近“状态机能到达明确终态”，而不是“每次业务结果都成功”。

### 4. Capability amplification：扩大模型能完成的工作范围

**Capability amplification** 指 harness 把只会生成文本的模型连接到文件、shell、MCP、skills 和 subagents，使模型可以观察环境、采取行动并验证结果。**Operational surface** 指这些可被模型或 harness 触达的操作面总和，包括模型可见 tool schema、实际 dispatcher、外部 MCP server、workspace 与 child agent。[D: D-002, D-005]

源码通过 streaming/concurrent tools、provider fallback、动态 MCP tools、skills、plugins 和 AgentTool 扩大能力面；但“能力存在”不等于“这一轮模型可见”，更不等于“已经获得权限执行”。能力扩大与治理边界必须同时描述。[S: S-009, S-016–S-020, S-032]

### 5. Contextual adaptability：根据项目、阶段和任务调整模型所见信息

这里的 **contextual** 不是只指模型 context window 的长度，而是指“当前这一轮应该让模型看到哪些信息”。同一个 harness 会因项目目录、CLAUDE.md、用户 memory、当前工具、MCP 连接、agent role、任务阶段和刚发生的 tool result 而构造不同 request。

官方 context/memory/team 材料分别描述 progressive disclosure、可编辑的 CLAUDE.md 与 auto memory、以及 teammate 的独立 context。源码对应多层 CLAUDE.md/rules、lazy attachments、skills/MCP delta、agent definition 和 sidechain transcript。其收益是只在需要时加入信息，代价是来源顺序、生命周期和 compaction 后保留内容更难推理。[D: D-005–D-007] [S: S-012, S-013, S-020, S-033]

## 十三条分析原则：按主题解释

### 权限与风险

- **Deny-first with escalation（拒绝优先，必要时升级）**：规则冲突时先尊重 deny；没有足够依据自动允许时，根据 mode 进入 ask 或 deny，而不是把“未匹配”默认为安全。`escalation` 指把决定升级给用户或更严格策略，不是提高进程权限。[S: S-023–S-024]
- **Graduated trust（分级信任）**：autonomy 不是开/关二值。`default`、`acceptEdits`、`dontAsk`、`plan`、`bypassPermissions` 代表不同信任级别，`auto` 还受 feature gate 限制；每一档改变的是哪些动作可以自动决定、哪些仍必须拒绝或询问。[S: S-023, S-044]
- **Defense in depth（纵深防御）**：假设任一层都可能遗漏，因此把 input check、rules、mode、classifier、hooks、sandbox 和授权 freshness 叠加。多层不表示没有缝隙；C-014 正是对 canonical path 外副作用的开放审计。[S: S-019, S-023–S-028, S-044]
- **Externalized programmable policy（外置、可编程策略）**：一部分治理不写死在 tool 实现中，而由 settings、managed policy 和 hook events 配置。这样组织可以施加规则，但也引入配置优先级和 hook 副作用。[S: S-023, S-024, S-043]
- **Reversibility-weighted risk（按可逆性分配风险预算）**：读取、编辑、执行远程命令和删除文件的恢复成本不同，因此不应使用完全相同的并发、permission 和 workspace 策略。worktree/file rewind 提供有限可逆性，但不是事务式回滚。[S: S-009, S-023, S-031, S-035]

### Context 与持久状态

- **Progressive context management（渐进式 context 管理）**：先使用成本较低、损失较小的处理，再在压力继续上升时 snip、microcompact、collapse 或生成摘要。它不是达到阈值后一次性清空历史。[S: S-014–S-015]
- **Append-oriented durable state（面向追加的持久状态）**：重要事件主要追加到 JSONL，并通过 `parentUuid`、boundary 和 sidechain 解释逻辑关系；这与每次覆盖一份完整 session snapshot 不同。追加日志更易审计，恢复时却需要重建链和处理损坏记录。[S: S-029, S-037]
- **Transparent file-based memory（透明的文件式 memory）**：CLAUDE.md 和 auto-memory 文件可以由用户检查和编辑，不是只存在于不可见数据库。它们保存可复用知识；transcript JSONL 则保存执行历史，两者不能混为一类 memory。[D: D-006] [S: S-012, S-029]

### 控制循环与恢复

- **Minimal decision scaffolding（最小决策脚手架）**：harness 没有用一个庞大的固定 planner 预先决定所有步骤，而是让模型在 query loop 中根据最新结果继续选择 action；确定性的基础设施负责 schema、permission、状态和停止条件。`minimal` 描述决策层，不表示代码量很少。[S: S-006–S-009] [I: I-005]
- **Judgment plus guardrails（判断加护栏）**：CLAUDE.md、skills 和 system prompt 提供软指导；permission、sandbox 和 schema validation 提供确定性限制。软指导帮助模型作判断，但不能代替执行边界。[S: S-012–S-013, S-023–S-027]
- **Graceful recovery（有界恢复）**：错误先尝试 retry、fallback、compaction 或 interruption cleanup；只有无法恢复时才终止。`graceful` 不表示无限重试，而是恢复次数和 shutdown 时间都有上限。[S: S-008, S-014, S-018, S-041]

### 扩展与委派

- **Composable extensibility（可组合扩展）**：MCP、Plugins、Skills、Hooks 不是同一个 plugin API 的四种名字；它们分别改变 tool surface、打包分发、context 和 lifecycle/authorization，可以组合但有不同成本与信任边界。[S: S-020, S-043, S-046]
- **Isolated delegation context（隔离的委派 context）**：child 不直接继承完整 parent message history，而是重新构建 context/tool/MCP，并用 sidechain 保存自己的 transcript，最后返回摘要或结果。这里的隔离主要是 context/transcript；普通 child 仍可能共享 cwd 和文件。[S: S-032–S-033, S-045]

## 速查映射

| 产品立场 | 最相关的分析原则 | 代表性源码机制 | 不能推出什么 |
|---|---|---|---|
| Human decision authority | deny-first 与 graduated trust：不同风险动作需要不同默认决策，并在无法自动判断时升级到 ask 或 deny。 | Permission rules、interrupt、`bypassPermissions` 显式选择、resume 后重新建立 permission context。 | 不能推出每个内部步骤都弹窗，也不能推出旧 session 的临时授权会被恢复。 |
| Safety/security/privacy | defense in depth 与 externalized policy：把 input check、rules、mode、classifier、hooks、sandbox 和 redaction 分层组合。 | Classifier、hooks、sandbox adapter、telemetry redaction、managed/user/project policy。 | 不能推出 canonical path 外的 startup、hook、MCP lifecycle 副作用都已经 runtime-verified。 |
| Reliable execution | graceful recovery 与 minimal decision scaffolding：让模型继续做判断，harness 负责协议、状态、恢复和停止。 | Query loop、tool_result 回填、provider retry/fallback、context recovery、graceful shutdown。 | 不能推出业务结果一定正确；它主要说明状态机如何到达明确终态。 |
| Capability amplification | composable extensibility 与 reversibility-weighted risk：扩展能力面时按副作用和可逆性分配治理强度。 | Built-in tools、MCP、plugins、skills、AgentTool、worktree/file rewind。 | 不能把能力存在、模型可见、获准执行和被 sandbox 隔离合并成一个事实。 |
| Contextual adaptability | progressive context、transparent memory 与 isolated delegation：按任务阶段和来源调节模型可见信息。 | CLAUDE.md、attachments、skills/MCP delta、sidechains、agent-specific context。 | 不能推出 context 变化无损；compaction survivor 和 provenance 仍需实验验证。 |

## First-party 材料索引

- [Safe and trustworthy agents](https://www.anthropic.com/news/our-framework-for-developing-safe-and-trustworthy-agents)：human control、read-only default 与 approval boundary。[D-001]
- [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)：agentic loop 与 verifiable outcomes。[D-002]
- [Claude Code auto mode](https://www.anthropic.com/engineering/claude-code-auto-mode) / [sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing)：approval fatigue、威胁分类与 FS/network isolation。[D-003–D-004]
- [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) / [memory](https://code.claude.com/docs/en/memory)：context scarcity、progressive disclosure、compaction、CLAUDE.md 与 auto memory。[D-005–D-006]
- [Agent teams](https://code.claude.com/docs/en/agent-teams) / [Claude's Constitution](https://www.anthropic.com/constitution)：independent teammate contexts 与 principal-aware oversight；后者是 model-level stance，不是 harness ADR。[D-007–D-008]

## 不能由这些映射推出什么

同一机制可以服务多个产品立场，箭头不是一一因果关系。官方材料没有把这十三条命名成 Claude Code 的正式原则；因此它们保持 I evidence。要验证它们是否为 Claude Code 特有，还需要用同一 codebook 对其他 harness 独立编码。[I: I-003, I-005]
"""


REPORTS["00-design-space-and-running-example.md"] = f"""# 设计空间与静态 Running Example

{NOTICE}

## 六个设计问题

这一节先解释每个问题的两个端点，再说明 Claude Code 快照实际落在哪里。最后的表格只是速查摘要；第一次阅读时应先看六个小节。

### 1. 界面与 loop 是一套系统，还是每个界面各有一套？

这里的 **界面（surface）** 指用户或外部程序进入 harness 的方式，例如交互式 REPL、`--print`、SDK、server 或 bridge；**core loop** 指把 messages 发给模型、处理 `tool_use`、执行工具、回填 `tool_result` 并判断停止的控制器。

一种设计是“每个界面拥有独立 controller”：REPL 有自己的循环，SDK 另写一套，server 再写一套。优点是每个入口可以高度定制；缺点是 stop condition、tool error 和 permission 语义容易随时间漂移。该快照选择“薄适配器 + 共享 `query()`”：REPL 的 QueryGuard 和 headless QueryEngine 分别准备 UI state、structured I/O、context 与 tools，随后消费同一个 async generator。[S: S-004–S-006] [C: C-002–C-004]

“共享 loop”不等于所有入口行为相同。交互入口能显示 approval dialog、接收 ESC 和增量渲染；headless 入口必须用非交互策略表达同一决定。因此共享的是模型/工具状态机，不是整个产品体验。

### 2. Context 是每轮完整快照，还是按生命周期合流的流水线？

**快照式 context** 可以理解为：每次模型请求前，从一个 canonical state 重新收集所有规则、memory、history 和工具说明，拼成一份完整且自包含的 prompt。它的优点是单次 request 容易解释；代价是重复加载大量不变内容，也不容易利用 lazy loading 或 provider cache。

**流水线式 context** 则把信息按“什么时候产生、要保留多久、何时才需要”分开。Claude Code 更接近流水线：

- **startup**：session 建立或 reload 时准备的基础信息，例如 system prompt、初始工具/mode guidance、启动时发现的 CLAUDE.md；它不是每个 token chunk 都重新发现一次。
- **lazy**：先只保留可发现性，真正需要时再加载的内容，例如进入某目录后适用的 instructions、被选择的 skill、后来连接的 MCP/agent/tool delta。`lazy` 说的是加载时机，不表示内容不重要。
- **per-turn**：只与当前用户提交或当前 iteration 有关的信息，例如本轮输入、queued messages、diagnostics、task/agent notification 和刚完成的 tool result。
- **carry-forward**：已经进入当前 message chain，并自然随下一次 model request 继续携带的 user/assistant/tool blocks。它描述“在这次 live conversation 中继续带着走”。
- **durable**：写到进程外持久介质、重启后仍可能恢复的信息，例如 transcript JSONL、CLAUDE.md 和部分 memory。durable 描述存储寿命，不保证下一轮一定进入模型。

这些维度可以重叠：一条 tool result 先是 per-turn，写入 message chain 后成为 carry-forward，若 transcript flush 成功还会成为 durable history。一次具体请求大致经历“startup baseline + 当前 history projection + lazy delta + per-turn attachment → token/compaction 变换 → model request”。这种设计减少无关 context 和重复成本，却让 provenance（每段信息来自哪里）、顺序和 compaction survivor 更难理解。[S: S-010–S-015] [C: C-006–C-007]

### 3. Tool registry 是否就等于模型这一轮能调用的工具？

**Registry** 只是“harness 已经知道哪些 capability”的集合。一个工具从代码存在到真正产生副作用，至少经过：安装/配置 → 注册进候选池 → 按 mode/feature/deny 过滤 → 转成这一轮模型可见 schema → 模型实际发出 `tool_use` → router 查找并验证 → permission 决定 → 可选 sandbox → 执行。

因此 `registered`、`visible`、`requested`、`authorized` 和 `executed` 是不同状态。例如 MCP server 已连接并不保证其所有 tools 都暴露；skill 被发现不等于它是 executable tool；模型看见 Bash schema 也不表示当前命令会被允许。[S: S-019–S-022] [C: C-010–C-011]

替代方案是固定一组工具并每轮全部发送，分析更简单，但 schema token 成本高，也无法自然表达 plugin、MCP、mode 与 deferred discovery。当前分层机制更灵活，代价是安全审计不能只看 registry。

### 4. Approval 与 isolation 是同一件事吗？

**Approval/permission** 回答“这项动作在当前规则和 mode 下是否允许”：结果可以是 allow、deny 或 ask。**Isolation/sandbox** 回答“如果允许，动作在怎样的文件系统、网络和进程边界内执行”。前者是政策决定，后者是执行环境约束。

四种组合都可能有意义：deny 时不应执行；allow + sandbox 表示允许但限制影响范围；allow + no sandbox 表示在宿主边界直接执行；ask + sandbox 表示先取得人类决定，再以受限环境执行。Claude Code 的 canonical Bash 路径先 permission，再根据配置决定是否包 sandbox wrapper。[S: S-023–S-027] [C: C-012–C-014]

另一种系统可以强制所有动作进 sandbox、从不弹窗；也可以只依赖 approval、不提供 OS isolation。Claude Code 将两层分开，部署更灵活，但读者很容易把“用户点了允许”误读为“这条命令已经隔离”。

### 5. Child agent 到底共享什么、隔离什么？

“Subagent 有独立 context”只回答一个维度。完整边界至少包括：模型消息/context、tool pool、permission rule、transcript、workspace/files、process/backend、cancellation 和结果通道。

普通 Agent child 会重新构建 system/user context、tools、MCP 和 sidechain transcript，因此不会把 parent 的完整 message history 原样塞进去；但默认仍在同一 cwd/files 上工作。async child 有独立 abort controller，不自动随主请求 ESC 结束；显式 worktree child 才获得独立 git worktree；swarm teammate 又可能由 in-process backend 或 terminal pane 承载。[S: S-032–S-037] [C: C-017–C-020]

替代方案是每个 child 强制独立 process/container/worktree。那会减少文件竞争和污染，但同步 artifacts、启动成本和清理都更复杂。当前选择偏向低成本协作，把强 workspace isolation 作为显式选项。

### 6. Resume 是恢复会话，还是回滚整个世界？

**Resume** 恢复的是 conversational/session state：根据 JSONL、`parentUuid` 和 metadata 重建 messages、session identity、部分 agent/worktree/todo 状态。**Rollback** 则意味着外部世界也回到旧时刻，例如把普通 workspace 文件、已启动进程和远程副作用恢复到 checkpoint。

该快照只支持前一种语义。用户在上次 session 中写过的文件通常仍留在 cwd；resume 不会自动撤销。`--fork-session` 创建新的 session identity 并复制可恢复 history，也不是 git branch。CLI 的 file-history rewind 是另一个显式、范围有限的机制，恰好说明 session restore 不是事务式 workspace snapshot。[S: S-029–S-031, S-044] [C: C-015–C-016, C-029]

替代设计可以把每个 turn 放在 **copy-on-write workspace**（未修改数据共享底层副本，首次写入时才创建私有副本）或 **VM checkpoint**（保存虚拟机磁盘/内存状态）中，实现会话与文件一起回退；代价是存储、外部服务一致性和长期 CLI 工作流都会更复杂。

## 六个问题速查

| 问题 | Claude Code 的选择 | 主要替代方案 | 权衡与边界 | 证据 |
|---|---|---|---|---|
| 多入口如何复用 core | Surface 先各自适配 UI、structured I/O、permission callback 和 live state，再共用 `query()`。 | 每个入口维护独立 controller，各自实现 tool loop、stop 和 recovery。 | 共享 core 降低语义漂移；代价是 REPL/headless 的 state、approval 和输出差异必须靠 adapter 处理，不能假设行为完全相同。 | C-002–C-004 |
| context 如何构造 | Startup、lazy、per-turn、carry-forward、durable 来源合流，再经过有序 shaping/compaction。 | 每轮从 canonical store 重建一份完整 prompt snapshot。 | 节省 token 和重复加载，但 provenance、stage 顺序、survivor 和摘要损失更难审计。 | C-006–C-007 |
| 工具何时可执行 | Capability 依次经历 registered、eligible、visible schema、requested、validated、authorized、executed。 | 固定工具全集每轮直接发给模型并按名称 dispatch。 | 动态 MCP/skill/plugin 能力更灵活；审计时不能只看 registry，必须说明证明到哪一级。 | C-010–C-011 |
| 是否允许与如何隔离 | Permission 先回答 allow/ask/deny；若允许，Bash 等路径再按配置选择 sandbox wrapper。 | 所有动作强制 sandbox，或完全只靠人类 approval。 | 两层可组合，部署灵活；但 allow 不等于 isolated，sandbox 也不是 rollback。 | C-012–C-014 |
| child 的隔离边界 | Child 重建 context 和 sidechain transcript；普通 child 默认共享 cwd/files，worktree 是显式隔离选项。 | 每个 child 强制独立 process、container 或 worktree。 | 协作和 artifact 共享成本低；代价是文件竞争、policy prompt owner 和 cancellation 需要逐维验证。 | C-017–C-020 |
| resume 恢复什么 | 从 JSONL、parentUuid 和 metadata 恢复会话 view，不回滚普通 workspace 文件，也不恢复临时 grants。 | 为每个 turn 建立事务式 workspace checkpoint 或 VM snapshot。 | 符合 CLI 长任务习惯、存储成本低；不能当作撤销或安全回滚机制。 | C-015–C-016 |

收益、代价和替代方案均是分析者综合，不是作者动机。[D: D-001–D-008] [I: I-003, I-005] [C: C-024, C-027]

## 静态 running example：一次需要工具的用户提交

{fig("claude-turn-flow", "一次 query 的模型工具循环")}

1. REPL 的 **QueryGuard** 先取得当前主 query 的执行权，防止两个主 query 同时修改 live state；headless 模式则由 **QueryEngine** 建立等价的 structured I/O 上下文。两者最终调用共享 `query()`。[S: S-004–S-006]
2. `queryLoop` 先投影当前 message chain，处理 tool-result budget、可选 snip/microcompact/collapse/autocompact 和 hard limit，再构造一次 Anthropic Messages request。[S: S-007, S-014]
3. 模型 streaming response 中若出现 `tool_use` block，router 用 tool name 查找当前 pool，验证 schema/input，运行 pre-tool hook，再请求 permission decision。[S: S-022–S-024]
4. 允许后，Bash 等工具可能先套 sandbox wrapper，再由 Shell spawn；拒绝或验证失败时不会静默丢弃，而是生成模型可消费的 error `tool_result`。[S: S-025–S-027]
5. `tool_result` 与 runtime attachments 被追加到 message chain，触发同一用户 query 的下一次 iteration。没有 tool call、达到 max turns、hook stop、abort 或不可恢复错误时，`query()` 才到 terminal transition。[S: S-008–S-009]

**Model Stream** 是一次 API request 的流式返回；**Continue Loop** 是同一用户提交中的下一次 agentic iteration；**Stop** 是当前 `query()` 的终态；**Session** 则可以横跨多个用户提交。这个例子是源码路径演练，不是 runtime trace。{tech("turn-flow")}

不能由此推出：external bundle 包含所有 feature path、真实模型一定选择某工具、permission denied 的 OS 层绝无副作用，或该路径在生产中的出现频率。
"""


REPORTS["01-scope-and-method.md"] = f"""# 范围、证据与方法

{NOTICE}

## 冻结对象

| 字段 | 值 |
|---|---|
| 本地仓库 | /volume/med/work/users/mzchen/work/claude-code |
| remote | https://github.com/IcyFeather233/claude-code.git |
| commit | {COMMIT} |
| branch / dirty / tag | main / clean / 无 tag |
| 目标身份 | source-only public mirror；与论文 v2.1.88 corpus 强指纹一致，exact artifact 未证明 |
| README | 按用户要求，不把人为 README 架构叙述作为证据 |

分析按 14 个 module 深读入口、loop、context、compaction、provider、tools、permission、sandbox、workspace、session、subagent、orchestration、observability 和 recovery。重要结论先写 claim，再关联 evidence，最后投影到 HIR 与图。

## 证据记录中的缩写

- **Claim（C）**：报告希望成立、并且能被反例推翻的一条明确结论。claim 必须列 supporting evidence、confidence、coverage 和 falsification test。
- **Documented evidence（D）**：first-party 文档、ADR 或作者声明，可支持产品目标和公开意图，但不能单独证明当前 commit 的控制流。
- **Static evidence（S）**：固定源码、配置和 schema 中能定位的结构或潜在路径。S 能证明代码存在，不证明当前 build 可达或生产中常走。
- **Runtime observation（R）**：真实 target harness 某次执行产生的 trace。R 证明路径至少发生过一次，不证明所有配置都如此。
- **Controlled experiment（X）**：为区分某个 claim 专门设计的探针、scripted run 或 fault injection。本报告的 provider probe 和 corpus fingerprint 属于 X，但前者绕过了 target loop。
- **Inference（I）**：分析者根据多条 D/S/R/X 得出的设计归纳或风险解释，不能伪装成作者原话。
- **HIR（Harness Intermediate Representation）**：把 agent loop、context、tools、policy、state 和 delegation 表成 typed nodes/edges 的机器可读模型；正文和图是它的投影视图。
- **Coverage**：这条结论检查了哪些目录、入口、配置和场景。`not found` 只有在 coverage 足够明确时才能接近“没有”。

本轮没有 target R，因为 Claude Code 快照未能启动。论文只作为 prior-analysis benchmark 和反例线索，不直接作为实现真值。[C: C-024–C-026]

## 版本指纹，而不是版本猜测

本快照有 1,884 个 TS/TSX 与 18 个 JS/JSX 文件。论文明确报告 v2.1.88 corpus 有 1,884 个 TypeScript 文件；本地还命中同一批高辨识度符号和 feature gates，包括 `HISTORY_SNIP`、`CACHED_MICROCOMPACT`、`CONTEXT_COLLAPSE`、`TRANSCRIPT_CLASSIFIER` 与 `MAX_OUTPUT_TOKENS_RECOVERY_LIMIT=3`。[X: X-003] [C: C-026]

这构成 **strong fingerprint match**，但缺少 package version、上游 tree hash、lockfile/build manifest，不能升级为 exact match。分析对象因此仍固定为 commit，而不是把论文版本号写进源码事实。

## 可运行性安全门

scan_snapshot.py 在 1,902 个 TS/JS 文件中发现 12,958 个相对 import，其中 657 个目标缺失；顶层没有 package manifest、lockfile 或 tsconfig。这不是只安装 Bun 即可修复的缺口：依赖图和 feature() 构建值都不完整。[X: X-001]

SiFlow 探针确认 endpoint 可用：Anthropic /v1/messages、SSE、强制 tool use 都是 HTTP 200；关闭默认 thinking 后得到 echo({{text: hello}})。它排除了 provider 基础方言不兼容，却不能补全快照。[X: X-002]

## 有效性威胁

- 无 tag/package manifest，虽然与 v2.1.88 corpus 强指纹一致，仍不能证明 exact artifact identity。
- feature() 是编译时 DCE；源码存在不等于 external bundle 存在。
- loop、安全、resume、child 均无 target runtime evidence。
- 缺失文件既有 type-only 也有实际模块，不能整体忽略。
- 源码注释只能解释局部机制，不能自动升级为产品动机。

复现材料：[manifest](../manifest.json)、[完整性扫描](../experiments/snapshot-integrity.json)、[provider probe](../experiments/provider-probe.json)、[coverage](../evidence/coverage.json)。
"""

REPORTS["02-interfaces-lifecycle.md"] = f"""# 接口与生命周期

{NOTICE}

{src("src/entrypoints/cli.tsx", 33, "CLI bootstrap")} 先处理 --version 和 feature-gated fast path，其余才加载 {src("src/main.tsx", 585, "Commander main")}。main 再区分 interactive、--print/SDK、server、remote/bridge、MCP 与条件子命令。[S: S-002–S-003]

## 先理解 surface、adapter 和 core

- **Bootstrap** 是进程刚启动时的最小分发层：解析少量参数，处理无需完整应用初始化的 fast path，再决定是否加载 main。它不等于 agent loop。
- **Surface** 是输入/输出产品界面。REPL（Read-Eval-Print Loop）面向人在终端中连续交互；`--print`/SDK（Software Development Kit）面向脚本和调用方；server/bridge/MCP 子命令面向其他协议。
- **Adapter** 把某个 surface 的状态转换成 core 能理解的 messages、tools、permission callback 和 event consumer。共享 core 不要求 UI、输出格式或 approval 交互相同。
- **AppState** 是交互进程中的 live mutable state，包括当前 messages、tool permission context、tasks、agents 等；它不是 durable transcript 本身。
- **QueryGuard** 是 REPL 的并发入口保护，确保一个主 query 获得执行权，后来的输入排队或作为附件处理。
- **QueryEngine** 是 headless/SDK 侧的 controller。`headless` 表示没有交互式终端 UI；`structured I/O` 表示用机器可解析的记录而不是屏幕文本交换事件。QueryEngine 负责这种 I/O、非交互 permission 语义和调用共享 `query()`。

| 表面 | 主要对象 | 进入 core 前准备什么 | 读者注意 |
|---|---|---|---|
| Interactive REPL | React/Ink UI、AppState、QueryGuard | 维护终端渲染、输入队列、ESC/abort、approval dialog 和 live task/agent state，然后由 `onQueryImpl` 调用共享 `query()`。 | 共享的是 model/tool 状态机，不是 UI 行为；REPL 能做人类交互，headless 入口不一定能。 |
| Print / SDK | QueryEngine、structured I/O event consumer | 把机器输入转成 messages/attachments，以 JSON/event records 输出进度，并为非交互场景提供 permission 决策路径。 | 它消费同一 `query()`，但 approval、错误呈现和 backpressure 与 REPL 不同。 |
| MCP/server/bridge | 协议 runner、子命令 handler | 先处理协议握手、server lifecycle 或 bridge/remote 子命令；只有进入 agent execution 的分支才会触达主 loop。 | 不能把“同一 binary 里有 server/MCP 代码”直接解释成所有协议请求都走 canonical query path。 |
| Resume/fork | sessionRestore、sessionStorage、metadata loader | 先从 JSONL、parentUuid 和 metadata 重建 live session view，再按当前 settings/CLI 重新建立运行上下文。 | 恢复会话不等于回滚 workspace，也不从旧 transcript 恢复临时 permission grants。 |

## Session、query、iteration 与 API request

- **Session**：跨多个用户提交的容器，有 session ID、live state，并可对应 transcript JSONL。[S: S-029–S-031]
- **一次用户 query**：提交输入到这次 query() terminal transition。QueryGuard 防止两个主 query 同时运行，新消息可排队。[S: S-004]
- **Agentic loop iteration**：queryLoop 的一次 while(true)，通常取样一次、可能执行一组工具，再决定继续或 terminal。[S: S-006–S-008]
- **API request / model round**：对 Anthropic Messages 的一次请求。一个用户 query 可因工具回填、retry、fallback 或 recovery 含多个 request。[S: S-007, S-017–S-018]

所以“一个 turn 调几次模型”必须先定义 turn。本报告固定使用上述四个词。

一个具体包含关系可以写成：`一个 Session` 包含多次 `用户 query`；一次 query 包含一到多次 `loop iteration`；一次 iteration 通常包含一次 `model API request`，还可能执行零到多个 tool calls。provider retry 可能让一次 iteration 内出现额外 request，因此这不是严格的一对一数学关系。

## 从进程启动到一次提交结束

1. **Bootstrap** 选择入口，只加载当前 mode 需要的模块。
2. **Main initialization** 读取 settings、permission mode、provider、plugins/MCP、session metadata，并建立 surface state。
3. **Surface intake** 把用户文本或 structured input 转成 messages/attachments；REPL 还处理队列、ESC 和渲染。
4. **Query execution** 进入共享 `query()`，在 model request 与 tool execution 之间循环。
5. **Persistence** 把 message/tool chain 追加到 transcript；这一步使部分 live state 变成 durable state。
6. **Terminal/next input** 当前 query 返回，但 session 可以继续接收下一次提交；收到 signal 时则转入 graceful shutdown。

--print 会跳过 workspace trust dialog，且 non-interactive 场景无法使用普通 UI approval；共用 loop 不表示治理体验完全相同。[S: S-003, S-024]
"""

REPORTS["03-core-loop.md"] = f"""# 共享核心循环

{NOTICE}

{fig("claude-turn-flow", "Claude Code query loop")}

{src("src/query.ts", 219, "query/queryLoop")} 初始化 messages、tool context、compaction tracking、recovery counters、stop-hook state、turnCount 和 transition，再进入 while(true)。[S: S-006]

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

该表是从 {src("src/query.ts", 219, "query.ts")} 的真实源码顺序恢复，不是把论文中的视觉顺序反写成事实。[S: S-006–S-009, S-014] [C: C-004, C-007]

## 九个阶段中的几个容易误解的词

**State snapshot** 不是把整个 session 写成磁盘快照，而是在本轮开始时读取当前 live messages、tool context、turn count 和 recovery counters，形成这一轮决策所使用的状态视图。随后这些 live objects 仍可能被 tool result 或 attachment 更新。

**Boundary projection** 是从 durable/live history 中选择“当前 request 仍然有效的 message chain”。compaction boundary 之前的原始消息可能被 summary 代表，因此 projection 不等于简单取 JSONL 的全部行。

**Stream consumption** 表示 Anthropic Messages response 是逐块到达的。`AsyncGenerator` 让 query loop 可以一边收到 provider event，一边向 REPL/SDK yield 进度；但 UI event 不会自动成为下一次模型 message，只有经过 message/result 组装的内容才会回填。

**Streaming-safe tool** 可以在模型尚未完全结束输出时提前启动；**concurrency-safe tool** 可以与相邻的同类 tool call 并发执行。这两个属性不同。并发完成顺序也不等于模型 block 顺序，因此 **ordered reconciliation** 会按原 `tool_use` 顺序合并 results/context modifiers。

**Transition** 是 loop 对下一步的显式决定：continue、stop、recover 或 abort。`terminal` 只表示当前 query 结束，不表示进程退出或 session 被删除。

`query()`/`queryLoop()` 是 `AsyncGenerator`：它同时承载流式 UI 输出、model/tool events 和 terminal result；因此“流向界面的 event”与“写回下一轮模型的 message”是两个不同通道。Loop 以实际 `tool_use` blocks 决定 follow-up，而不只相信 stop_reason。[S: S-006–S-008]

并行也不是“所有工具一起跑”：连续 concurrency-safe calls 形成有上限批次，不安全工具串行；同批某些失败会取消 sibling，但结果与 context modifier 仍按原 block 顺序归并，避免执行完成顺序污染模型协议。[S: S-009, S-022]

unknown/schema/permission error 通常变为 model-facing tool_result；provider 失败由 retry 层处理；context overflow 可触发 reactive compaction；abort 会补 interruption result，避免协议悬空。这些均为 static-only。{tech("turn-flow")}
"""



REPORTS["04-context-memory-compaction.md"] = f"""# Context、Memory 与 Compaction

{NOTICE}

{fig("claude-context-lifecycle", "Claude Code context lifecycle")}

## 生命周期词典：何时进入、保留多久、是否可恢复

Context 来源不能只按“内容是什么”分类，还要同时回答三个问题：什么时候加载、会携带多久、进程重启后能否恢复。

- **Startup**：建立 session 或 reload 时计算的基线，例如 system prompt 的稳定部分、启动时可见的 project instructions。它可能在配置变化后重算，所以不是“进程一生永不变化”。
- **Lazy**：先记录可发现性，只有任务触发时才加载完整内容。例如 skill 只有被选中时才把详细 instruction 带入 context；目录规则可能在访问对应路径后出现。
- **Per-turn**：为当前用户提交或当前 iteration 生成，例如 diagnostics、task notification、queued input 和最新 tool result。下一轮是否继续携带取决于它是否被写入 message chain。
- **Carry-forward**：已经进入 live message chain，并继续出现在后续 model request 中，直到被 boundary projection、snip 或 compaction 替换。
- **Durable**：已经写到 JSONL 或文件，进程退出后仍存在。durable 不代表模型每轮都看到它；resume 时仍要经过恢复和 context selection。

例如 Bash 的输出最初是 per-turn tool result；追加到 messages 后成为 carry-forward；transcript flush 后又具有 durable copy；之后 microcompact 或 summary boundary 可能只保留 preview/摘要。生命周期是可叠加状态，不是互斥标签。

| 图中标签 | 生命周期 | 典型内容 | 读者注意 |
|---|---|---|---|
| System Prompt | startup/reload，部分 section 会随 mode、tool set 或配置重算。 | tone、task policy、tool/mode guidance、稳定环境说明。 | 它是 provider request 中高优先级内容，不等于项目 memory，也不代表每个 section 永久不变。 |
| CLAUDE.md + Rules | startup 与 lazy 混合；全局/项目规则可启动时加载，目录或 include 规则可能按需出现。 | managed/user/project/local 层级、目录规则、`@include`、add-dir。 | 它是可维护 instruction 来源，不是 transcript；include 还可能触发额外 approval。 |
| History JSONL | durable copy 与 carry-forward view 并存；resume 时再投影当前分支。 | user/assistant/tool chain、parentUuid、compact boundary、summary segment。 | JSONL 保存发生过的记录，模型本轮看到的是经过 selection/projection/compaction 后的 view。 |
| Runtime Attachments | per-turn 或 per-iteration 产生，部分写入消息链后变成 carry-forward。 | MCP/agent delta、skills、memory、tasks、diagnostics、queue、tool result preview。 | Attachment 不是用户原文；是否进入下一轮取决于 message assembly、预算和压缩处理。 |

{src("src/utils/claudemd.ts", 1, "claudemd.ts")} 保留来源 provenance，并处理多层目录、@include 和外部 include approval；{src("src/utils/attachments.ts", 1, "attachments.ts")} 区分 user-triggered、every-thread 与 main-only attachment。[S: S-012–S-013]

## Context 是有结构的位置，不只是字符串拼接

这里的 **system prompt** 是 provider request 中具有高指令优先级的 system 内容；**system context** 是 harness 计算出的环境/模式信息；**user context** 则以 user-side context block 形式加入项目规则、memory 和动态附件。它们都可能影响模型，但在 request 中的位置、cache 行为和指令优先级不同。

**Provenance** 指每段 context 的来源记录，例如来自 managed CLAUDE.md、用户级文件、项目文件、某个 skill 或某次 tool result。保留 provenance 能帮助 reload、approval 和调试，也让 compaction 后的“哪些来源仍然存活”可被追踪。

System prompt/context 放产品约束、tool/mode guidance 与稳定环境信息；user context 则把 CLAUDE.md、memory、skills、MCP/agent/tool delta 和 runtime attachments 以可追踪来源带入消息链。`CLAUDE.md` 还分 managed、user、project、local 与目录层级，可通过 `@include` 引入外部文件；auto memory 是可审计文件，不等于 transcript。[D: D-005–D-006] [S: S-010–S-013]

## Compaction 不是一个摘要按钮

| 实际顺序 | Stage | 条件 | 主要效果 | 不是 |
|---|---|---|---|---|
| 1 | Tool-result budget | 常规路径，优先处理旧工具输出占用。 | 缩减或替代高体积 tool result，使后续 request 先释放低价值 token。 | 不是整段会话摘要，也不改变所有历史消息。 |
| 2 | History snip | `HISTORY_SNIP` feature 条件满足时。 | 从当前 projection 中剪掉符合条件的历史 segment，降低进入本轮 request 的历史量。 | 不是删除 durable transcript；被 snip 的记录仍可能存在于 JSONL。 |
| 3 | Microcompact | 常规路径；cache 行为另受 feature 控制。 | 对旧内容/结果做细粒度清理，尽量在不生成大摘要的情况下回收 token。 | 不是 autocompact，也不一定产生新的 summary boundary。 |
| 4 | Context collapse | `CONTEXT_COLLAPSE` feature 条件满足时。 | 条件性折叠更大历史结构，作为更强的 projection/替代机制。 | 源码存在不证明 external bundle 一定启用。 |
| 5 | Autocompact | token threshold/config 满足且前序处理仍不足或策略要求时。 | 通过模型生成 summary boundary，并重注入仍需保留的文件、plan、skill、MCP/agent/tool delta。 | 不是无损压缩；survivor 需要单独检查。 |
| 6 | Hard-limit recovery | 上述步骤后仍 prompt-too-long、max-output 或 request 不合法。 | 尝试最后恢复、报错或 terminal transition，避免构造非法 model request。 | 不是日常 memory 管理 stage，而是失败收束路径。 |

这个顺序直接来自 {src("src/query.ts", 365, "query.ts ordered shapers")}；早先报告把 microcompact 与 history snip 颠倒，已由逐语句 source-order audit 纠正。[S: S-014] [C: C-007]

这些 stage 处理的粒度不同：

- **Tool-result budget** 优先缩减旧工具输出，因为它们往往体积大、可由文件路径或 preview 替代；它不等于总结整段对话。
- **History snip** 按条件把某些旧 message segment 从本轮 projection 中剪掉，原始 durable transcript 不一定同时消失。
- **Microcompact** 做更局部的内容清理，目标是先回收低价值 token，避免立即调用模型生成大摘要。
- **Context collapse** 是 feature-gated 的更大范围结构折叠；“源码存在”不证明 external build 启用。
- **Autocompact** 在 threshold/config 满足时生成 summary boundary，用摘要替代较老 history，同时重注入仍需要的文件、plan、skill 和动态状态。
- **Hard-limit recovery** 是前述处理后仍无法形成合法 request 时的最后恢复/终止路径，不是第六种日常 memory。

`boundary` 是“从哪里开始把摘要视为新的有效历史起点”；`survivor` 则是 compaction 后仍被明确保留或重新注入的信息。判断 compaction 质量不能只看 token 数，还要检查关键约束和 provenance 是否成为 survivor。

`compactConversation` 通过另一次模型调用生成 summary boundary，再有限重注入近期文件、plan、skill、MCP/agent/tool delta。[S: S-015] 这些机制分别可能清理旧结果、投影历史段，或用摘要替换历史。Memory 与 transcript 都会进入 context，但前者是可维护知识来源，后者是 durable execution history；所有权和恢复语义不同。[S: S-012–S-015, S-029]

最大未知项是摘要信息损失、实际 threshold、启用的 feature projection 和长任务语义漂移。需要可运行构建强制 overflow，再比较压缩前后 request envelope 与 resume。{tech("context-lifecycle")}
"""

REPORTS["05-models-tools-extensions.md"] = f"""# 模型、工具与扩展

{NOTICE}

{fig("claude-tool-surface", "Claude Code tool and extension surface")}

## 一项 capability 从“存在”到“执行”的状态链

1. **Installed/configured**：代码、plugin 或 MCP 配置存在于机器上。
2. **Registered**：loader/registry 已把它转换成候选 capability。
3. **Eligible**：当前 mode、feature、policy 和 provider 条件没有把它过滤掉。
4. **Visible schema**：name、description 和 input schema 被放进这一轮 model request；这是模型“知道可以调用”的边界。
5. **Requested**：模型真的返回匹配的 `tool_use` block。
6. **Dispatched**：router 找到实现并通过 schema/input validation。
7. **Authorized**：hooks/permission 决定允许该具体 input。
8. **Executed**：在可选 sandbox/外部 MCP backend 中运行，并生成 result。

因此“Claude Code 支持某工具”至少可能指前四种不同事实。安全分析必须说明自己证明到了哪一级。

## 图中层次与扩展名词

- **Built-in Tools**：Bash、Read/Edit/Write、search、Agent、Task、plan 等；进入 pool 仍受 mode、feature、deny 和 enabled state 影响。[S: S-019]
- **MCP Servers**：通过 Model Context Protocol 连接的外部 capability provider。server lifecycle 包括配置、启动/连接、列出 tools/resources/prompts、健康状态与关闭；一次 tool invocation 只是其中一个阶段。[S: S-020]
- **Plugins**：是 packaging/distribution 层，不是单一 runtime injection point。manifest 除 metadata 外可组合 hooks、commands、agents、skills、output styles、channels、MCP、LSP、settings 与 user config 十类 component surfaces。[S: S-046]
- **Skills**：主要把 prompt/workflow 内容按需注入 context，不天然构成 executable sandbox；其低初始 context cost 来自 progressive disclosure，而不是“免费”。[D: D-005] [S: S-013, S-033]
- **Tool Pool**：当前候选集合；built-in 在同名冲突时优先，并稳定排序。[S: S-020]
- **Visible Schemas**：真正发送给模型的 schemas。registry 存在不保证这一轮可见。[S: S-019–S-021]
- **Tool Router**：lookup、schema/input validation、hooks 和 permission 的共同执行路径。[S: S-022]
- **Tool Result**：执行输出被转换成与 `tool_use_id` 对应的模型消息。过大结果可能落盘，只向模型返回 preview/path；所以“工具完整 stdout”不一定等于“模型实际看到的 result”。
- **Hook**：在 27 类 lifecycle event 上运行的观察/修改/阻断逻辑。部分 hook 可以执行外部命令，因此既是扩展点也是需要单独审计的副作用表面。[S: S-028, S-043]
- **LSP**：Language Server Protocol 服务，向编辑/分析能力提供符号、诊断等语言信息；plugin 可以打包 LSP 配置，但它不是 MCP tool 的同义词。[S: S-046]

## Provider、retry 与 fallback

**Provider** 是模型服务的承载路径。direct Anthropic 直接调用 Anthropic API；Bedrock、Vertex 和 Foundry 分别通过 AWS、Google Cloud 和 Azure 承载接口。它们可以共享上层 Messages 语义，但认证、endpoint、header 和错误分类不同。

**Retry** 通常在同一 provider/model 上重试暂时性失败，例如 429/529 或断流；**fallback** 则切到不同 request mode、model 或 provider path。二者都可能让一次用户 query 包含额外 API request，但不会自动重放已经产生副作用的 tool call。

{src("src/services/api/client.ts", 88, "getAnthropicClient")} 选择 direct Anthropic、Bedrock、Vertex 或 Foundry。{src("src/services/api/claude.ts", 1480, "Messages request builder")} 负责 messages/system/tools、thinking、cache/beta headers 与 stream；{src("src/services/api/withRetry.ts", 170, "withRetry")} 处理 auth refresh、429/529、backoff、fallback 和 token correction。[S: S-016–S-018]

## SiFlow 结果

models route 返回 qwen3.6-35ba3b 与 262,144 context；Anthropic /v1/messages 非流式和 SSE 均 HTTP 200；带 tool_choice=echo 与 enable_thinking=false 时返回 tool_use，input 为 {{"text":"hello"}}。[X: X-002]

这证明协议子集可用，不证明完整 Claude Code request 兼容。真实 envelope 还含 beta headers、thinking/output config、prompt caching、复杂 schemas 与多轮 tool_result。[C: C-009, C-025]

六个不要混淆的等号：installed plugin ≠ enabled plugin；registered tool ≠ visible schema；visible ≠ model 一定调用；tool call ≠ permission allow；allow ≠ sandbox enabled；skill loaded ≠ 独立进程执行。{tech("tool-extension-surface")}

## 四类扩展注入的是不同语义位置

{fig("claude-extension-injection", "Claude Code 扩展注入位置与 context 成本")}

- **Assemble**：构造模型输入的阶段，决定 system/user context、instructions 和 attachments 中出现什么。
- **Model surface**：放进 request 的 tool schemas/resources/prompts，决定模型知道自己可以调用什么。
- **Authorize/execute**：模型提出 action 之后的 hook、permission、sandbox 和 backend，决定请求能否以及如何产生副作用。
- **Packaging**：把多种 component 一起分发、配置和启用；它不自动等于上述任一 runtime stage。

| 机制 | 主要注入点 | 模型/loop 实际得到什么 | Context 成本与治理 |
|---|---|---|---|
| Skills | Assemble，即 request 组装和 instruction 选择阶段。 | 先暴露短描述供发现；被任务命中后才加载详细 instruction、workflow 或 resource 到 context。 | 初始 token 成本低、使用后增长；skill 内容能指导模型，但不天然获得 shell/file 权限，也不是独立进程。 |
| MCP Servers | Model surface + execute，即模型可见 schema 与外部 server 调用边界。 | 动态 tool schemas、resources 或 prompts；调用时还要经过 MCP client lifecycle、tool dispatch 和 permission/治理。 | schema 可能常驻也可能按需暴露；server 已连接不表示所有 tools visible，更不表示具体 input authorized。 |
| Hooks | Assemble、authorize/execute、lifecycle，即生命周期事件上的观察、修改、阻断或外部命令回调。 | 27 个 hook event 可以读取上下文、改写行为或影响 permission/tool 结果；部分 hook 自身也会产生副作用。 | Event-driven，不是每个 hook 都进入 model context；因为能执行外部命令，所以需要与 tool path 分开审计。 |
| Plugins | Packaging fan-out，即把多种 component surfaces 一起分发、配置和启用。 | 可打包 commands、agents、skills、hooks、MCP、LSP、settings、output styles 等，但运行时仍落到各自机制。 | Plugin 自身没有统一 context 或 execution 语义；安装/启用/可见/执行必须拆开看。 |

这张图按“模型看见什么、模型能调用什么、动作能否/如何执行”分层，而不是按目录或安装格式分组。27 是当前 `HOOK_EVENTS` 常量的源码计数；十类是 manifest component groups，均受 snapshot/feature/config 条件限制，不能外推成所有生产构建始终启用。[S: S-043, S-046] [C: C-028]
"""

REPORTS["06-permissions-sandbox-workspace.md"] = f"""# 权限、Sandbox 与 Workspace

{NOTICE}

{fig("claude-permission-pipeline", "Claude Code permission pipeline")}

共享 toolExecution 先做 schema/tool validation，再运行 pre-tool hooks，随后 permission resolver。{src("src/utils/permissions/permissions.ts", 560, "hasPermissions")} 综合 blanket deny、ask rules、tool check、tool deny、interaction requirement、safety、mode、allow rule 与 passthrough。[S: S-022–S-024]

## Permission 由 rule、mode、decision 和 prompt 四部分组成

- **Rule** 针对 tool name 和可选 input pattern 表达 allow、ask 或 deny，并记录来源，例如 managed policy、user/project/local settings、CLI 或当前 session。deny-first 表示更强的拒绝规则不会被较宽松 allow 轻易覆盖。
- **Mode** 是一组默认决策策略，不是单条权限。例如 `plan` 限制实现型动作，`dontAsk` 在无法交互时倾向 fail closed。mode 仍会与具体 rules 和 tool-specific safety check 组合。
- **Decision** 是对“这一次具体 tool input”算出的结果：allow、deny，或需要 ask。它不是对整个 tool 永久授权。
- **Prompt/approval UI** 只在当前 surface 能与人交互且 decision 为 ask 时出现。headless/async child 不能假设可以弹出和 REPL 相同的 dialog。

**Blanket deny** 是覆盖范围较广的拒绝；**managed policy** 是组织/管理员施加、普通 session 不能随意覆盖的规则；**interaction requirement** 表示某些 action 无论一般 mode 多宽松，仍要求显式人类交互；**classifier** 是 feature-gated auto mode 中辅助判断具体请求风险的模型化步骤，不等于 sandbox。**Fail closed** 指无法完成必要判断或无法询问时选择拒绝/停止，而不是默认放行。

外部 schema 固定五种 mode：`default`、`acceptEdits`、`dontAsk`、`plan`、`bypassPermissions`。`auto` 只有 `TRANSCRIPT_CLASSIFIER` 构建中才加入 user-addressable runtime set，并对 external serialization 映射回 `default`；`bubble` 只属于 internal union，不在 runtime validation set。论文或图把它们直接数成七个并列用户模式会夸大可用表面。[S: S-023, S-044]

| Mode | 实际语义 | 不能误读为 | 计数边界 |
|---|---|---|---|
| default | 按规则、tool safety check 和交互可用性决定 allow/ask/deny；需要人类判断时可弹 approval。 | 所有工具都必然弹窗，或所有未知动作都可自动执行。 | external schema 中的稳定用户模式。 |
| acceptEdits | 对编辑类动作给更宽松默认，但 shell、网络、敏感 tool 仍受 rules、mode 和 safety checks 约束。 | 全部 tool 直接 allow，或关闭 permission resolver。 | external schema 中的稳定用户模式。 |
| dontAsk | 在无法或不应交互时避免弹窗；不能自动决定的路径通常 fail closed 或按非交互策略处理。 | `bypassPermissions` 的别名，或静默允许所有 ask。 | external schema 中的稳定用户模式。 |
| plan | 偏向规划/阅读，限制实现型或高副作用动作。 | OS 层 read-only sandbox；它是 permission mode，不是 filesystem 隔离机制。 | external schema 中的稳定用户模式。 |
| bypassPermissions | 显式绕过 canonical permission decision，让工具路径减少或跳过 ask/deny 检查。 | 环境绝对安全，或 sandbox 自动开启。 | external schema 中的稳定用户模式，但应视为高风险配置。 |
| feature-gated auto | `TRANSCRIPT_CLASSIFIER` 构建中加入的自动分类路径，结合 classifier 与特殊 safety handling。 | external schema 的第六个无条件稳定 mode。 | feature/build 条件满足时才 user-addressable，serialization 还会映射回 `default`。 |
| internal bubble | child/dialog 之间传播 permission prompt 或 decision 语义的内部 union 值。 | 用户可在 CLI/settings 中直接选择的 runtime mode。 | internal-only，不计入外部用户 mode census。 |

## 七个重叠边界，而不是一个 PermissionGate

1. tool-specific input/schema 与 dangerous-pattern prefilter；
2. managed/user/project/local/CLI/session rules，deny 优先；
3. mode fallback 与交互可用性；
4. feature-gated auto classifier 和 explicit-user-permission exceptions；
5. 27-event hooks 中的 PermissionRequest/Denied、Pre/PostToolUse；
6. 可选 filesystem/network sandbox；
7. resume/fork 重新从持久 settings/CLI 初始化，**不恢复 session-scoped allow/deny/ask grants**。[D: D-001, D-003–D-004] [S: S-023–S-028, S-043–S-044]

第 7 层是 trust freshness，而不是 transcript 丢失：会话历史可恢复，临时授权不会随 JSONL 被静默带入新进程。[C: C-029]

## Sandbox 是后续执行变换

shouldUseSandbox 依赖 availability/settings、excluded commands 与 dangerouslyDisableSandbox 是否被 policy 允许。选中后 SandboxManager 映射 FS/network settings，Shell 包装命令再 spawn；未选中则直接由 Shell 执行，但 canonical path 中仍应先经过 permission。[S: S-025–S-027]

所以 Permission 回答“可不可以”，Sandbox 回答“以什么边界执行”。普通 Agent child 默认共享 cwd/files；worktree isolation 是可选项。Sandbox 也不是事务式文件回滚。[S: S-032, S-035]

图底部 Hooks + Other Subsystems 带 AUDIT，因为 startup、hooks、MCP lifecycle、bridge/daemon 等有独立副作用表面。不能因为 canonical tool path 有 PermissionGate 就自动宣称全部同等受控。这是 open claim C-014，不是已经发现具体 bypass。[S: S-003, S-028] [I: I-001]

下一实验应抓 harness event、process tree、filesystem diff 与 network attempts，对 permission modes、sandbox on/off、hooks/MCP 做矩阵。{tech("permission-pipeline")}
"""



REPORTS["07-subagents-delegation.md"] = f"""# Subagent 与团队协作

{NOTICE}

{fig("claude-subagent-topology", "Claude Code subagent and teammate topology")}

## 先定义图中名词

- **Parent Query**：主线程当前一次用户 query；它可以通过 AgentTool 委派，也可能在 child 后继续自己的 loop。
- **AgentTool**：模型可调用的 delegation tool。它选择 normal/fork、sync/async、agent definition、tool pool 与 isolation。[S: S-032]
- **Agent Child**：runAgent 驱动的 child query loop。它有自己的初始 messages、system/user/system context、tool context、agent-specific MCP 与 sidechain transcript。[S: S-033]
- **SYNC**：父 tool call 等 child 完成后返回 result；共享某些 AppState callback 和父 abort 语义。
- **ASYNC**：注册为 background task，拥有未链接到主请求 ESC 的 abort controller，完成后以 notification 回到主 context。[S: S-032–S-033]
- **Sidechain JSONL**：child 的 transcript 文件，不等于主 session JSONL 中的一条普通消息。[S: S-029, S-033]
- **Shared Workspace**：普通 Agent child 默认在同一 cwd/files 上工作；context 分开不代表文件隔离。
- **Worktree Isolation**：显式请求后创建独立 git worktree。无改动可清理，有改动通常保留路径供后续处理。[S: S-032, S-035]
- **Swarm Teammate**：团队成员机制，可由 in-process backend 或 tmux/iTerm terminal pane 承载，不应一律称为独立进程。[S: S-034, S-036]
- **Team Mailbox**：~/.claude/teams/<team>/inboxes/<name>.json，使用文件锁投递 unread messages，也承载 shutdown/plan approval protocol。[S: S-037]

本报告没有使用“V2 mailbox”这个名称，因为该快照的证据支持的是具体 Team Mailbox；给机制贴未知版本标签只会增加阅读成本。

## “隔离”必须拆成多个维度

- **Context isolation**：child 是否拥有独立 message history、system/user context 和 token budget。独立 context 不自动意味着独立文件系统。
- **Tool/policy isolation**：child 看到哪些 tools、permission mode/rules 如何从 parent 派生，以及谁负责弹 approval prompt。
- **Transcript isolation**：child 的过程是否写入独立 sidechain JSONL，parent 最终只接收 summary/result，还是两者共享同一 message chain。
- **Workspace isolation**：child 是否与 parent 使用同一 cwd/files，还是进入独立 git worktree/container。
- **Process/backend isolation**：child loop 是在同一进程、另一个 terminal pane，还是独立 worker 中执行。terminal pane 是承载方式，不等于安全 sandbox。
- **Cancellation isolation**：parent 的 ESC/abort 是否传播。`AbortController` 是 JavaScript 的取消信号对象；独立 controller 表示 child 不自动订阅 parent 的同一取消信号。
- **Result channel**：sync tool result、async task notification 和 mailbox message 的到达时机、持久性和消费方不同。

`AppState callback` 指 child 仍可能调用 parent 进程提供的状态读取/更新函数；因此“独立 context”不能简化成“所有状态完全复制”。

## 静态 inheritance matrix

| 维度 | 普通 Agent child | Async child | Worktree child | Swarm teammate |
|---|---|---|---|---|
| Model/context | 由 child 重新构建初始 messages、system/user context、tool context 和 agent-specific MCP，不直接复制 parent 完整 history。 | 也重新构建 context，但以 background task 方式运行，完成后把 notification/delta 返回主 context。 | 重新构建 context，同时把 workspace path 指向新 git worktree；context 隔离与文件隔离同时出现。 | teammate runner 维护自己的 context 和任务状态；是否与主进程共享内存取决于 backend。 |
| Tool pool / policy | 从 parent permission context 派生，再应用 agent definition、mode 和 allowedTools override；managed/CLI policy 仍应保留。 | 派生逻辑相同，但 non-interactive 语义更重要，因为不能假设父 REPL dialog 可用。 | 派生逻辑相同；worktree 只改变文件边界，不自动扩大 tool 权限。 | 由 teammate runtime、mode、team config 和 backend 决定；不能只用 parent tool list 推断。 |
| Transcript | 写入独立 sidechain JSONL，parent 通常只接收 summary/result。 | sidechain 外还可能有 task output 与 notification，供主 context 后续消费。 | sidechain 加 worktree metadata，便于恢复或保留有改动的路径。 | team task state、team files 与 mailbox 共同承载过程和消息。 |
| Workspace | 默认共享 parent cwd/files，因此两个 child 可能竞争同一文件。 | 默认同样共享 cwd/files；后台运行会放大并发写入风险。 | 使用独立 git worktree；无改动可清理，有改动通常保留路径。 | 取决于 backend 与 team 配置：可能是同进程、终端 pane 或其他 runner，不能预设 container 隔离。 |
| 主请求 ESC / cancellation | sync 路径通常与父请求 abort 语义有关，具体传播需 runtime 验证。 | 不自动跟随主请求 ESC；需要显式 task kill/abort。 | 取决于该 worktree child 是 sync 还是 async 承载。 | 有独立 controller，可单独 abort；mailbox 仍可能保留未读消息。 |
| Result channel | 以 AgentTool 的 tool result 返回 parent loop。 | 以 task notification 或后续 attachment 进入主 context。 | 返回 result，并可能附带 retained worktree path 供后续处理。 | 通过 mailbox、task notification 或 team attachment 到达；时序与持久性不同。 |

该表是源码恢复，不是 runtime measurement；最关键的未验证项是 permission prompt 在 sync/async/teammate 间的实际传播、并发文件冲突和 process identity。[C: C-017–C-020]

## Child 权限不是简单“继承父权限”

`runAgent` 从当前 parent permission context 出发，再应用 agent definition override：parent 的显式 mode 约束优先；SDK `cliArg` rules 会保留；若 child 明确声明 `allowedTools`，它替换的是 session-sourced rules，而不是抹掉 managed/CLI policy。async child 因不能弹普通父 UI dialog，还要走 non-interactive/notification 语义；`bubble` 是内部传播标记，不是用户选择的独立安全模式。[S: S-045]

因此正文使用“derive + override”而不是“copy”。要验证真实边界，必须分别记录 parent/child 的 effective mode、rule provenance、prompt owner 与最终 decision；只比较 tool list 不够。

## Coordinator 不是新的 agent loop

Coordinator mode 主要改变主模型 prompt、可见 tools 与 worker orchestration 规则；worker 最终仍通过 AgentTool/runAgent 进入共享 query core。不要把“orchestrator role”误画成与 query loop 平行的第二套 runtime。[S: S-032–S-033]

图中的 Result / Notification 是统一读者概念：sync child 返回 tool result；async child 产生 task notification；teammate 可通过 mailbox/attachment 通知。三者来源不同，报告不会用一根箭头掩盖差异。{tech("subagent-topology")}
"""

REPORTS["08-sessions-persistence-recovery.md"] = f"""# Session、持久化与恢复

{NOTICE}

{fig("claude-persistence-lifecycle", "Claude Code persistence lifecycle")}

## 持久化词典

- **Live state**：只存在于当前进程内存中的 AppState、正在运行的 query、abort controller 和未 flush 队列；进程退出后必须重建。
- **Durable state**：已经写入文件等进程外介质，重启后仍可读取。durable 只表示“数据还在”，不保证格式完整、仍被当前配置采用，或自动进入模型 context。
- **JSONL transcript**：一行一个 JSON record 的追加式会话日志。它不是一份每次覆盖的完整 session JSON snapshot。
- **parentUuid**：把一条 message/record 指向逻辑父记录的标识。恢复时沿这些链接重建当前分支，而不是假设文件行号就是唯一对话顺序。
- **Sidechain**：subagent 的独立 transcript 分支。它和主 session 有关联 metadata，但 child 的中间消息不需要全部进入 parent context。
- **Queue/flush**：写入先进入进程内队列，`flush` 才表示尽力把待写 records 落到持久介质；突然 SIGKILL 可能发生在两者之间。
- **External workspace state**：普通文件、git worktree 和远程副作用虽然也会持久存在，但不由 session JSONL 统一拥有，所以 resume 不能把它们当会话字段回滚。

## Live 与 durable state

| 状态 | 所有者 | 是否 durable | 恢复含义 |
|---|---|---|---|
| Live Session | 当前进程的 AppState、正在运行的 query、队列和 abort controller。 | 否；进程退出后内存对象消失。 | Resume 只能重新构建等价 view，不能恢复正在运行的 promise、未 flush 队列或旧 controller。 |
| Message chain | transcript JSONL 与 parentUuid 逻辑链。 | 是；以追加式 records 保存。 | 通过 parentUuid、branch selection 和 compaction boundary 重建当前会话视图，不是按文件行号简单 replay 全部记录。 |
| Child transcript | subagents/agent-*.jsonl 与 agent metadata。 | 是；child 过程有独立 sidechain。 | 恢复时可选择/关联 child 分支，但 parent 不会自动把 child 中间消息全塞回主 context。 |
| Compaction boundary | transcript entry、summary segment 和 preserved metadata。 | 是；影响后续 projection。 | 指定旧历史由 summary 代表的位置，以及哪些 survivor 被重新注入。 |
| Team inbox | `~/.claude/teams` 下的 team files/mailbox。 | 是；文件锁保护 unread messages。 | 未读消息可跨进程作为 attachment 消费，但它是 team 通道，不是主 JSONL 的普通行。 |
| Workspace files | 当前 cwd、git worktree、外部命令产生的文件和远程副作用。 | 外部持久状态；由 OS/git/远端拥有。 | 不随 session resume 自动回滚；需要 git、file-history rewind 或更强 checkpoint 机制单独处理。 |
| Worktree path metadata | session/agent metadata 中记录的路径和 agent/worktree 关联。 | 条件 durable；只有路径仍存在且配置可访问时有意义。 | 可帮助恢复 child cwd 或保留改动路径，但不能保证 worktree 内容完整或无外部修改。 |

{src("src/utils/sessionStorage.ts", 500, "sessionStorage")} 使用项目路径派生目录和 sessionId JSONL，主消息与 sidechain 分开；parentUuid 形成逻辑链。写入有 queue/flush，compact/snip 后会重连 dangling parent 或重写可恢复 segment。[S: S-029]

## Resume 与 fork 的精确差别

- **Resume**：默认继续原 sessionId，加载 transcript/metadata，恢复 agent/mode、file history attribution、todo、worktree path 等可用信息。
- **Fork**：保留启动时的新 sessionId，同时复制可恢复 history 与部分 replacement metadata；它是会话身份分叉，不是 git branch 或文件快照。
- **Rewind files**：CLI 另有显式 file-history rewind，说明普通 resume/fork 本身不等于 filesystem rollback；它也不是任意 workspace/process 的通用 checkpoint。[S: S-030–S-031]
- **Permission freshness**：resume/fork 不从 transcript 反序列化旧 session 的临时 allow/deny/ask grants；新进程从当前 settings 与 CLI 参数重建 permission context。[S: S-044] [C: C-029]

所以 durable transcript 保存“发生过什么”，不自动保存“现在仍被授权做什么”。若恢复后再次请求同一 Bash action，正确的验证实验是观察是否重新 ask，而不是只检查 mode label。

## Compaction 与 persistence

Compact summary 不只是内存中替换 messages：boundary、preserved segment 和重注入 metadata 会影响之后 JSONL chain 如何加载。[S: S-015, S-029]

这里的 **byte-level prefilter** 是先用字节/记录级条件筛掉明显无关或不完整的输入，避免所有内容都进入高层解析；**dead-branch pruning** 是去掉不在当前 parentUuid 分支上的历史；**parent-chain reconstruction** 是沿父链接恢复当前有效消息链。三者说明 resume 不是“按文件顺序读取所有 JSON 行”，而是从 append log 重建一个逻辑会话视图。

## Crash/exit recovery

Graceful shutdown 把 cleanup/persistence 放在 SessionEnd hooks 和 analytics 之前，并用 2 秒 cleanup race、hook budget、analytics 500ms cap 与最终 failsafe 限制退出时间。[S: S-041]

静态代码尚不能回答 corrupted JSONL 是 fail closed、局部修复还是丢弃到什么粒度，也不能证明 abrupt SIGKILL 时最后一批 buffered writes 的边界。需要 resume/fork/corruption/signal 四组实验。{tech("persistence-lifecycle")}
"""

REPORTS["09-observability-evaluation.md"] = f"""# 观测、Tracing 与评估边界

{NOTICE}

{fig("claude-observability-recovery", "Claude Code observability and recovery layers")}

## 先区分 event、metric、span、trace 和 profiler

- **Event** 是某件事发生的一条离散记录，例如 tool 被调用或某 feature 启用；它适合计数和属性分析，但不天然表达父子关系。
- **Metric** 是聚合数值，例如次数、延迟分布或 token 总量。当前源码中的 analytics event 可以被 sink 聚合成 metric，但 event 本身不是 metric。
- **Span** 表示一个有开始/结束时间的操作，例如一次 LLM request 或 tool execution，并可带 status、token 和 parent span。
- **Trace** 是由 parent-child spans 组成的一次端到端执行树。只有 correlation 正确，才能知道某个 tool span 属于哪次 interaction/model request。
- **Profiler** 关注进程内部阶段耗时和资源快照，通常用于本地诊断；它不一定发送到 telemetry backend。
- **Redaction** 是在记录前删除或替换 prompt、路径、代码等敏感内容。它降低泄漏风险，但只有 runtime 配置与实际 payload 检查才能证明生效。

## 四类观测面

| 图中标签 | 机制 | 默认/条件 | 能回答什么 |
|---|---|---|---|
| Events | analytics `logEvent` queue、typed metadata 和 attachable sinks/exporters。 | 依赖 sink 初始化、sampling/config 和 metadata redaction 约束。 | 回答哪些 feature/tool/error 发生过、带了什么低敏属性；不能表达一次 query 的完整父子时序。 |
| OTel spans | interaction、LLM request、tool execution、hook 等有开始/结束时间的 spans。 | 受 enhanced/beta telemetry gate、exporter 和 privacy 设置控制。 | 回答 parent-child timing、token、status、success/error；前提是 correlation 正确且 payload 被正确 redacted。 |
| Query Profiler | local performance marks、阶段耗时和 memory snapshot。 | 由 `CLAUDE_CODE_PROFILE_QUERY` 等本地开关触发。 | 回答 context/model/tool 前后阶段耗时和资源变化；更适合本地诊断，不等于生产 telemetry。 |
| Perfetto Trace | Chrome trace event 格式、agent registry 和可视化 timeline。 | 受 feature/user/env gates 控制，默认不能假设开启。 | 回答 agent hierarchy、TTFT/TTLT、tool spans 和并发关系；没有 trace 时不能推断频率或 latency 分布。 |

{src("src/utils/telemetry/sessionTracing.ts", 176, "sessionTracing")} 用 **AsyncLocalStorage**（Node.js 在异步 callback/promise 链中传播请求上下文的机制）保存 interaction/tool context，并为并发 LLM request 要求显式传回对应 span，避免 response 绑错。默认 prompt 内容会 redacted，只有显式 env 才记录。[S: S-039]

表中的 **sink** 是 event/span 的最终接收器或 exporter；**sampling** 表示只记录满足比例/规则的事件；**TTFT** 是 time to first token，衡量请求到首 token；**TTLT** 是 time to last token，衡量请求到最后 token。它们回答的性能问题不同。

{src("src/services/analytics/index.ts", 1, "analytics API")} 在 sink attach 前排队事件，并用类型标记要求字符串 metadata 显式确认不含代码/路径；这是一种源码层防误传机制，不等同于完整隐私证明。[S: S-038]

Perfetto 记录 agent parent relationship，但源码注释标明条件门控；图中 OPTIONAL 不是装饰，而是防止读者以为每次用户运行都会产出 trace。[S: S-040]

## Retry 与 shutdown 为什么分成两条 lane

Model retry 处理一次调用边界上的 auth/rate/capacity/stream 问题；graceful shutdown 处理 process lifecycle。前者可以回到同一 query，后者目标是尽快保存关键状态并退出。把它们画成一个 Recovery box 会丢失时间预算和所有权差异。[S: S-018, S-041]

## 本分析观测到什么

只观测到 snapshot scanner 和 provider protocol probe，没有 target interaction/LLM/tool spans。因此本报告不能给出 latency、token、cost、tool frequency、delegation coverage 或 production behavior distribution。将来启用 OTel 时应保持 prompt redaction，另用 sanitized request digest 比较 context，而不是保存私有 prompt。{tech("layered-architecture")}
"""



REPORTS["10-design-decisions.md"] = f"""# 设计决策与权衡

{NOTICE}

这里严格使用 `D → design question → S → I`：官方材料只支持产品目标，源码说明 mechanism，收益/代价仍是 analyst inference。不能把“官方强调 safety”直接写成“作者因此选择了某个函数结构”。

这张表是证据索引，不是完整解释。`D` 列只说官方材料公开强调了什么；`S` 列列出该快照的机制；`I/X` 列才是分析者提出的权衡与反例实验。相同一行中的 D 和 S 不构成已经证明的作者因果链。

| 决策 | First-party stance（D）只支持什么 | 当前机制（S） | Analyst tradeoff 与反例测试（I/X） | 证据边界 |
|---|---|---|---|---|
| 多 surface 共用 `query()` | 官方材料支持 iterative agentic loop 与可验证结果，但不直接说明每个入口的代码结构。 | REPL 的 QueryGuard/onQueryImpl 与 headless QueryEngine 都适配到同一 async generator。 | 复用 tool-result、stop 和 recovery 语义；风险在 UI/headless state 差异。反例测试是给两个入口相同 scripted response，diff event/message sequence。 | D-002；C-003–C-004。当前为 static-only，无双入口 runtime trace。 |
| Context 按生命周期合流 | 官方强调 context scarce、progressive disclosure、memory 可检查与 compaction。 | Prompt、CLAUDE.md、history JSONL、attachments、skills/MCP delta 进入五阶段 ordered shaper。 | 节省无关 context 并保留 provenance；代价是顺序、survivor 和摘要漂移难推理。反例测试是逐项 ablation 与 overflow envelope capture。 | D-005–D-006；C-006–C-007。压缩损失未量化。 |
| Registry 与 exposure 分离 | 官方 stance 支持按任务逐步呈现 capability。 | Tool pool、filter/eligibility、visible schema、dispatch/router 四层分开；MCP/skills/plugins/hooks注入不同位置。 | 动态能力强，审计面也更复杂。反例测试是 built-in/MCP 同名、enabled/disabled、mode 组合矩阵。 | D-005；C-010、C-028。未安装 fixture 实测。 |
| Permission 与 sandbox 分离 | 官方材料支持 human control、bounded autonomy 和 sandboxing 作为安全层。 | Policy decision 先判断 allow/ask/deny；Bash 等执行路径再按 settings/policy 选择 sandbox wrapper。 | 两层可组合，部署灵活；代价是 allow 容易被误读成 isolated。反例测试是同时记录 permission event、process tree、file diff、network attempt。 | D-001、D-003–D-004；C-012–C-014。canonical path 外副作用仍待审计。 |
| Child context 分离、workspace 默认共享 | 官方 team/subagent 材料支持 independent context 的产品概念。 | `runAgent` 重建 context/tool/MCP，写 sidechain；普通 child 默认共享 cwd，worktree 是显式选项。 | 节省 parent token 并便于共享 artifacts；代价是并发文件冲突。反例测试是默认 cwd 与 worktree 下的 same-file experiment。 | D-005、D-007；C-017–C-020。没有 child runtime matrix。 |
| JSONL append + parent chain | 官方 memory stance 支持可检查、可编辑、可延续，但不直接规定 transcript 格式。 | 主 session 与 sidechain 使用 JSONL、parentUuid、boundary 和 metadata；resume 不恢复 session-scoped grants。 | 易审计、易 fork；代价是 parent-chain reconstruction 与 corruption handling 复杂。反例测试是破坏尾记录、中间 parent、sidechain metadata。 | D-001、D-006；C-015–C-016、C-029。corruption/SIGKILL 未测。 |
| 多层 telemetry | 没有足够 first-party 架构意图，只能描述源码机制。 | Events、OTel spans、Query Profiler、Perfetto Trace 分别覆盖计数、时序、本地诊断和 timeline。 | 粒度可选；correlation、sampling 和 redaction 配置复杂。反例测试是并发 LLM/tool span correlation 与 sanitized payload 检查。 | C-021。没有 target interaction spans。 |
| Cleanup 优先的有界 shutdown | 没有足够 first-party 架构意图，只能评价可观察控制流。 | Persistence cleanup 先于 hooks/analytics，并有 cleanup race、hook budget、analytics cap 和 failsafe。 | 降低关键状态丢失风险；代价是 hung cleanup 会被时间预算截断。反例测试是注入慢 flush、慢 hook 和 signal。 | C-022。未做 signal/failure injection。 |

## 表中权衡的展开说明

**共享 query()** 的迁移价值是让 interactive/headless 复用相同 tool-result 和 stop 语义；风险在 surface adapter。验证方法不是比较函数名，而是给两个入口相同 scripted response，比较实际 event/message sequence。

**Context 生命周期合流** 的价值是按需加载和复用稳定内容；风险是 provenance、顺序和 compaction survivor。`ablation` 指一次只关闭一种来源，再比较 request envelope，从而判断该来源真正注入了什么。

**Registry/exposure 分离** 允许 MCP、mode 和 deferred discovery 动态改变模型所见工具；风险是审计者看到 registry 后误报能力面。`same-name/disabled matrix` 是用同名 built-in/MCP、enabled/disabled 和不同 mode 组合测试最终 visible schema 与 dispatch owner。

**Permission/sandbox 分离** 让策略判断与 OS 边界独立配置；风险是把 allow 当成 isolation。`side-effect matrix` 要同时记录 permission event、process spawn、文件 diff 和 network attempt，而不只看 UI 文案。

**Child context 分离但 workspace 共享** 减少 parent token 压力并方便共享 artifacts；风险是两个 child 同时修改同一文件。`same-file experiment` 应比较默认 cwd 与 worktree mode 下的冲突、保留路径和取消行为。

**Append-only JSONL** 便于追踪分支和 resume，但恢复依赖 parent-chain reconstruction；corruption test 应分别破坏尾记录、中间 parent 和 sidechain metadata。Telemetry/shutdown 两行缺少足够 D evidence，因此只评价可观察机制，不声称作者为何选择它们。

## 架构上最值得迁移的三点

第一，工具“存在、可见、被调用、被允许、被隔离、成功执行”应建模为六个状态，不应压成一个 capability edge。第二，subagent 隔离需要 context/process/workspace/policy/transcript/cancellation 六维矩阵。第三，resume 必须把 conversational state 与 external workspace state 分开描述。

## 不应迁移的假确定性

不能把 source-visible feature 当 production feature，不能把 analyst-normalized principle 冒充 Anthropic 官方 taxonomy，也不能把 provider probe 当 end-to-end harness validation。[C: C-023–C-027]
"""

REPORTS["11-runtime-experiments.md"] = f"""# 运行实验

{NOTICE}

## 实验术语

- **Target runtime**：真实 Claude Code build 启动后的 loop、permission、tool 和 persistence 行为。只有它能产生本报告定义的 R evidence。
- **Protocol probe**：直接向模型 endpoint 发送最小合成 request，检查 HTTP/SSE/tool-use 方言。它绕过了 Claude Code，所以只能证明 provider 接口子集。
- **Scripted model**：按测试脚本返回确定性 model/tool blocks 的假模型，用来强制 harness 走指定分支；它测试 harness，不测试真实模型判断质量。
- **Fault injection**：主动制造 timeout、deny、corruption、oversized output 或 crash，观察恢复路径。
- **Sanitized result**：移除 credential、私有 prompt、代码和路径后保存的实验摘要；sanitized 不等于原始 trace 完整保留。
- **Blocked scenario**：实验前置条件不成立，未形成目标行为证据；它不是“测试失败”，更不是“机制不存在”。

## 已执行

| ID | 实验问题 | 设置与前置 | 结果 | 证据边界 |
|---|---|---|---|---|
| X-SCENARIO-001 | 当前 source snapshot 能否自包含启动成 target runtime。 | Clean commit；静态 import resolver 检查相对 import、manifest 和闭合 module graph。 | 发现 657 个 missing relative imports，且缺少 package/build manifest。 | 证明本轮不能安全形成 target runtime R evidence；不证明这些源码机制在官方 artifact 中不存在。 |
| X-SCENARIO-002 | SiFlow endpoint 是否支持报告后续实验需要的 Anthropic Messages 方言子集。 | 无真实用户凭据、无私有 prompt；qwen3.6-35ba3b；非流式、SSE、forced tool_use 最小请求。 | models/messages/SSE/tool_use 均 HTTP 200，forced echo 返回结构合法。 | 只证明 provider protocol 子集可用；没有经过 Claude Code request builder、retry、permission 或 tool loop。 |
| X-SCENARIO-008 | 本地快照是否与论文声称的 Claude Code v2.1.88 TypeScript corpus 同源。 | 文件计数、关键 symbol、feature gates 和高辨识度机制 fingerprint。 | 1,884 TS/TSX 精确匹配，关键机制同名且结构强一致。 | 支持 strong fingerprint；缺少 package version、tree hash 或字节 artifact，不能升级为 exact identity。 |

Provider probe 的 forced call 是 echo({{"text":"hello"}})，并使用 `chat_template_kwargs.enable_thinking=false`，避免默认 thinking 消耗短输出预算。SSE（Server-Sent Events）是服务器在一条 HTTP response 上持续推送事件的文本流协议；HTTP 200 + 合法 SSE/tool_use 只能说明 endpoint 理解这组最小请求。原始内容仅含合成 prompt，sanitized 结果保存在 [provider-probe.json](../experiments/provider-probe.json)。[X: X-002]

## 未执行及原因

| ID | 场景 | 目标 claim | 为什么阻塞 | 下一步需要什么 |
|---|---|---|---|---|
| X-SCENARIO-003 | scripted text-only query | C-003/C-004 | 无闭合 module/build graph，无法启动真实 `query()` 并替换 callModel。 | 同 commit package/lock、source map 或 compiled bundle；然后用 scripted response 比较 event/message sequence。 |
| X-SCENARIO-004 | permission deny 无 side effect | C-012–C-014 | 无可启动 target，因此无法同时观测 permission event、process tree、filesystem diff 和 network attempt。 | 可运行 bundle，加 deny fixture、sandbox on/off、hook/MCP lifecycle matrix。 |
| X-SCENARIO-005 | context overflow | C-006/C-007 | 无法构造真实 request envelope，也无法触发实际 threshold、snip、microcompact 或 autocompact。 | 可运行 target、超长 synthetic history、sanitized request digest 与 survivor comparison。 |
| X-SCENARIO-006 | resume/fork | C-015/C-016 | 无法产生和恢复真实 JSONL、metadata、file history 与 permission context。 | 可运行 target、resume/fork/corruption fixture、permission grant freshness check。 |
| X-SCENARIO-007 | child inheritance matrix | C-017–C-020 | 无法启动 AgentTool/runAgent 的 sync、async、worktree、teammate 分支。 | Child runtime fixture，记录 pid、cwd、tools、mode、abort controller、transcript 和 result channel。 |

“blocked”不表示机制不存在，只表示本轮不能形成 R/X evidence。为了避免把 injector 行为冒充原系统，本报告没有手工补齐 657 个 import、伪造 package.json 或用 Python 重写 query loop。

## 下一轮最小 runtime package

需要同 commit 对应的 `package.json`/lock（依赖、版本与可重复安装信息）、完整 source-map contents（bundle 到原始模块的映射与可能内嵌源码）、`bun:bundle` feature manifest（构建时到底保留哪些 feature 分支），或已编译 external bundle。

恢复前置条件后，先跑 `version/help` 验证 bootstrap，再利用 `query/deps.ts` 的 **callModel seam**（core 调模型时可替换的依赖边界）注入 scripted response，执行 deterministic tool loop；最后才接真实 SiFlow endpoint。这样能把“harness 状态机错误”和“真实模型随机选择”分开。
"""

REPORTS["12-failure-modes.md"] = f"""# 失败模式与开放问题

{NOTICE}

## 风险术语

- **Identity gap**：知道本地 corpus 很像某个发布版本，但缺少 tree hash/package linkage，无法证明完全相同。
- **Reachability ambiguity**：源码里存在一条路径，但不清楚当前 build feature、mode 和 runtime config 是否能走到它。
- **DCE（dead-code elimination）**：构建时根据 feature 常量删除分支；被删除的源码机制不会出现在 external bundle。
- **Canonical path**：最主要、证据最完整的 model→tool 执行路径。证明 canonical path 有 gate，不等于证明所有后台/启动路径有相同 gate。
- **Semantic loss**：压缩后语法仍合法、任务仍能继续，但某些约束、事实或出处已经丢失。
- **Blind spot**：当前观测手段看不到的维度，例如没有 target spans 时无法知道生产 latency/frequency。

## 对分析结论影响最大的风险

1. **Snapshot identity gap**：1,884-file/symbol fingerprint 强匹配论文 v2.1.88 corpus，但无 package version/tree hash/build manifest。缓解：所有 source URL 固定 commit，身份写 strong fingerprint 而非 exact。[C-001, C-026]
2. **Feature reachability ambiguity**：feature() 分支可能被 DCE。缓解：mode/extension/hook 计数都写条件，图不把 source-visible 分支标 runtime verified。[C-023]
3. **Process-wide policy gap**：canonical tool gate 很清楚，但 hooks/startup/MCP 等需独立 reachability audit。这是 open claim，不宣称已有 bypass。[C-014]
4. **Compaction semantic loss**：静态可列保留项，不能量化 summary 丢失。[C-007]
5. **Child isolation ambiguity**：普通 child、async、worktree、teammate/pane 的边界不同；用一个 subagent 标签会造成安全误判。[C-017–C-020]
6. **Session/workspace confusion**：resume/fork 不自动回滚普通 files。[C-016]
7. **Telemetry blind spot**：本轮没有 target spans，无法报告性能、成本和频率。[C-021, C-025]

## 优先实验队列

`P0` 表示不解决就会动摇核心安全/版本结论，`P1` 是重要行为边界，`P2` 是在核心模型稳定后补充的排序与鲁棒性问题。

| 优先级 | 可证伪问题 | 为什么优先 | 判别数据 |
|---|---|---|---|
| P0 | 哪个 feature set 构成 external bundle。 | 直接决定 source-visible path 能否代表用户可达产品；没有它，mode、hook、auto、collapse 等计数都只能写条件。 | build manifest、bundle strings、source map、entrypoint reachability、feature constant value。 |
| P0 | 非 canonical side effects 是否有等价 policy。 | 这是核心安全声明的反例空间：canonical tool path 受控不自动覆盖 startup、hooks、MCP lifecycle、bridge/daemon。 | process/file/network trace、permission events、hook events、MCP lifecycle logs、deny-path side effects。 |
| P1 | sync/async/teammate 的实际 inheritance。 | Subagent 隔离是多维概念，静态矩阵需要 runtime 验证 prompt owner、policy owner、workspace 和 cancellation。 | pid、cwd、tool list、effective mode、rule provenance、abort controller、transcript path、result channel。 |
| P1 | compact 后再 resume 保留什么。 | 它连接 context 质量和 persistence 语义；只看 token 数无法判断关键约束是否存活。 | 压缩前后 request digest、summary boundary、survivor list、restored history、resume 后 model-visible context。 |
| P2 | concurrent tools 的真实排序。 | 并发执行若与协议合并顺序不一致，可能污染模型看到的结果顺序。 | tool start/end span、original `tool_use` block order、context modifier merge order、error cancellation record。 |
| P2 | corrupted JSONL 如何降级。 | 影响恢复可靠性，但不先于 P0/P1；需要可运行 target 和可控损坏 fixture。 | controlled byte corruption、tail truncation、中间 parent 缺失、sidechain metadata 破坏、resume result。 |

## 产品风险与分析限制要分开

“某机制尚未验证”是分析限制；“源码显示存在无 gate 的副作用路径”才可能是产品风险。本轮只把 C-014 保留为待审计边界，没有将未运行状态包装成漏洞结论。
"""



REPORTS["13-coverage-reproducibility.md"] = f"""# 覆盖率与复现

{NOTICE}

## Coverage 在这里表示什么

- **Source coverage**：哪些目录、入口和关键 symbol 被实际阅读；它不是“扫描到关键词”的文件数。
- **Runtime coverage**：哪些路径在指定配置下真的执行并产生 trace/side effect evidence。
- **Configuration coverage**：测试过哪些 mode、feature、provider、platform 和 permission policy。同一代码路径在不同配置下可能有不同语义。
- **Partial**：已覆盖该模块的主要 source path，但缺少完整 build graph、次要入口或 runtime scenario；它不是“精确完成了 50%”。
- **Excluded surface**：明确不在本轮结论范围内的模式。排除项不是不存在，而是读者不能用本报告替它作保证。

## 14 模块覆盖

| Module | 状态 | 已覆盖的 source 面 | Runtime / 未覆盖边界 |
|---|---|---|---|
| interfaces | partial source coverage | `cli.tsx`、`main.tsx`、REPL、QueryEngine，覆盖 bootstrap、interactive/headless 入口和部分子命令分发。 | 无 target run；server/bridge/MCP 子命令的实际 reachability 未验证。 |
| core_loop | partial source coverage | `query.ts`、query config/deps，覆盖 loop state、model request、tool follow-up、transition 和 recovery counters。 | 无 scripted/real query trace；不能证明事件顺序在 runtime 中完整出现。 |
| context_assembly | partial source coverage | context、prompts、CLAUDE.md、attachments，覆盖 provenance、startup/lazy/per-turn/carry-forward 来源。 | 无真实 request envelope；无法量化每类 context 的 token cost。 |
| compaction | partial source coverage | autoCompact、compact、microCompact、query shaper order，覆盖 source-verified stage order。 | 无 overflow/fault injection；summary loss、threshold 和 survivor 质量未测。 |
| model_abstraction | static + protocol probe | client、claude request builder、withRetry、providers，并执行 SiFlow protocol probe。 | Probe 绕过 Claude Code；完整 headers、thinking/cache、retry/fallback 未端到端验证。 |
| tools_extensions | partial source coverage | Tool types、registry、toolExecution、hooks、MCP、plugin schema、orchestration。 | 无 fixture 安装/调用；同名 tool、disabled tool、hook side effects 未实测。 |
| permissions_safety | partial source coverage | permission types/engine、mode schema、useCanUseTool、child derivation、resume freshness。 | 无 permission deny side-effect matrix；canonical path 外副作用仍为 open claim。 |
| sandbox_execution | partial source coverage | BashTool、shouldUseSandbox、sandbox adapter、Shell wrapper。 | 无实际 spawn、filesystem/network trace；sandbox availability 和 policy interaction 未跑。 |
| workspace | partial source coverage | cwd handling、worktree creation/cleanup、AgentTool workspace choices。 | 无并发 same-file 或 worktree retention experiment。 |
| sessions_persistence | partial source coverage | sessionStorage、sessionRestore、JSONL、parentUuid、fork/resume metadata。 | 无 corruption、SIGKILL、flush-boundary 实验。 |
| subagents | partial source coverage | AgentTool、runAgent、spawnInProcess、async task、worktree、teammate/mailbox。 | 无 child runtime matrix；pid/cwd/tool/mode/abort/result channel 未观测。 |
| orchestration | partial source coverage | query orchestration、tool scheduling、coordinatorMode 与 worker delegation。 | 无 branch-forcing scripted model；concurrent tool ordering 未实测。 |
| observability | partial source coverage | analytics、sessionTracing、OTel gates、Query Profiler、Perfetto。 | 无 target spans；不能报告 latency、cost、frequency 或 correlation accuracy。 |
| recovery | partial source coverage | withRetry、gracefulShutdown、compaction recovery、abort/interruption result。 | 无 induced provider failure、hung hook、slow flush 或 signal experiment。 |

partial 表示已做重点 source coverage，但缺少 build configuration 与 runtime scenario，不表示“只读了一半文件”。机器可读范围见 [coverage.json](../evidence/coverage.json)。

## 复现顺序

1. python3 experiments/scan_snapshot.py
2. python3 experiments/compile_analysis.py
3. python3 experiments/compile_story_specs.py
4. python3 experiments/write_reports.py
5. 运行 skill 的 render_diagrams.py 与 render_story_diagrams.py
6. 运行 validate_analysis.py . --strict
7. 运行 audit_outputs.py . --strict

## Artifact map

- [manifest.json](../manifest.json)：冻结对象、执行边界
- [inventory.json](../inventory.json)：启发式导航
- [hir.json](../hir.json)：34 nodes / 54 edges
- [claims.jsonl](../evidence/claims.jsonl)：29 claims
- [observations.jsonl](../evidence/observations.jsonl)：62 条 D/S/X/I evidence
- [conflicts.jsonl](../evidence/conflicts.jsonl)：快照与 runtime 冲突
- [scenarios](../scenarios/catalog.json)：3 executed（含 paper fingerprint）、5 blocked
- [story specs](../diagrams/story-specs.json)：十一张读者图规格，含 question/exact-text/glossary/exclusions contract
- [image prompts](../diagrams/generated/prompts/prompts.jsonl)：首批 gpt-image-2 正文图提示词；论文对照新增图见 [paper-gap prompts](../diagrams/generated/prompts/09-11-paper-gap-prompts.jsonl)
- [generated assets](../diagrams/generated/assets/)：当前八张 gpt-image-2 PNG 正文图；另三张已有 story spec/prompt，因本轮自定义 API 凭据发送审批未通过而待生成
- [image metadata](../diagrams/generated/metadata.json)：模型、端点类别、哈希与人工语义审查

该仓库无法单独重建官方 bundle、确定 feature set 或运行 Claude Code。它能强指纹映射到论文 v2.1.88 corpus，但关闭 exact identity 与 runtime 缺口仍需要同快照 package/build metadata、tree hash 或编译 artifact。
"""

REPORTS["14-source-claim-index.md"] = f"""# 源码与 Claim 索引

{NOTICE}

## 关键源码

| Evidence | 源码 | 主题 |
|---|---|---|
| S-002/S-003 | {src("src/entrypoints/cli.tsx", 33, "cli.tsx")} / {src("src/main.tsx", 585, "main.tsx")} | 产品入口、feature path |
| S-004/S-005 | {src("src/screens/REPL.tsx", 2661, "REPL")} / {src("src/QueryEngine.ts", 260, "QueryEngine")} | surface adapters |
| S-006–S-008 | {src("src/query.ts", 219, "query.ts")} | loop、recovery、stop |
| S-010–S-013 | {src("src/context.ts", 1, "context")} / {src("src/utils/attachments.ts", 1, "attachments")} | context |
| S-014/S-015 | {src("src/services/compact/compact.ts", 330, "compact")} | compaction |
| S-016–S-018 | {src("src/services/api/client.ts", 88, "client")} / {src("src/services/api/withRetry.ts", 170, "withRetry")} | provider/retry |
| S-019–S-022 | {src("src/tools.ts", 100, "tools")} / {src("src/services/tools/toolExecution.ts", 880, "toolExecution")} | capability |
| S-023–S-027 | {src("src/utils/permissions/permissions.ts", 560, "permissions")} / {src("src/utils/sandbox/sandbox-adapter.ts", 1, "sandbox")} | governance |
| S-029–S-031 | {src("src/utils/sessionStorage.ts", 500, "storage")} / {src("src/utils/sessionRestore.ts", 1, "restore")} | persistence |
| S-032–S-037 | {src("src/tools/AgentTool/AgentTool.tsx", 323, "AgentTool")} / {src("src/utils/teammateMailbox.ts", 1, "mailbox")} | child/team |
| S-038–S-041 | {src("src/utils/telemetry/sessionTracing.ts", 176, "tracing")} / {src("src/utils/gracefulShutdown.ts", 391, "shutdown")} | observability/recovery |
| S-043 | {src("src/entrypoints/sdk/coreTypes.ts", 25, "HOOK_EVENTS")} | 27 个 hook lifecycle events |
| S-044/S-045 | {src("src/main.tsx", 1035, "permission initialization")} / {src("src/tools/AgentTool/runAgent.ts", 415, "child permission derivation")} | resume 与 child permission |
| S-046 | {src("src/utils/plugins/schemas.ts", 884, "PluginManifestSchema")} | plugin packaging surfaces |
| D-001–D-008 | [Anthropic first-party sources](../evidence/observations.jsonl) | 产品立场，不直接证明源码控制流 |
| X-003 | [论文对照](15-paper-benchmark.md) | v2.1.88 corpus 强指纹 |

## Claim index

| Claims | 结论族 | 章节 |
|---|---|---|
| C-001, C-023–C-026 | snapshot、feature、intent、runtime 与论文 corpus 边界 | 01, 11–15 |
| C-002–C-003 | surfaces 与共享 core | 02 |
| C-004–C-005 | loop 与 tool result 回填 | 03 |
| C-006–C-007 | context 与 compaction | 04 |
| C-008–C-011 | provider、SiFlow、capability/dispatch | 05 |
| C-012–C-014 | permission、sandbox、process audit | 06, 12 |
| C-015–C-016 | JSONL、resume/fork、workspace | 08 |
| C-017–C-020 | Agent child、worktree、teammate/mailbox | 07 |
| C-021–C-022 | telemetry 与 shutdown | 09 |
| C-027 | 跨 subsystem 的架构承诺与五价值/十三原则 | 00-values, 10 |
| C-028 | MCP/Plugin/Skill/Hook 的差异化注入 | 05 |
| C-029 | resume/fork 不恢复 session-scoped permission grants | 06, 08 |

正文 PNG 是 gpt-image-2 根据 evidence-grounded prompt 生成并经人工语义审查的读者图；它们帮助解释，但不是结构化真值。可审计的 node/edge、claim 与 evidence 映射保留在 [story-specs.json](../diagrams/story-specs.json) 和各节链接的技术 SVG 中。最重要的开放 claim 是 C-014：canonical gate 之外的副作用表面是否有等价治理；它会保持 open，直到 runtime reachability 与 OS side-effect matrix 完成。
"""



REPORTS["15-paper-benchmark.md"] = f"""# 与 arXiv 2604.14228v2 的对照

{NOTICE}

对照对象是 [Dive into Claude Code: The Design Space of Today’s and Future AI Agent Systems](https://arxiv.org/html/2604.14228v2)。论文明确分析 Claude Code v2.1.88 的 1,884-file TypeScript corpus；本地快照的 TS/TSX 数量及高辨识度 symbols/feature gates 强匹配，但缺少 exact tree 证明。[X: X-003] [C: C-026]

## 不是“谁更长”，而是回答层级不同

| 维度 | 论文 v2 | 本报告改进前 | 本次改进后 | 仍有差距 |
|---|---|---|---|---|
| 研究 framing | 五 values、十三 principles、未来设计空间 | 机制章强，价值层弱 | 新增 D→I→S 的价值/原则/机制章 | taxonomy 仍需跨 harness 验证 |
| 版本身份 | 直接称 v2.1.88 | 只写 unknown | strong fingerprint / exact unproven | 需要 npm/tree hash |
| 核心 loop | turn flow 清楚，机制描述密集 | 生命周期词更精确 | 扩成九阶段，保留 Session/query/iteration/request 区分 | 无 runtime trace |
| Context | hierarchy、mutability、accessibility 表达强 | provenance/compaction 较强 | 补 context 结构、五阶段真实顺序与条件 | 压缩损失未量化 |
| Extensions | Figure 5 的注入位置很有效 | 主要是 capability pipeline | 新增 Assemble/Model Surface/Authorize-Execute 投影 | 未安装 fixture 实测 |
| Permissions | 分层治理叙述强 | canonical path 与 audit 边界更谨慎 | 精确区分 5 external、feature-gated auto、internal bubble；补 resume grants | process-wide audit 未跑 |
| Subagents | isolation 与 agent types 易读 | child 机制/取消/后端区分更细 | 补 derive+override 权限矩阵 | 没有 child runtime matrix |
| Persistence | session 图直观 | JSONL/parentUuid/sidechain 更具体 | 补 trust freshness；避免把 resume 画成 rollback | corruption/SIGKILL 未测 |
| 可复现性 | 论文给 methodology，但无机器可读 claim graph | HIR/evidence/scenario 较强 | 29 claims、62 evidence、54 edges、benchmark appendix | snapshot 不可启动 |
| 图像 | 论文图密度高，按研究问题投影 | 读者图风格统一但少三类投影 | 新增 3 个 story spec/prompt 与 caption/glossary/exclusions contract | 外部 API 待授权；生成后仍需人工语义审核 |

## 论文做得更好的地方

1. **解释链完整。** 它不是从文件树开始，而是用 values/principles 组织 mechanism，读者更容易理解“为什么这个细节值得看”。本报告原先大量使用 I evidence，却没有足够 D evidence 约束价值判断。
2. **机制 census 更密。** 论文显式列出 compaction variants、hook event、permission modes、extension categories 与 built-in agents，使读者能感知设计表面大小。
3. **图按问题投影。** Figure 3、5、6 分别回答 layered responsibility、extension injection、context hierarchy；它们没有把完整 call graph 塞进一张图。
4. **研究讨论更远。** 它把 Claude Code 放进 agent systems design space，并讨论 future directions；本报告主要是单仓 source-grounded recovery。

## 本报告更强或更谨慎的地方

1. **版本与证据不越级。** “1,884 files 一致”只能给 strong fingerprint，不能给 exact identity；paper conclusion 也不直接当 S evidence。
2. **生命周期词更精确。** Session、一次用户 query、agentic iteration 与 API request 分开，避免把一个 tool loop 误叫一个 session/turn。
3. **条件计数更精确。** external modes 是五个；`auto` feature-gated 且 externalize 为 default；`bubble` internal-only。source union 不是 production UI census。
4. **安全声明保留反例空间。** canonical tool path 有 permission gate，不自动证明 startup、hooks、MCP lifecycle、bridge/daemon 的所有副作用都走同一 gate。[C: C-014]
5. **Subagent 不被压成一个盒子。** normal/fork、sync/async、worktree、in-process teammate 与 terminal-pane teammate 的 context/process/workspace/transcript/cancellation 边界分别描述。
6. **可审计产物更完整。** 每条重要结论回到 evidence ID；图只是解释层，HIR/claims/observations/scenarios 才是 structured truth。

## 对照时发现并纠正的实质问题

最重要的事实修正是 compaction source order。旧报告写成 `budget → microcompact → history snip`；逐语句检查 {src("src/query.ts", 365, "query.ts")} 后确认是 `budget → optional HISTORY_SNIP → microcompact → optional CONTEXT_COLLAPSE → autocompact`，之后才进入 hard-limit/recovery。[S: S-014] [C: C-007]

另外三处不是简单补字，而是改变模型：

- Plugins 从“另一种扩展”改为跨 hooks/commands/agents/skills/output styles/channels/MCP/LSP/settings/user-config 的 packaging layer。[S: S-046]
- Permission state 从“resume 恢复 mode”细化为“恢复 conversation metadata，但不反序列化 session-scoped grants”。[S: S-044] [C: C-029]
- 五 values/十三 principles 明确标 I evidence；官方材料只支撑 product stance，不把 analyst taxonomy 冒充作者原话。[D: D-001–D-008] [C: C-024, C-027]

## 图像质量差异与本次策略

论文图的优势是信息架构：有限颜色、清晰分组、箭头承担语义、一个 figure 只回答一个问题。弱点是部分标签把 build-time/internal/source-visible 机制并列，且图边没有逐条 evidence link。旧报告的 gpt-image-2 图更统一、视觉更轻，但缺少 layered architecture、extension injection 和 values-to-mechanisms 三个研究投影。

本次新增三张正文图的 story spec 与 gpt-image-2 prompt；由于自定义外部 API 的凭据发送在本轮被审批器拒绝，当前报告不嵌入这三张未生成图片。已有八张位图继续使用；全部图强制四项 caption contract：

- `question`：这张图只回答哪个问题；
- `glossary`：首次出现的缩写/项目内名词如何解释；
- `exclusions`：图明确不表达什么；
- `evidence_ids`：结构来自哪些 D/S/X/I records。

技术 SVG 继续保留为可重复生成的 evidence map，但正文只嵌入 gpt-image-2 PNG。生成图不是事实源；如果文字顺序、计数或箭头与 structured spec 冲突，就应拒收/重生成，而不是用 caption 修补错误图片。

## 剩余最高价值工作

当前最大差距不是再写一章，而是 **target runtime evidence 为零**。拿到同 commit 的 package/build artifact 后，优先运行：ordered context envelope capture、permission denied side-effect matrix、session-grant resume test、sync/async child inheritance matrix 与 compaction-before/after request digest。完成这些实验后，报告才会从 source-grounded architecture recovery 升级成 active harness archaeology。
"""


REPORTS["16-glossary.md"] = f"""# 全局术语表

{GLOSSARY_NOTICE}

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
"""


def main() -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    for name, content in REPORTS.items():
        (REPORT / name).write_text(content.strip() + "\n", encoding="utf-8")
    print(f"Wrote {len(REPORTS)} report chapters")


if __name__ == "__main__":
    main()
