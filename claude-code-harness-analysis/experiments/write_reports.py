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


NOTICE = "> **证据边界。** 本报告分析 source-only commit `16a676f`。其 1,884 个 TS/TSX 文件、关键 symbol 与 feature gates 和论文所述 Claude Code v2.1.88 corpus 强指纹一致，但缺少 package version、上游 tree hash、build manifest，不能视为已证明的 exact 官方 artifact。快照仍有 657 个无法解析的相对 import；除 SiFlow 协议探针外，主循环、安全、session 与 subagent 结论均为 static-only。官方材料只支持产品立场，五价值/十三原则是 analyst synthesis。[X: X-001–X-003] [D: D-001–D-008] [C: C-001, C-024–C-026]\n"

REPORTS: dict[str, str] = {}

REPORTS["index.md"] = f"""# Claude Code Harness 架构分析

{NOTICE}

## 核心结论

这个快照恢复出的核心不是一个“收到问题、调用一次模型、执行一个命令”的薄 CLI，而是共享、可递归的 `query()` 控制器。交互 REPL 与 print/SDK 各自准备 session、工具和 context，随后进入同一循环；循环可能在一个用户提交内发起多次 Anthropic Messages 请求，并在每次 `tool_use` 后经过验证、hook、权限、可选 sandbox、执行、`tool_result` 回填后继续。[S: S-004–S-009] [C: C-003–C-005]

{fig("claude-system-overview", "Claude Code 产品边界与 canonical path")}

**图怎么读。** 主线从左到右：界面进入 live session，session 调用 query loop，loop 调 Anthropic Messages，模型提出工具调用，Tool Router 再经过 Permission Gate 到执行后端。`Context Builder`、`Transcript JSONL` 和 `Subagents` 是主线的供给、持久化和递归分支。`Sandbox / Shell` 表示按配置选择 wrapper 后再执行，并不表示 sandbox 永远开启。{tech("system-overview")}

## 定义架构的五个选择

| 设计问题 | 该快照中的答案 | 主要代价 |
|---|---|---|
| 多界面是否共用控制器 | REPL 与 headless 都消费 `query()` | 界面状态与 headless mutable state 仍有差异 |
| context 如何增长 | 分层来源 + 每轮附件 + tool result carry-forward | 来源多且生命周期不同，压缩损失难静态量化 |
| 工具如何受控 | schema/validation → hook → permission → call | canonical gate 不自动证明所有子系统同等受控 |
| child 如何隔离 | context/tools/transcript 分开；workspace 默认共享，worktree 可选 | “subagent”不是单一 process/isolation 语义 |
| 什么是 durable state | transcript、sidechain、team inbox 和部分 metadata | resume 恢复会话，不回滚普通 workspace 文件 |

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

结构化真值位于 [HIR](../hir.json)、[claims](../evidence/claims.jsonl)、[observations](../evidence/observations.jsonl)、[coverage](../evidence/coverage.json) 和 [scenarios](../scenarios/catalog.json)。
"""


REPORTS["00-values-principles.md"] = f"""# 产品立场、设计原则与实现机制

{NOTICE}

{fig("claude-values-mechanisms", "Claude Code 产品立场、分析原则与源码机制")}

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
"""


