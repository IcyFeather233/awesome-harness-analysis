# 产品立场、设计原则与实现机制

> **证据边界。** 本报告分析 source-only commit `16a676f`。其 1,884 个 TS/TSX 文件、关键 symbol 与 feature gates 和论文所述 Claude Code v2.1.88 corpus 强指纹一致，但缺少 package version、上游 tree hash、build manifest，不能视为已证明的 exact 官方 artifact。快照仍有 657 个无法解析的相对 import；除 SiFlow 协议探针外，主循环、安全、session 与 subagent 结论均为 static-only。官方材料只支持产品立场，五价值/十三原则是 analyst synthesis。[X: X-001–X-003] [D: D-001–D-008] [C: C-001, C-024–C-026] 首次遇到缩写或内部名词时，可查 [全局术语表](16-glossary.md)。


> **读者图待生成。** 问题：first-party 产品立场如何经 analyst principle 映射到源码机制？ evidence-grounded story spec 与 gpt-image-2 prompt 已生成；外部图像 API 尚未获本轮风险授权，因此当前不嵌入占位图或技术 SVG。

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
