# 产品立场、设计原则与实现机制

> **证据边界。** 本报告分析 source-only commit `16a676f`。其 1,884 个 TS/TSX 文件、关键 symbol 与 feature gates 和论文所述 Claude Code v2.1.88 corpus 强指纹一致，但缺少 package version、上游 tree hash、build manifest，不能视为已证明的 exact 官方 artifact。快照仍有 657 个无法解析的相对 import；除 SiFlow 协议探针外，主循环、安全、session 与 subagent 结论均为 static-only。官方材料只支持产品立场，五价值/十三原则是 analyst synthesis。[X: X-001–X-003] [D: D-001–D-008] [C: C-001, C-024–C-026]


> **读者图待生成。** 问题：first-party 产品立场如何经 analyst principle 映射到源码机制？ evidence-grounded story spec 与 gpt-image-2 prompt 已生成；外部图像 API 尚未获本轮风险授权，因此当前不嵌入占位图或技术 SVG。

## 先区分三层

- **Product stance（D）**：Anthropic 官方材料直接表达的目标或约束，例如 human oversight、read-only default、可验证执行、context scarcity 和可审计 memory。
- **Analyst principle（I）**：研究者把多份官方材料与源码重复模式归纳成的原则。下面的五价值与十三原则不是 Anthropic 发布的正式 architecture taxonomy。[C: C-024, C-027]
- **Mechanism（S）**：可在固定 commit 中定位的实现，例如 deny-first rule order、五阶段 compaction、四类 extension、JSONL 与 sidechain。

图的中栏标记 `ANALYST`，就是为了避免把解释框架伪装成作者原话。

## 五个产品立场

| 归纳价值 | First-party 依据 | 源码中可观察的对应机制 |
|---|---|---|
| Human decision authority | safe-agent framework 强调 autonomy 与 human control；Constitution 描述 principal-aware oversight [D: D-001, D-008] | read-only/default approval、deny/ask/allow、interrupt、resume 后不恢复 session grant [S: S-023, S-024, S-044] |
| Safety, security, privacy | auto mode 记录 approval fatigue 与四类威胁；sandbox 文档强调 FS/network boundary [D: D-003, D-004] | pre-filter、rules、classifier、hooks、optional sandbox、process-wide audit question [S: S-023–S-028] |
| Reliable execution | 官方工作流强调 loop 与可验证 outcome；context engineering 处理长任务 coherence [D: D-002, D-005] | shared query loop、ordered recovery、compaction、bounded shutdown [S: S-006–S-009, S-014, S-041] |
| Capability amplification | agentic loop、tools 与 progressive context 提供更大的 operational surface [D: D-002, D-005] | streaming/concurrent tools、MCP、skills、subagents、provider fallback [S: S-009, S-016–S-020, S-032] |
| Contextual adaptability | 官方 memory、context 与 team 文档描述 project instructions、auto memory 和 independent contexts [D: D-005–D-007] | CLAUDE.md/rules、lazy attachment、skills、MCP、agent definitions、sidechains [S: S-012, S-013, S-020, S-033] |

## 十三条 analyst-normalized principles

| 原则 | 回答的设计问题 | 主要机制 | 证据边界 |
|---|---|---|---|
| Deny-first with escalation | 未识别 action 默认 allow、deny 还是 ask？ | deny 优先、unmatched 路径按 mode ask/deny | D-001; S-023–S-024 |
| Graduated trust | autonomy 是单开关还是 spectrum？ | 5 个 external modes；`auto` feature-gated；`bubble` internal-only | S-023, S-044 |
| Defense in depth | 单一 gate 还是重叠边界？ | pre-filter、rules、hooks、classifier、sandbox、resume re-check | S-019, S-023–S-028, S-044 |
| Externalized programmable policy | policy hardcoded 还是可配置？ | settings rules、managed policy、27 hook events | S-023, S-024, S-043 |
| Progressive context management | context pressure 一步截断还是分级处理？ | budget → snip → microcompact → collapse → autocompact | S-014–S-015 |
| Append-oriented durable state | mutation、snapshot 还是 event log？ | transcript JSONL、boundary、sidechain、mailbox | S-029, S-037 |
| Minimal decision scaffolding | harness 替模型规划，还是让模型决定 action？ | simple query loop + dense deterministic infrastructure | S-006–S-009; I-005 |
| Judgment plus guardrails | guidance 与 deterministic enforcement 如何分工？ | CLAUDE.md/skills 引导；permission/sandbox enforce | S-012–S-013, S-023–S-027 |
| Composable extensibility | 一个 plugin API 还是不同语义机制？ | MCP、Plugins、Skills、Hooks | S-020, S-043, S-046 |
| Reversibility-weighted risk | read/write/remote action 是否同等治理？ | tool-specific rules、concurrency classes、worktree/rewind | S-009, S-023, S-031, S-035 |
| Transparent file-based memory | opaque DB 还是用户可编辑文件？ | CLAUDE.md、auto memory files、JSONL | D-006; S-012, S-029 |
| Isolated delegation context | child 是否继承完整 parent history？ | runAgent context/tool/MCP rebuild、sidechain、summary return | S-032–S-033, S-045 |
| Graceful recovery | 错误直接失败还是分级恢复？ | retry/fallback、reactive compact、interrupt cleanup | S-008, S-014, S-018, S-041 |

## First-party 材料索引

- [Safe and trustworthy agents](https://www.anthropic.com/news/our-framework-for-developing-safe-and-trustworthy-agents)：human control、read-only default 与 approval boundary。[D-001]
- [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)：agentic loop 与 verifiable outcomes。[D-002]
- [Claude Code auto mode](https://www.anthropic.com/engineering/claude-code-auto-mode) / [sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing)：approval fatigue、威胁分类与 FS/network isolation。[D-003–D-004]
- [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) / [memory](https://code.claude.com/docs/en/memory)：context scarcity、progressive disclosure、compaction、CLAUDE.md 与 auto memory。[D-005–D-006]
- [Agent teams](https://code.claude.com/docs/en/agent-teams) / [Claude's Constitution](https://www.anthropic.com/constitution)：independent teammate contexts 与 principal-aware oversight；后者是 model-level stance，不是 harness ADR。[D-007–D-008]

## 不能由这张表推出什么

同一机制可以服务多个价值，这不是一一因果映射。官方材料没有把这十三条命名成 Claude Code 的正式原则；因此它们保持 I evidence。要验证这些原则是否为 Claude Code 特有，还需要用相同 codebook 对其他 harness 独立编码。[I: I-003, I-005]