REPORTS["00-design-space-and-running-example.md"] = f"""# 设计空间与静态 Running Example

{NOTICE}

## 六个设计问题

| 问题 | 当前机制 | 可替代方案 | 分析者判断 | 证据 |
|---|---|---|---|---|
| 界面与 loop 是否耦合 | 多入口，共用 query() | 每界面独立 controller | 共享语义减少漂移，state 适配面更大 | C-002–C-004 |
| context 是快照还是流水线 | startup、lazy、per-turn、durable 来源合流 | 每次重建完整 prompt | 有利于 cache/成本，却增加 provenance 与压缩复杂度 | C-006–C-007 |
| registry 是否等于可见工具 | 不是；组装、过滤、exposure、dispatch 分层 | 固定工具全集 | 动态能力面灵活，也更难证明实际暴露范围 | C-010–C-011 |
| approval 与 isolation 是否一件事 | permission 后才是可选 sandbox | 强制 sandbox、无交互审批 | 两层可独立配置，也容易混淆 | C-012–C-014 |
| child 默认共享什么 | context/tool/transcript 分开，workspace 默认共享 | 每 child 强制 worktree | 协作快，写冲突需由任务划分承担 | C-017–C-020 |
| resume 是否是 rollback | 恢复 JSONL，会话外文件继续存在 | 事务式 workspace snapshot | 符合 CLI 工作流，但不能当撤销 | C-015–C-016 |

收益、代价和替代方案均是分析者综合，不是作者动机。官方产品材料可作为 D evidence 支持 human control、sandbox、context scarcity、memory 与 team 等产品立场，但“五价值/十三原则”仍是分析者对 D 与 S 的归纳，不是 Anthropic 正式 taxonomy。[D: D-001–D-008] [I: I-003, I-005] [C: C-024, C-027]

## 静态 running example：一次需要工具的用户提交

{fig("claude-turn-flow", "一次 query 的模型工具循环")}

1. REPL 的 QueryGuard 获得执行权，或 headless QueryEngine 启动；两者准备 context 与工具后调用 query()。[S: S-004–S-006]
2. queryLoop 处理 tool-result budget、压缩候选和 hard limit，再构造一次模型请求。[S: S-007, S-014]
3. 若流中出现 tool_use，router 查找工具、验证 schema/input，运行 pre-tool hook 和 permission decision。[S: S-022–S-024]
4. 允许后，Bash 等工具可能先经过 sandbox wrapper，再由 Shell spawn；拒绝则生成模型可消费的 error result。[S: S-025–S-027]
5. tool_result 与运行时附件进入下一次 context；没有 tool call、达到 max turns、hook stop、abort 或不可恢复错误时退出。[S: S-008–S-009]

Model Stream 是一次 API request；Continue Loop 是同一用户提交中的下一次 agentic iteration；Stop 是 query() 的 terminal transition。三者都不等于 durable session。这个例子是源码路径演练，不是 runtime trace。{tech("turn-flow")}

不能由此推出：external bundle 包含所有 feature path、真实模型一定选某工具、permission denied 的 OS 层绝无副作用，或该路径在生产中的频率。
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

本轮 D 是 first-party 产品材料，S 是源码结构，X 是控制实验，I 是分析推断。没有 R，因为 target harness 未启动。论文只作为 prior-analysis benchmark 和反例线索，不直接作为实现真值。[C: C-024–C-026]

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

| 表面 | 主要对象 | 与 core 的关系 |
|---|---|---|
| Interactive REPL | React/Ink + AppState + QueryGuard | onQueryImpl 消费共享 query() |
| Print / SDK | QueryEngine + structured I/O | QueryEngine 消费共享 query() |
| MCP/server/bridge | 协议 runner | 是否进入主 loop 取决于子命令 |
| Resume/fork | sessionRestore + sessionStorage | 重建 live session 后进入相同 core |

## Session、query、iteration 与 API request

- **Session**：跨多个用户提交的容器，有 session ID、live state，并可对应 transcript JSONL。[S: S-029–S-031]
- **一次用户 query**：提交输入到这次 query() terminal transition。QueryGuard 防止两个主 query 同时运行，新消息可排队。[S: S-004]
- **Agentic loop iteration**：queryLoop 的一次 while(true)，通常取样一次、可能执行一组工具，再决定继续或 terminal。[S: S-006–S-008]
- **API request / model round**：对 Anthropic Messages 的一次请求。一个用户 query 可因工具回填、retry、fallback 或 recovery 含多个 request。[S: S-007, S-017–S-018]

所以“一个 turn 调几次模型”必须先定义 turn。本报告固定使用上述四个词。

生命周期是：bootstrap 选入口 → main 建配置/permission/provider/extensions/session → surface 接收输入并组 context → query loop → transcript 追加 → terminal 返回；signal 则进入 graceful shutdown。

--print 会跳过 workspace trust dialog，且 non-interactive 场景无法使用普通 UI approval；共用 loop 不表示治理体验完全相同。[S: S-003, S-024]
"""

REPORTS["03-core-loop.md"] = f"""# 共享核心循环

{NOTICE}

{fig("claude-turn-flow", "Claude Code query loop")}

{src("src/query.ts", 219, "query/queryLoop")} 初始化 messages、tool context、compaction tracking、recovery counters、stop-hook state、turnCount 和 transition，再进入 while(true)。[S: S-006]

## 一次 iteration 的九个语义阶段

| 顺序 | 阶段 | 关键事实 |
|---|---|---|
| 1 | State snapshot | 读取 mutable tool/context state、turnCount、transition 与 recovery counters |
| 2 | Boundary projection | 按 compact boundary 选择当前 message chain |
| 3 | Ordered context shaping | tool-result budget → 条件 HISTORY_SNIP → microcompact → 条件 CONTEXT_COLLAPSE → autocompact |
| 4 | Model request | 选择 provider/model，构造 system/messages/tools，启动 streaming request |
| 5 | Stream consumption | 逐块产出 assistant content，并识别实际 `tool_use` blocks |
| 6 | Tool scheduling | streaming-safe 工具可提前启动；连续 concurrency-safe calls 有界并发，其余串行 |
| 7 | Governed execution | lookup/schema → pre-hook → permission → 可选 sandbox → tool.call |
| 8 | Ordered reconciliation | 即使执行并发，tool results/context modifiers 仍按原 block 顺序合并 |
| 9 | Transition | tool_result/attachments 回填后 continue，或因 stop、budget、abort、不可恢复错误 terminal |

该表是从 {src("src/query.ts", 219, "query.ts")} 的真实源码顺序恢复，不是把论文中的视觉顺序反写成事实。[S: S-006–S-009, S-014] [C: C-004, C-007]

`query()`/`queryLoop()` 是 `AsyncGenerator`：它同时承载流式 UI 输出、model/tool events 和 terminal result；因此“流向界面的 event”与“写回下一轮模型的 message”是两个不同通道。Loop 以实际 `tool_use` blocks 决定 follow-up，而不只相信 stop_reason。[S: S-006–S-008]

并行也不是“所有工具一起跑”：连续 concurrency-safe calls 形成有上限批次，不安全工具串行；同批某些失败会取消 sibling，但结果与 context modifier 仍按原 block 顺序归并，避免执行完成顺序污染模型协议。[S: S-009, S-022]

unknown/schema/permission error 通常变为 model-facing tool_result；provider 失败由 retry 层处理；context overflow 可触发 reactive compaction；abort 会补 interruption result，避免协议悬空。这些均为 static-only。{tech("turn-flow")}
"""



REPORTS["04-context-memory-compaction.md"] = f"""# Context、Memory 与 Compaction

{NOTICE}

{fig("claude-context-lifecycle", "Claude Code context lifecycle")}

| 图中标签 | 生命周期 | 典型内容 |
|---|---|---|
| System Prompt | startup/reload，部分 section 动态重算 | tone、task policy、tool/mode guidance |
| CLAUDE.md + Rules | startup/lazy | managed/user/project/local、rules、add-dir |
| History JSONL | durable/carry-forward | user/assistant/tool chain、compact boundary |
| Runtime Attachments | per-turn | MCP/agent delta、skills、memory、tasks、diagnostics、queue |

{src("src/utils/claudemd.ts", 1, "claudemd.ts")} 保留来源 provenance，并处理多层目录、@include 和外部 include approval；{src("src/utils/attachments.ts", 1, "attachments.ts")} 区分 user-triggered、every-thread 与 main-only attachment。[S: S-012–S-013]

## Context 是有结构的位置，不只是字符串拼接

System prompt/context 放产品约束、tool/mode guidance 与稳定环境信息；user context 则把 CLAUDE.md、memory、skills、MCP/agent/tool delta 和 runtime attachments 以可追踪来源带入消息链。`CLAUDE.md` 还分 managed、user、project、local 与目录层级，可通过 `@include` 引入外部文件；auto memory 是可审计文件，不等于 transcript。[D: D-005–D-006] [S: S-010–S-013]

## Compaction 不是一个摘要按钮

| 实际顺序 | Stage | 条件 | 主要效果 |
|---|---|---|---|
| 1 | Tool-result budget | 常规路径 | 压低旧工具结果占用，不先改写完整对话 |
| 2 | History snip | `HISTORY_SNIP` | 投影掉满足条件的历史段 |
| 3 | Microcompact | 常规路径；cache 另受 feature 控制 | 更细粒度清理旧内容/结果 |
| 4 | Context collapse | `CONTEXT_COLLAPSE` | 条件性折叠更大历史结构 |
| 5 | Autocompact | threshold/config | 生成 summary boundary 并重注入必要状态 |
| 6 | Hard-limit recovery | 前述不足时 | prompt-too-long/max-output 的恢复或终止 |

这个顺序直接来自 {src("src/query.ts", 365, "query.ts ordered shapers")}；早先报告把 microcompact 与 history snip 颠倒，已由逐语句 source-order audit 纠正。[S: S-014] [C: C-007]

`compactConversation` 通过另一次模型调用生成 summary boundary，再有限重注入近期文件、plan、skill、MCP/agent/tool delta。[S: S-015] 这些机制分别可能清理旧结果、投影历史段，或用摘要替换历史。Memory 与 transcript 都会进入 context，但前者是可维护知识来源，后者是 durable execution history；所有权和恢复语义不同。[S: S-012–S-015, S-029]

最大未知项是摘要信息损失、实际 threshold、启用的 feature projection 和长任务语义漂移。需要可运行构建强制 overflow，再比较压缩前后 request envelope 与 resume。{tech("context-lifecycle")}
"""

REPORTS["05-models-tools-extensions.md"] = f"""# 模型、工具与扩展

{NOTICE}

{fig("claude-tool-surface", "Claude Code tool and extension surface")}

## 图中层次

- **Built-in Tools**：Bash、Read/Edit/Write、search、Agent、Task、plan 等；进入 pool 仍受 mode、feature、deny 和 enabled state 影响。[S: S-019]
- **MCP Servers**：运行时外部 capability provider；连接 lifecycle 与一次 tool invocation 不是同一步。[S: S-020]
- **Plugins**：是 packaging/distribution 层，不是单一 runtime injection point。manifest 除 metadata 外可组合 hooks、commands、agents、skills、output styles、channels、MCP、LSP、settings 与 user config 十类 component surfaces。[S: S-046]
- **Skills**：主要把 prompt/workflow 内容按需注入 context，不天然构成 executable sandbox；其低初始 context cost 来自 progressive disclosure，而不是“免费”。[D: D-005] [S: S-013, S-033]
- **Tool Pool**：当前候选集合；built-in 在同名冲突时优先，并稳定排序。[S: S-020]
- **Visible Schemas**：真正发送给模型的 schemas。registry 存在不保证这一轮可见。[S: S-019–S-021]
- **Tool Router**：lookup、schema/input validation、hooks 和 permission 的共同执行路径。[S: S-022]
- **Tool Result**：映射为模型可消费内容；过大结果可能落盘，只返回 preview/path。

## Provider 与 retry

{src("src/services/api/client.ts", 88, "getAnthropicClient")} 选择 direct Anthropic、Bedrock、Vertex 或 Foundry。{src("src/services/api/claude.ts", 1480, "Messages request builder")} 负责 messages/system/tools、thinking、cache/beta headers 与 stream；{src("src/services/api/withRetry.ts", 170, "withRetry")} 处理 auth refresh、429/529、backoff、fallback 和 token correction。[S: S-016–S-018]

## SiFlow 结果

models route 返回 qwen3.6-35ba3b 与 262,144 context；Anthropic /v1/messages 非流式和 SSE 均 HTTP 200；带 tool_choice=echo 与 enable_thinking=false 时返回 tool_use，input 为 {{"text":"hello"}}。[X: X-002]

这证明协议子集可用，不证明完整 Claude Code request 兼容。真实 envelope 还含 beta headers、thinking/output config、prompt caching、复杂 schemas 与多轮 tool_result。[C: C-009, C-025]

六个不要混淆的等号：installed plugin ≠ enabled plugin；registered tool ≠ visible schema；visible ≠ model 一定调用；tool call ≠ permission allow；allow ≠ sandbox enabled；skill loaded ≠ 独立进程执行。{tech("tool-extension-surface")}

## 四类扩展注入的是不同语义位置

{fig("claude-extension-injection", "Claude Code 扩展注入位置与 context 成本")}

| 机制 | 主要注入点 | 模型/loop 实际得到什么 | Context 成本与治理 |
|---|---|---|---|
| Skills | Assemble | 描述先可发现，命中后再加载详细 instruction/resource | 初始低、使用后增长；内容指导不等于权限 |
| MCP Servers | Model surface + execute | 动态 tool schemas/resources/prompts，调用时走 MCP client lifecycle | schema 常驻或按需暴露；实际 tool call 仍需治理 |
| Hooks | Assemble、authorize/execute、lifecycle | 27 个 event 的观察、修改、阻断或外部命令回调 | event-driven；并非每个 hook 都进入 model context |
| Plugins | Packaging fan-out | 把上述机制及 commands/agents/LSP 等一起分发和配置 | 自身没有一种统一 context 或 execution 语义 |

这张图按“模型看见什么、模型能调用什么、动作能否/如何执行”分层，而不是按目录或安装格式分组。27 是当前 `HOOK_EVENTS` 常量的源码计数；十类是 manifest component groups，均受 snapshot/feature/config 条件限制，不能外推成所有生产构建始终启用。[S: S-043, S-046] [C: C-028]
"""

REPORTS["06-permissions-sandbox-workspace.md"] = f"""# 权限、Sandbox 与 Workspace

{NOTICE}

{fig("claude-permission-pipeline", "Claude Code permission pipeline")}

共享 toolExecution 先做 schema/tool validation，再运行 pre-tool hooks，随后 permission resolver。{src("src/utils/permissions/permissions.ts", 560, "hasPermissions")} 综合 blanket deny、ask rules、tool check、tool deny、interaction requirement、safety、mode、allow rule 与 passthrough。[S: S-022–S-024]

外部 schema 固定五种 mode：`default`、`acceptEdits`、`dontAsk`、`plan`、`bypassPermissions`。`auto` 只有 `TRANSCRIPT_CLASSIFIER` 构建中才加入 user-addressable runtime set，并对 external serialization 映射回 `default`；`bubble` 只属于 internal union，不在 runtime validation set。论文或图把它们直接数成七个并列用户模式会夸大可用表面。[S: S-023, S-044]

| Mode | 重点 | 不能误读为 |
|---|---|---|
| default | 规则匹配后按需 ask | 所有工具都弹窗 |
| acceptEdits | 对编辑更宽松，其他能力仍看规则 | 全部 allow |
| dontAsk | 无法自动决定时避免交互，通常 fail closed | bypass |
| plan | 限制实现型动作 | read-only OS sandbox |
| bypassPermissions | 显式绕过 canonical decision | 环境绝对安全 |
| feature-gated auto | classifier + 特殊 safety path | external schema 的第六个稳定 mode |
| internal bubble | child/dialog 传播语义 | 用户可在 CLI/settings 选择的 mode |

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

## 静态 inheritance matrix

| 维度 | 普通 Agent child | Async child | Worktree child | Swarm teammate |
|---|---|---|---|---|
| Model/context | child 自己构建 | child 自己构建 | child 自己构建 | teammate runner 自己维护 |
| Tool pool | 按 child permission/mode 组装 | 同左，non-interactive | 同左 | 由 teammate runtime/mode 决定 |
| Transcript | sidechain JSONL | sidechain + task output/notification | sidechain + worktree metadata | task state + team files/mailbox |
| Workspace | 默认共享 cwd | 默认共享 cwd | 独立 worktree | backend/config dependent |
| 主请求 ESC | 通常有关联 | 不自动跟随；显式 kill | 取决 sync/async | 独立 controller，可单独 abort |
| Result channel | tool result | task notification | result + retained path | mailbox/task notification |

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

## Live 与 durable state

| 状态 | 所有者 | 是否 durable | 恢复含义 |
|---|---|---|---|
| Live Session | 进程/AppState | 否 | 重启后重建 |
| Message chain | transcript JSONL | 是 | 通过 parentUuid 重建会话视图 |
| Child transcript | subagents/agent-*.jsonl | 是 | 用 agent metadata 选择/恢复 child |
| Compaction boundary | transcript entry | 是 | 指定被摘要/保留 segment 的新边界 |
| Team inbox | ~/.claude/teams | 是 | unread message 可跨进程被 attachment 消费 |
| Workspace files | 当前 cwd/git worktree | 外部持久状态 | 不随 session resume 自动回滚 |
| Worktree path metadata | session/agent metadata | 条件 durable | 路径仍存在时可恢复 cwd |

{src("src/utils/sessionStorage.ts", 500, "sessionStorage")} 使用项目路径派生目录和 sessionId JSONL，主消息与 sidechain 分开；parentUuid 形成逻辑链。写入有 queue/flush，compact/snip 后会重连 dangling parent 或重写可恢复 segment。[S: S-029]

## Resume 与 fork 的精确差别

- **Resume**：默认继续原 sessionId，加载 transcript/metadata，恢复 agent/mode、file history attribution、todo、worktree path 等可用信息。
- **Fork**：保留启动时的新 sessionId，同时复制可恢复 history 与部分 replacement metadata；它是会话身份分叉，不是 git branch 或文件快照。
- **Rewind files**：CLI 另有显式 file-history rewind，说明普通 resume/fork 本身不等于 filesystem rollback；它也不是任意 workspace/process 的通用 checkpoint。[S: S-030–S-031]
- **Permission freshness**：resume/fork 不从 transcript 反序列化旧 session 的临时 allow/deny/ask grants；新进程从当前 settings 与 CLI 参数重建 permission context。[S: S-044] [C: C-029]

所以 durable transcript 保存“发生过什么”，不自动保存“现在仍被授权做什么”。若恢复后再次请求同一 Bash action，正确的验证实验是观察是否重新 ask，而不是只检查 mode label。

## Compaction 与 persistence

Compact summary 不只是内存中替换 messages：boundary、preserved segment 和重注入 metadata 会影响之后 JSONL chain 如何加载。大文件读取还会做 byte-level prefilter、dead-branch pruning 和 parent chain reconstruction；这使恢复具有明确算法，而不是简单读取所有 JSON 行。[S: S-015, S-029]

## Crash/exit recovery

Graceful shutdown 把 cleanup/persistence 放在 SessionEnd hooks 和 analytics 之前，并用 2 秒 cleanup race、hook budget、analytics 500ms cap 与最终 failsafe 限制退出时间。[S: S-041]

静态代码尚不能回答 corrupted JSONL 是 fail closed、局部修复还是丢弃到什么粒度，也不能证明 abrupt SIGKILL 时最后一批 buffered writes 的边界。需要 resume/fork/corruption/signal 四组实验。{tech("persistence-lifecycle")}
"""

REPORTS["09-observability-evaluation.md"] = f"""# 观测、Tracing 与评估边界

{NOTICE}

{fig("claude-observability-recovery", "Claude Code observability and recovery layers")}

## 四类观测面

| 图中标签 | 机制 | 默认/条件 | 能回答什么 |
|---|---|---|---|
| Events | analytics logEvent queue + sinks | sink 初始化、sampling/config | feature/tool/error 计数与属性 |
| OTel spans | interaction、LLM、tool、hook | enhanced/beta telemetry gate | parent-child timing、tokens、success/error |
| Query Profiler | performance marks + memory snapshot | CLAUDE_CODE_PROFILE_QUERY | context/model/tool 前后阶段耗时 |
| Perfetto Trace | Chrome trace event + agent registry | feature/user/env gated | agent hierarchy、TTFT/TTLT、tool spans |

{src("src/utils/telemetry/sessionTracing.ts", 176, "sessionTracing")} 用 AsyncLocalStorage 保存 interaction/tool context，并为并发 LLM request 要求显式传回对应 span，避免 response 绑错。默认 prompt 内容会 redacted，只有显式 env 才记录。[S: S-039]

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

| 决策 | First-party stance（D） | 当前机制（S） | Analyst tradeoff / 反例测试（I/X） | 证据 |
|---|---|---|---|---|
| 多 surface 共用 query() | 官方描述 iterative agentic loop 与 verifiable outcomes | REPL/QueryEngine 适配后进入同一 generator | 核心语义复用；需双入口 scripted diff 验证 UI/headless 差异 | D-002; C-003–C-004 |
| Context 按生命周期合流 | context 是有限资源，应 progressive disclosure/compact | prompt、CLAUDE.md、history、attachments；五阶段 shaper | provenance 强但有顺序/摘要漂移；逐项 ablation | D-005–D-006; C-006–C-007 |
| Registry 与 exposure 分离 | capability 应按任务逐步呈现 | pool/filter/schema/dispatch 四层 | 动态 MCP/deferred tools；同名/disabled matrix | D-005; C-010, C-028 |
| Permission 与 sandbox 分离 | human control + bounded autonomy | policy decision 后条件 sandbox wrapper | 两层可组合但易把 allow 误读为 isolated；side-effect matrix | D-001, D-003–D-004; C-012–C-014 |
| Child context 分离、workspace 默认共享 | subagent/team 使用 independent context | runAgent + optional worktree | 节省主 context；共享文件会冲突；并发 same-file experiment | D-005, D-007; C-017–C-020 |
| JSONL append + parent chain | memory 应可检查、可编辑、可延续 | session/sidechain JSONL，resume 不恢复 session grants | 易审计/分叉；corruption 与 trust freshness 需注入测试 | D-001, D-006; C-015–C-016, C-029 |
| 多层 telemetry | 没有足够 first-party 架构意图 | events、OTel、profiler、Perfetto | 粒度可选；correlation/privacy 配置复杂 | C-021 |
| Cleanup 优先的有界 shutdown | 没有足够 first-party 架构意图 | persistence → hooks → analytics → failsafe | 降低关键状态丢失；hung cleanup test | C-022 |

## 架构上最值得迁移的三点

第一，工具“存在、可见、被调用、被允许、被隔离、成功执行”应建模为六个状态，不应压成一个 capability edge。第二，subagent 隔离需要 context/process/workspace/policy/transcript/cancellation 六维矩阵。第三，resume 必须把 conversational state 与 external workspace state 分开描述。

## 不应迁移的假确定性

不能把 source-visible feature 当 production feature，不能把 analyst-normalized principle 冒充 Anthropic 官方 taxonomy，也不能把 provider probe 当 end-to-end harness validation。[C: C-023–C-027]
"""

REPORTS["11-runtime-experiments.md"] = f"""# 运行实验

{NOTICE}

## 已执行

| ID | 问题 | 设置 | 结果 | 能证明什么 |
|---|---|---|---|---|
| X-SCENARIO-001 | snapshot 能否自包含运行 | clean commit；静态 import resolver | 657 missing relative imports；无 manifest | 当前快照不满足 target runtime 前置条件 |
| X-SCENARIO-002 | SiFlow 是否支持关键 Anthropic 方言 | 无凭据、无私有 prompt；qwen3.6-35ba3b | models/messages/SSE/tool_use 均 HTTP 200 | provider 协议子集可用 |
| X-SCENARIO-008 | 本地快照与论文 v2.1.88 corpus 是否同源 | 文件计数 + 高辨识度 symbol/feature fingerprint | 1,884 TS/TSX 精确匹配，关键机制同名 | strong match；不能证明 exact tree |

Provider probe 的 forced call 是 echo({{"text":"hello"}})，并使用 chat_template_kwargs.enable_thinking=false，避免默认 thinking 消耗短输出预算。原始内容仅含合成 prompt，sanitized 结果保存在 [provider-probe.json](../experiments/provider-probe.json)。[X: X-002]

## 未执行及原因

| ID | 场景 | 目标 claim | 阻塞 |
|---|---|---|---|
| X-SCENARIO-003 | scripted text-only query | C-003/C-004 | 无闭合 module/build graph |
| X-SCENARIO-004 | permission deny 无 side effect | C-012–C-014 | 无可启动 target |
| X-SCENARIO-005 | context overflow | C-006/C-007 | 无可启动 target |
| X-SCENARIO-006 | resume/fork | C-015/C-016 | 无可启动 target |
| X-SCENARIO-007 | child inheritance matrix | C-017–C-020 | 无可启动 target |

“blocked”不表示机制不存在，只表示本轮不能形成 R/X evidence。为了避免把 injector 行为冒充原系统，本报告没有手工补齐 657 个 import、伪造 package.json 或用 Python 重写 query loop。

## 下一轮最小 runtime package

需要同 commit 对应的 package.json/lock、完整 source map contents、bun:bundle feature manifest 或已编译外部 bundle。然后先跑 version/help，再用 query/deps.ts 的 callModel seam 做 deterministic tool loop；最后才接真实 SiFlow endpoint。
"""

REPORTS["12-failure-modes.md"] = f"""# 失败模式与开放问题

{NOTICE}

## 对分析结论影响最大的风险

1. **Snapshot identity gap**：1,884-file/symbol fingerprint 强匹配论文 v2.1.88 corpus，但无 package version/tree hash/build manifest。缓解：所有 source URL 固定 commit，身份写 strong fingerprint 而非 exact。[C-001, C-026]
2. **Feature reachability ambiguity**：feature() 分支可能被 DCE。缓解：mode/extension/hook 计数都写条件，图不把 source-visible 分支标 runtime verified。[C-023]
3. **Process-wide policy gap**：canonical tool gate 很清楚，但 hooks/startup/MCP 等需独立 reachability audit。这是 open claim，不宣称已有 bypass。[C-014]
4. **Compaction semantic loss**：静态可列保留项，不能量化 summary 丢失。[C-007]
5. **Child isolation ambiguity**：普通 child、async、worktree、teammate/pane 的边界不同；用一个 subagent 标签会造成安全误判。[C-017–C-020]
6. **Session/workspace confusion**：resume/fork 不自动回滚普通 files。[C-016]
7. **Telemetry blind spot**：本轮没有 target spans，无法报告性能、成本和频率。[C-021, C-025]

## 优先实验队列

| 优先级 | 可证伪问题 | 判别数据 |
|---|---|---|
| P0 | 哪个 feature set 构成 external bundle | build manifest、bundle strings、entrypoint reachability |
| P0 | 非 canonical side effects 是否有等价 policy | process/file/network trace + permission events |
| P1 | sync/async/teammate 实际 inheritance | pid、cwd、tools、mode、abort、transcript matrix |
| P1 | compact 后再 resume 保留什么 | request digest、boundary、restored history |
| P2 | concurrent tools 的真实排序 | start/end span 与 context modifier order |
| P2 | corrupted JSONL 如何降级 | controlled byte corruption + resume result |

## 产品风险与分析限制要分开

“某机制尚未验证”是分析限制；“源码显示存在无 gate 的副作用路径”才可能是产品风险。本轮只把 C-014 保留为待审计边界，没有将未运行状态包装成漏洞结论。
"""



REPORTS["13-coverage-reproducibility.md"] = f"""# 覆盖率与复现

{NOTICE}

## 14 模块覆盖

| Module | 状态 | 重点文件 | Runtime |
|---|---|---|---|
| interfaces | partial | cli.tsx、main.tsx、REPL、QueryEngine | 无 |
| core_loop | partial | query.ts、query/config、query/deps | 无 |
| context_assembly | partial | context、prompts、claudemd、attachments | 无 |
| compaction | partial | autoCompact、compact、microCompact | 无 |
| model_abstraction | partial | client、claude、withRetry、providers | 仅 provider probe |
| tools_extensions | partial | Tool、tools、toolExecution、orchestration | 无 |
| permissions_safety | partial | permissions types/engine、useCanUseTool | 无 |
| sandbox_execution | partial | BashTool、shouldUseSandbox、sandbox-adapter、Shell | 无 |
| workspace | partial | cwd、worktree、AgentTool | 无 |
| sessions_persistence | partial | sessionStorage、sessionRestore | 无 |
| subagents | partial | AgentTool、runAgent、spawnInProcess | 无 |
| orchestration | partial | query、toolOrchestration、coordinatorMode | 无 |
| observability | partial | analytics、sessionTracing、Perfetto | 无 |
| recovery | partial | withRetry、gracefulShutdown、compact | 无 |

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


def main() -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    for name, content in REPORTS.items():
        (REPORT / name).write_text(content.strip() + "\n", encoding="utf-8")
    print(f"Wrote {len(REPORTS)} report chapters")


if __name__ == "__main__":
    main()
