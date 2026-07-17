#!/usr/bin/env python3
"""Compile the Claude Code source-snapshot evidence model."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TARGET = Path("/volume/med/work/users/mzchen/work/claude-code")
COMMIT = "16a676ffa36eadbfb28eec39007dff73941346b1"
SOURCE = f"https://github.com/IcyFeather233/claude-code/blob/{COMMIT}"
MODULES = [
    "interfaces", "core_loop", "context_assembly", "compaction",
    "model_abstraction", "tools_extensions", "permissions_safety",
    "sandbox_execution", "workspace", "sessions_persistence", "subagents",
    "orchestration", "observability", "recovery",
]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, values: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(v, ensure_ascii=False, sort_keys=True) + "\n" for v in values),
        encoding="utf-8",
    )


def source_url(path: str, line: int) -> str:
    return f"{SOURCE}/{path}#L{line}"


def evidence(
    evidence_id: str,
    kind: str,
    summary: str,
    supports: list[str],
    *,
    path: str | None = None,
    line: int | None = None,
    end: int | None = None,
    symbol: str | None = None,
    command: str | None = None,
    scenario: str | None = None,
    confidence: str = "high",
    conditions: dict | None = None,
    notes: str | None = None,
    url: str | None = None,
    locator: str | None = None,
) -> dict:
    record = {
        "id": evidence_id,
        "record_type": "evidence",
        "kind": kind,
        "summary": summary,
        "source": {
            "locator": locator or (f"{path}:{line}" if path and line else (scenario or command or "analysis artifact")),
            "path": path,
            "start_line": line,
            "end_line": end,
            "symbol": symbol,
            "url": url or (source_url(path, line) if path and line else None),
            "scenario_id": scenario,
            "trace_id": None,
            "command": command,
        },
        "supports_claims": supports,
        "contradicts_claims": [],
        "conditions": conditions or {},
        "confidence": confidence,
    }
    if notes:
        record["notes"] = notes
    return record


def claim(
    claim_id: str,
    statement: str,
    scope: str,
    evidence_ids: list[str],
    modules: list[str],
    falsification: str,
    *,
    confidence: str = "high",
    status: str = "supported",
    importance: str = "high",
    conditions: dict | None = None,
    notes: str | None = None,
) -> dict:
    record = {
        "id": claim_id,
        "record_type": "claim",
        "statement": statement,
        "scope": scope,
        "importance": importance,
        "status": status,
        "evidence_ids": evidence_ids,
        "counterevidence_ids": [],
        "confidence": confidence,
        "conditions": conditions or {},
        "coverage_refs": modules,
        "falsification_test": falsification,
    }
    if notes:
        record["notes"] = notes
    return record


CLAIMS = [
    claim("C-001", "分析对象是 commit 16a676f 的 source-only 镜像：没有 tag、package manifest、lockfile 或 tsconfig，且 657 个相对 import 无法在快照内解析；它不能证明某个官方发布版本的完整构建配置。", "source snapshot integrity", ["S-001", "X-001"], ["interfaces", "recovery"], "取得对应 npm 构建产物与 manifest 后重跑 import/build；若所有依赖闭合且版本可追溯，则缩小该限制。"),
    claim("C-002", "CLI bootstrap 先分派 version、MCP、bridge、daemon、后台会话等快速路径，再进入 Commander 主入口；默认交互、print/headless、server/remote 等是不同产品表面。", "source-visible entrypoints", ["S-002", "S-003"], ["interfaces"], "对编译后的 external build 枚举 argv，记录实际可达入口；当前 feature() 构建值未知。", confidence="medium"),
    claim("C-003", "交互 REPL 与 headless QueryEngine 在各自完成上下文和工具准备后，都调用共享 query() generator，因此核心模型/工具循环不是两套实现。", "interactive and headless paths", ["S-004", "S-005", "S-006"], ["interfaces", "core_loop"], "在可运行构建中分别执行相同 scripted tool call，比较 query trace；本快照无法执行。"),
    claim("C-004", "query() 是显式可变状态循环：每轮整理上下文、选择模型、流式取样、收集 tool_use、执行工具并把结果附回消息，直到停止、限制、hook 或错误终止。", "shared query loop", ["S-006", "S-007", "S-008"], ["core_loop", "orchestration", "recovery"], "注入 deterministic callModel，覆盖纯文本、一次工具、未知工具、maxTurns 和中断；依赖注入点存在但快照不可构建。"),
    claim("C-005", "工具结果不是旁路日志，而是 user-role tool_result 与附件，进入下一次模型请求；streaming-safe 工具可以在模型流结束前启动，其他工具在流后批量调度。", "tool follow-up path", ["S-007", "S-009"], ["core_loop", "tools_extensions", "context_assembly"], "第二个 scripted 响应必须看到第一轮 tool_use_id 才返回验证码；当前未执行。", confidence="medium"),
    claim("C-006", "模型上下文由 system prompt、user context、system context、历史消息、CLAUDE.md/rules、memory/skills、MCP/agent/tool delta 和每轮附件分层组装；不同来源具有 startup、per-turn、lazy 与 durable 生命周期。", "context assembly", ["S-010", "S-011", "S-012", "S-013"], ["context_assembly"], "逐项关闭 CLAUDE.md、skills、MCP、memory 和动态附件并比较 request envelope；仅静态恢复。", confidence="medium"),
    claim("C-007", "上下文压力处理不是单一摘要：tool-result budget → 可选 history snip → microcompact → 可选 context collapse → autocompact → hard-limit recovery 按源码顺序协作；legacy compaction 会生成摘要边界并重注入近期文件、plan、skill 与动态 delta。", "compaction pipeline", ["S-014", "S-015"], ["compaction", "context_assembly", "recovery"], "构造超大 tool result 和临界 token estimate，分别触发各分支并检查保留项；未执行。", confidence="medium"),
    claim("C-008", "模型边界基于 Anthropic Messages，provider 可切换 direct、Bedrock、Vertex 和 Foundry；retry 自行管理 429/529、auth refresh、stream-to-nonstream fallback 与可选 model fallback。", "model abstraction", ["S-016", "S-017", "S-018"], ["model_abstraction", "recovery"], "对每个 provider 注入 401、429、529 和断流，核对重建 client、backoff 与 fallback；仅 direct endpoint 做了协议探针。", confidence="medium"),
    claim("C-009", "用户提供的 SiFlow endpoint 在 2026-07-16 接受 Anthropic /v1/messages、SSE event stream 和强制 tool_use；关闭默认 thinking 后返回 echo({text: hello})。这只证明协议子集，不证明当前源码快照可运行。", "SiFlow qwen3.6-35ba3b probe", ["X-002"], ["model_abstraction"], "用完整编译版 Claude Code 的真实 request envelope 执行多轮工具回填；当前因 source-only snapshot 未完成。", conditions={"provider": "siflow/qwen3.6-35ba3b"}),
    claim("C-010", "能力面由 built-in tools、动态 MCP、plugins、skills、hooks 与 deferred discovery 合成；tool registry 的存在、当前模型可见性和执行时启用状态是不同层。", "capability assembly", ["S-019", "S-020", "S-021"], ["tools_extensions", "context_assembly"], "注册同名 built-in/MCP tool 并切换 deferred/disabled 状态，比较 prompt schema 与 dispatch；未执行。", confidence="medium"),
    claim("C-011", "连续 concurrency-safe 工具组成并发批次，非安全工具串行；工具输入验证、pre-tool hooks、权限决策、tool.call、post-processing 和结果持久化由共享执行器串联。", "tool execution", ["S-009", "S-022"], ["tools_extensions", "orchestration"], "脚本化两个只读工具和一个写工具，记录开始/结束序；未执行。", confidence="medium"),
    claim("C-012", "权限管线综合 blanket rules、ask/deny/allow rules、tool-specific check、interaction requirement、safety checks 和 permission mode；bypassPermissions 是显式特殊模式，而不是默认路径。", "canonical permission path", ["S-023", "S-024"], ["permissions_safety"], "在 default/dontAsk/plan/bypass 下请求同一 Bash 写入并检查进程是否创建；未执行。", confidence="medium"),
    claim("C-013", "Bash 的 sandbox 由平台可用性、settings、excluded commands 和 per-call dangerouslyDisableSandbox 决定；sandbox 关闭时权限仍是主要治理边界，开启时命令经 sandbox-runtime 包装后再 spawn。", "Bash execution boundary", ["S-025", "S-026", "S-027"], ["sandbox_execution", "permissions_safety", "workspace"], "在 Linux disposable workspace 比较 sandbox on/off、deny/allow 与 unsandbox override 的文件/网络副作用；未执行。", confidence="medium"),
    claim("C-014", "canonical tool gate 不能自动代表整个进程的全部副作用路径；hooks、MCP server lifecycle、startup/bridge/daemon 和内部维护路径需要独立审计。当前只恢复了入口和 hook/MCP 结构，尚未证明所有路径共享同一 PermissionGate。", "process-wide safety boundary", ["S-003", "S-020", "S-028", "I-001"], ["permissions_safety", "sandbox_execution", "tools_extensions"], "对所有 child_process/fs/network call site 做 reachability + runtime syscall matrix，寻找绕过 canonical toolExecution 的副作用。", confidence="low", status="open"),
    claim("C-015", "session transcript 以项目目录下的 append-oriented JSONL 持久化，主线程与 subagent sidechain 分文件，消息通过 parentUuid 形成链，compact/snip 会重连或重写可恢复视图。", "session persistence", ["S-029"], ["sessions_persistence", "context_assembly"], "运行两轮、并行 tool results、compact 后重启，核对 JSONL 链与恢复消息；未执行。", confidence="medium"),
    claim("C-016", "resume 默认复用 sessionId，--fork-session 生成新 sessionId 但复制历史与部分元数据；文件工作区不是会话回滚，普通 cwd 的外部状态继续存在，worktree 路径可单独恢复。", "resume and fork", ["S-030", "S-031"], ["sessions_persistence", "workspace", "recovery"], "修改文件后分别 resume/fork，比较 sessionId、history 和 workspace；未执行。", confidence="medium"),
    claim("C-017", "普通 AgentTool 子代理、fork child、后台 agent、coordinator worker 与 swarm teammate 是不同机制；不能用一个统一的“独立进程 child”描述它们。", "delegation mechanisms", ["S-032", "S-033", "S-034"], ["subagents", "orchestration"], "逐种机制记录 process id、context、abort controller、transcript 和 result channel；未执行。", confidence="medium"),
    claim("C-018", "runAgent 为普通 subagent 构建独立 system/user context、工具池、MCP 客户端与 sidechain transcript，并递归调用 query()；同步 agent 共享部分 AppState callback，异步 agent 使用独立 abort controller 且不随主请求 ESC 自动中断。", "AgentTool child context", ["S-032", "S-033", "S-045"], ["subagents", "context_assembly", "recovery"], "对 sync/async child 触发 ESC、permission prompt 与 MCP call，比较共享/隔离矩阵；未执行。", confidence="medium"),
    claim("C-019", "subagent 的 worktree isolation 是可选项：默认没有由 AgentTool 自动提供独立 workspace；启用后在 child cwd 运行，结束时无改动可清理，有改动则保留并返回路径。", "AgentTool workspace isolation", ["S-032", "S-035"], ["subagents", "workspace"], "让 default 与 isolation=worktree child 修改同一路径，观察主工作树与清理结果；未执行。", confidence="medium"),
    claim("C-020", "swarm teammate 可在进程内运行，也可由 tmux/iTerm pane backend 承载；团队消息通过 ~/.claude/teams/<team>/inboxes/*.json 加文件锁投递，属于 durable mailbox 而不是共享内存消息总线。", "team/swarm topology", ["S-034", "S-036", "S-037"], ["subagents", "orchestration", "sessions_persistence"], "跨两个进程并发写同一 inbox，检查锁、read 标记和 shutdown/plan approval 协议；未执行。", confidence="medium"),
    claim("C-021", "可观测性有多层：analytics event sink、interaction/LLM/tool OTel spans、query profiler 和 feature-gated Perfetto agent hierarchy；它们并非默认都开启，prompt 内容还受显式环境变量控制。", "observability", ["S-038", "S-039", "S-040"], ["observability"], "启用本地 OTLP/Perfetto 执行 tool turn，验证 span parent 与 prompt redaction；未执行。", confidence="medium"),
    claim("C-022", "退出恢复有明确优先级：signal/interrupt 进入 gracefulShutdown，先运行关键 cleanup/持久化，再执行有界 SessionEnd hooks、analytics flush，最后由 failsafe 保证退出。", "shutdown recovery", ["S-041"], ["recovery", "sessions_persistence", "observability"], "挂起 MCP cleanup 与 SessionEnd hook 后发送 SIGTERM，核对 2s cleanup、hook budget 与 failsafe；未执行。", confidence="medium"),
    claim("C-023", "feature() 是构建时 dead-code-elimination 边界，而 GrowthBook/env/settings 是运行时门；没有原始构建配置时，source-visible path 只能表示潜在结构，不能表示 external 发布物实际包含或启用。", "feature conditions", ["S-002", "S-003", "S-042", "I-002"], ["interfaces", "orchestration", "recovery"], "取得 build feature manifest 并比较 bundle strings/entrypoints；当前接受为分析未知项。", confidence="high"),
    claim("C-024", "仓库本身缺少 ADR，但 Anthropic 官方材料明确记录了 human oversight、read-only default、verification、conservative safety、context scarcity、inspectable memory 和 independent team context 等产品立场；把这些立场归纳为五个价值与十三条原则仍是分析者框架，不是 Anthropic 发布的正式架构 taxonomy。", "design intent", ["D-001", "D-002", "D-003", "D-004", "D-005", "D-006", "D-007", "D-008", "I-003"], MODULES, "若官方架构文档或 ADR 发布，比较其术语与本报告的价值/原则映射并记录差异。", confidence="medium"),
    claim("C-025", "本轮最强结论是 source-grounded architecture recovery，而不是 runtime-verified behavior：仅 provider 协议探针获得 X evidence，任何主循环、权限、sandbox、resume 或 subagent 路径都未被此快照真实执行。", "analysis validity", ["X-001", "X-002", "I-004"], MODULES, "提供可构建的同 commit package 或官方 npm artifact 后运行 scripted/real/fault scenario matrix。", confidence="high"),
    claim("C-026", "本地快照含 1,884 个 TS/TSX 文件，并出现论文 v2.1.88 点名的 queryLoop 五阶段 shaper、七成员权限 type union（五 external + auto + bubble）与相同 feature gates；它与论文 corpus 具有强指纹一致性，但缺少 package version、上游 tree hash 和 build manifest，不能宣称字节级相同或官方 artifact 等价。", "paper corpus fingerprint", ["X-003"], ["interfaces", "core_loop", "compaction", "permissions_safety"], "取得论文源码 corpus 的 tree hash 或 v2.1.88 npm 包后做逐文件 hash/diff。", confidence="medium"),
    claim("C-027", "跨 subsystem 重复出现五个可观察架构承诺：模型负责局部判断而 harness 负责确定性执行；安全采用分层治理；context 采用渐进式管理；扩展采用多机制组合；会话采用 append-oriented state 并将 delegation context 分离。它们是由 D/S evidence 支持的 analyst synthesis。", "cross-cutting architecture commitments", ["D-001", "D-002", "D-005", "D-006", "S-004", "S-006", "S-014", "S-020", "S-024", "S-029", "S-033", "S-045", "I-005"], MODULES, "对其他两个 harness 使用同一 codebook 独立编码，检验这些承诺是否是 Claude Code 特有还是通用模式。", confidence="medium"),
    claim("C-028", "Claude Code 的扩展面不是一个统一 plugin API：MCP 主要增加 callable tool surface，Skills 主要注入 context，Hooks 介入 lifecycle/authorization，Plugins 负责跨这些机制的包装与分发；四者具有不同 context cost 与执行语义。", "extension injection points", ["D-005", "S-019", "S-020", "S-028", "S-043", "S-046"], ["tools_extensions", "context_assembly", "permissions_safety"], "安装只含一种 component 的最小 plugin/skill/MCP/hook fixture，比较 request schema、context delta、permission event 和 side effect。", confidence="medium"),
    claim("C-029", "resume/fork 会恢复消息、session metadata 与可用 worktree/agent 状态，但不会从 transcript 恢复旧 session 的临时 permission grants；当前 permission context 由启动参数与磁盘 settings 重新建立。", "permission state across resume", ["D-001", "S-023", "S-030", "S-044"], ["permissions_safety", "sessions_persistence", "recovery"], "在可运行 v2.1.88 中先授予 session-only Bash rule，再 resume/fork 并请求同一命令，检查是否重新 ask。", confidence="medium"),
]


OBSERVATIONS = [
    evidence("S-001", "S", "Git snapshot is clean at commit 16a676f and has no tag; top-level build manifests are absent.", ["C-001"], command="git status; git log; git tag; find top-level"),
    evidence("S-002", "S", "CLI bootstrap dispatches version and feature-gated fast paths before importing the full main module.", ["C-002", "C-023"], path="src/entrypoints/cli.tsx", line=33, end=260, symbol="main"),
    evidence("S-003", "S", "Commander main defines interactive default, print/headless, permissions, resume/fork, MCP, server and remote surfaces.", ["C-002", "C-014", "C-023"], path="src/main.tsx", line=585, end=1005, symbol="main"),
    evidence("S-004", "S", "REPL QueryGuard serializes user-visible queries; onQueryImpl builds fresh tools and contexts then consumes query().", ["C-003"], path="src/screens/REPL.tsx", line=2661, end=2935, symbol="onQueryImpl"),
    evidence("S-005", "S", "QueryEngine builds headless context and consumes the same query() generator.", ["C-003"], path="src/QueryEngine.ts", line=260, end=700, symbol="QueryEngine"),
    evidence("S-006", "S", "query() initializes explicit loop state and delegates to queryLoop's while(true).", ["C-003", "C-004"], path="src/query.ts", line=219, end=330, symbol="query/queryLoop"),
    evidence("S-007", "S", "queryLoop calls the model, collects streamed tool_use blocks and handles fallback/orphan messages.", ["C-004", "C-005"], path="src/query.ts", line=557, end=980, symbol="queryLoop model phase"),
    evidence("S-008", "S", "No-tool, recovery, stop-hook, budget, max-turn and tool-follow-up branches terminate or continue the loop.", ["C-004"], path="src/query.ts", line=1060, end=1560, symbol="queryLoop transitions"),
    evidence("S-009", "S", "Tool orchestration batches concurrency-safe calls and shared execution turns results into model-facing tool_result messages.", ["C-005", "C-011"], path="src/services/tools/toolOrchestration.ts", line=1, end=280, symbol="runTools"),
    evidence("S-010", "S", "System and user context are memoized separately and include environment/git plus CLAUDE.md-derived context.", ["C-006"], path="src/context.ts", line=1, end=260),
    evidence("S-011", "S", "getSystemPrompt composes static and dynamic sections conditional on tools, modes, memory and features.", ["C-006"], path="src/constants/prompts.ts", line=130, end=620, symbol="getSystemPrompt"),
    evidence("S-012", "S", "CLAUDE.md discovery layers managed, user, project, local, rules, add-dir and auto/team memory with provenance.", ["C-006"], path="src/utils/claudemd.ts", line=1, end=520, symbol="getClaudeMds"),
    evidence("S-013", "S", "Attachment assembly adds user-triggered resources and per-thread/main deltas such as memory, skills, MCP, agents and queued messages.", ["C-006"], path="src/utils/attachments.ts", line=1, end=620, symbol="getAttachmentMessages"),
    evidence("S-014", "S", "queryLoop orders tool-result budgeting, optional history snip, microcompact, optional context collapse, autocompact and hard-limit recovery.", ["C-007", "C-027"], path="src/query.ts", line=365, end=540, symbol="queryLoop compaction phase"),
    evidence("S-015", "S", "Legacy compactConversation summarizes a forked context and builds a boundary plus selected reinjections.", ["C-007"], path="src/services/compact/compact.ts", line=330, end=760, symbol="compactConversation"),
    evidence("S-016", "S", "Client selection supports direct Anthropic, Bedrock, Foundry and Vertex based on environment.", ["C-008"], path="src/services/api/client.ts", line=88, end=315, symbol="getAnthropicClient"),
    evidence("S-017", "S", "The model adapter builds Anthropic beta Messages requests and streams raw SSE events.", ["C-008"], path="src/services/api/claude.ts", line=1480, end=1850, symbol="queryModelWithStreaming"),
    evidence("S-018", "S", "withRetry handles auth refresh, 429/529 policy, exponential delay, max-token correction and FallbackTriggeredError.", ["C-008"], path="src/services/api/withRetry.ts", line=48, end=520, symbol="withRetry"),
    evidence("S-019", "S", "Base tool assembly is conditional and later filtered by mode, deny rules and enabled state.", ["C-010"], path="src/tools.ts", line=100, end=560, symbol="getAllBaseTools/getTools"),
    evidence("S-020", "S", "Tool pool merges built-ins and dynamic MCP tools, deduplicates names and stabilizes ordering for prompt caching.", ["C-010", "C-014"], path="src/tools.ts", line=560, end=760, symbol="assembleToolPool"),
    evidence("S-021", "S", "The Tool contract separates schema, validation, permission, execution, concurrency, MCP/deferred flags and renderers.", ["C-010"], path="src/Tool.ts", line=1, end=360, symbol="Tool"),
    evidence("S-022", "S", "Shared toolExecution validates input, runs pre-tool hooks, resolves permission, invokes tool.call and post-processes output.", ["C-011"], path="src/services/tools/toolExecution.ts", line=880, end=1320, symbol="executeTool"),
    evidence("S-023", "S", "Permission types define external/internal modes, allow/ask/deny behavior and rule provenance.", ["C-012"], path="src/types/permissions.ts", line=1, end=260),
    evidence("S-024", "S", "hasPermissions evaluates blanket, ask, tool checks, deny, interaction, safety, bypass and allow rules in order.", ["C-012"], path="src/utils/permissions/permissions.ts", line=560, end=960, symbol="hasPermissions"),
    evidence("S-025", "S", "BashTool delegates command execution to runShellCommand and passes shouldUseSandbox into Shell.exec.", ["C-013"], path="src/tools/BashTool/BashTool.tsx", line=620, end=820, symbol="BashTool.call"),
    evidence("S-026", "S", "shouldUseSandbox checks availability/settings, per-call override policy and excluded commands.", ["C-013"], path="src/tools/BashTool/shouldUseSandbox.ts", line=1, end=180, symbol="shouldUseSandbox"),
    evidence("S-027", "S", "SandboxManager maps filesystem/network settings into sandbox-runtime and Shell wraps before process spawn.", ["C-013"], path="src/utils/sandbox/sandbox-adapter.ts", line=1, end=520, symbol="SandboxManager"),
    evidence("S-028", "S", "Hook execution and special CLI subsystems are separate entry/execution surfaces from canonical toolExecution.", ["C-014"], path="src/utils/hooks.ts", line=1, end=420),
    evidence("S-029", "S", "sessionStorage appends transcript JSONL, separates sidechains and reconstructs parentUuid chains across compaction/snip.", ["C-015"], path="src/utils/sessionStorage.ts", line=500, end=980, symbol="recordTranscript/recordSidechainTranscript"),
    evidence("S-030", "S", "Session restore chooses same-ID resume or fresh-ID fork and restores metadata, messages and worktree path when present.", ["C-016"], path="src/utils/sessionRestore.ts", line=1, end=420, symbol="processResumedConversation"),
    evidence("S-031", "S", "CLI exposes --resume, --fork-session and --rewind-files as distinct operations.", ["C-016"], path="src/main.tsx", line=988, end=1000),
    evidence("S-032", "S", "AgentTool selects normal/fork paths, assembles worker tools, chooses sync/async mode and optionally creates a worktree.", ["C-017", "C-018", "C-019"], path="src/tools/AgentTool/AgentTool.tsx", line=323, end=760, symbol="AgentTool.call"),
    evidence("S-033", "S", "runAgent builds agent contexts/MCP/tools, records sidechain transcripts and recursively consumes query().", ["C-017", "C-018"], path="src/tools/AgentTool/runAgent.ts", line=430, end=820, symbol="runAgent"),
    evidence("S-034", "S", "In-process teammate spawn creates independent abort/context/task state; backend choice is handled by swarm infrastructure.", ["C-017", "C-020"], path="src/utils/swarm/spawnInProcess.ts", line=49, end=230, symbol="spawnInProcessTeammate"),
    evidence("S-035", "S", "Agent worktree creation/removal and change detection are explicit optional workspace operations.", ["C-019"], path="src/utils/worktree.ts", line=1, end=420),
    evidence("S-036", "S", "Swarm backend registry includes in-process and terminal-pane backends.", ["C-020"], path="src/utils/swarm/backends/registry.ts", line=1, end=220),
    evidence("S-037", "S", "Teammate mailbox stores JSON inboxes under ~/.claude/teams and uses lock files for concurrent writes.", ["C-020"], path="src/utils/teammateMailbox.ts", line=1, end=190, symbol="writeToMailbox"),
    evidence("S-038", "S", "Analytics events queue before a sink attaches and string metadata requires an explicit non-code/non-path marker type.", ["C-021"], path="src/services/analytics/index.ts", line=1, end=170),
    evidence("S-039", "S", "Session tracing creates interaction, LLM and tool spans with AsyncLocalStorage and optional prompt logging.", ["C-021"], path="src/utils/telemetry/sessionTracing.ts", line=1, end=720),
    evidence("S-040", "S", "Perfetto tracing records agent hierarchy and operation timing but is feature/user gated.", ["C-021"], path="src/utils/telemetry/perfettoTracing.ts", line=1, end=420),
    evidence("S-041", "S", "gracefulShutdown prioritizes cleanup/persistence, bounds hooks/analytics and arms a failsafe timer.", ["C-022"], path="src/utils/gracefulShutdown.ts", line=391, end=530, symbol="gracefulShutdown"),
    evidence("S-042", "S", "Source repeatedly uses bun:bundle feature() branches intended for build-time elimination.", ["C-023"], path="src/entrypoints/cli.tsx", line=1, end=150),
    evidence("S-043", "S", "HOOK_EVENTS enumerates 27 lifecycle events spanning authorization, session, user input, subagents, compaction, tasks, worktrees, instructions, cwd and files.", ["C-028"], path="src/entrypoints/sdk/coreTypes.ts", line=25, end=53, symbol="HOOK_EVENTS"),
    evidence("S-044", "S", "Startup resolves the current permission mode and permission context from CLI/settings before resume data is folded into the live session; session restore reconstructs messages and metadata but does not deserialize prior session rules.", ["C-029"], path="src/main.tsx", line=1035, end=1410, symbol="permission initialization"),
    evidence("S-045", "S", "runAgent derives child prompting behavior and permission rules from the current parent context plus agent overrides; SDK cliArg rules are preserved while explicit child allowedTools replace session rules.", ["C-018", "C-027"], path="src/tools/AgentTool/runAgent.ts", line=415, end=480, symbol="runAgent permission context"),
    evidence("S-046", "S", "PluginManifestSchema composes hooks, commands, agents, skills, output styles, channels, MCP servers, LSP servers, settings and user configuration into one packaging format.", ["C-028"], path="src/utils/plugins/schemas.ts", line=884, end=898, symbol="PluginManifestSchema"),
    evidence("D-001", "D", "Anthropic's safe-agent framework documents the autonomy-versus-human-control tension and describes Claude Code as read-only by default with approval before modifying code or systems.", ["C-024", "C-027", "C-029"], url="https://www.anthropic.com/news/our-framework-for-developing-safe-and-trustworthy-agents", locator="Anthropic: safe and trustworthy agents"),
    evidence("D-002", "D", "Official Claude Code documentation describes an iterative agentic loop and advises giving the agent verifiable outcomes, supporting reliable execution as a product stance.", ["C-024", "C-027"], url="https://code.claude.com/docs/en/how-claude-code-works", locator="Anthropic: how Claude Code works"),
    evidence("D-003", "D", "Anthropic reports 93% approval of permission prompts and defines auto-mode threats including overeager behavior, honest mistakes, prompt injection and misalignment.", ["C-024"], url="https://www.anthropic.com/engineering/claude-code-auto-mode", locator="Anthropic: Claude Code auto mode"),
    evidence("D-004", "D", "Anthropic reports that filesystem and network sandbox boundaries reduced internal permission prompts by 84%, positioning bounded autonomy as a safety and usability mechanism.", ["C-024"], url="https://www.anthropic.com/engineering/claude-code-sandboxing", locator="Anthropic: Claude Code sandboxing"),
    evidence("D-005", "D", "Anthropic's context-engineering guidance treats context as limited, recommends progressive disclosure and compaction, and describes subagents returning condensed summaries from isolated context windows.", ["C-024", "C-027", "C-028"], url="https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents", locator="Anthropic: effective context engineering"),
    evidence("D-006", "D", "Official memory documentation distinguishes user-authored CLAUDE.md instructions from Claude-authored auto memory and provides explicit audit/edit surfaces.", ["C-024", "C-027"], url="https://code.claude.com/docs/en/memory", locator="Anthropic: Claude Code memory"),
    evidence("D-007", "D", "Official agent-team documentation states that each teammate has an independent context window and that token cost scales with teammates.", ["C-024"], url="https://code.claude.com/docs/en/agent-teams", locator="Anthropic: Claude Code agent teams"),
    evidence("D-008", "D", "Claude's Constitution documents principal-aware helpfulness, human oversight and contextual judgment; it is model-level intent rather than a direct harness architecture specification.", ["C-024"], url="https://www.anthropic.com/constitution", locator="Anthropic: Claude's Constitution", confidence="medium"),
    evidence("X-001", "X", "Snapshot scanner found 1,902 TS/JS source files, 12,958 relative imports, 657 unresolved relative imports and zero recognized build manifests.", ["C-001", "C-025"], command="python3 experiments/scan_snapshot.py", scenario="X-SCENARIO-001", notes="Result: experiments/snapshot-integrity.json"),
    evidence("X-002", "X", "SiFlow probe returned HTTP 200 for OpenAI models, Anthropic Messages, Anthropic SSE and forced echo tool_use with enable_thinking=false.", ["C-009", "C-025"], command="curl dialect probes", scenario="X-SCENARIO-002", conditions={"provider": "siflow/qwen3.6-35ba3b"}, notes="Sanitized result: experiments/provider-probe.json"),
    evidence("X-003", "X", "A controlled corpus fingerprint found exactly 1,884 TS/TSX files, matching the paper's v2.1.88 corpus count, plus the same named shapers, permission union and feature gates; exact tree equality remains unproven.", ["C-026"], command="rg --files + named-symbol fingerprint against arXiv:2604.14228v2", scenario="X-SCENARIO-008", notes="Benchmark source: https://arxiv.org/html/2604.14228v2"),
    evidence("I-001", "I", "Because side-effecting subsystems exist outside shared toolExecution, process-wide governance requires separate reachability/runtime proof.", ["C-014"], confidence="low"),
    evidence("I-002", "I", "Source-visible feature branches are potential architecture until the original build-time feature set is known.", ["C-023"], confidence="high"),
    evidence("I-003", "I", "The five-value and thirteen-principle hierarchy is an analyst synthesis over first-party product stances plus source mechanisms, not an official Anthropic architecture taxonomy.", ["C-024"], confidence="high"),
    evidence("I-004", "I", "Provider compatibility plus source structure is insufficient to label any harness behavior runtime_verified.", ["C-025"], confidence="high"),
    evidence("I-005", "I", "Repeated source patterns support five cross-cutting commitments, but their causal motivation and uniqueness require documentary and cross-project comparison.", ["C-027"], confidence="medium"),
]


def node(node_id: str, node_type: str, name: str, summary: str, evidence_ids: list[str], layer: str, **attrs: object) -> dict:
    return {
        "id": node_id,
        "type": node_type,
        "name": name,
        "summary": summary,
        "attributes": {"layer": layer, **attrs},
        "conditions": {},
        "evidence_ids": evidence_ids,
        "confidence": "high" if not any(e.startswith("I-") for e in evidence_ids) else "medium",
        "status": "static_only",
    }


def edge(edge_id: str, source: str, target: str, edge_type: str, evidence_ids: list[str], label: str = "", **conditions: object) -> dict:
    return {
        "id": edge_id,
        "source": source,
        "target": target,
        "type": edge_type,
        "label": label,
        "conditions": conditions,
        "evidence_ids": evidence_ids,
        "confidence": "medium" if any(e.startswith("I-") for e in evidence_ids) else "high",
        "status": "inferred" if any(e.startswith("I-") for e in evidence_ids) else "static_only",
    }


NODES = [
    node("N-CLI", "Interface", "CLI surfaces", "Interactive, print, server, bridge and special subcommands.", ["S-002", "S-003"], "interface", trust_zone="host"),
    node("N-CLIEntry", "Entrypoint", "CLI bootstrap", "Fast-path dispatcher before the full Commander main.", ["S-002"], "interface", lifecycle="startup/reload"),
    node("N-Interactive", "Interface", "Interactive REPL", "Ink/React surface with QueryGuard and UI approvals.", ["S-004"], "interface", trust_zone="host"),
    node("N-Headless", "Interface", "Print / SDK", "Non-interactive QueryEngine and structured output path.", ["S-003", "S-005"], "interface", trust_zone="host"),
    node("N-Session", "Session", "Live session", "Session id, app state, messages, permission state and runtime services.", ["S-003", "S-029"], "state", persistence_tier="live"),
    node("N-QueryLoop", "AgentLoop", "Shared query loop", "Mutable model/tool iteration shared by interactive and headless paths.", ["S-006", "S-007", "S-008"], "orchestration", agent_role="Primary", persistence_tier="live"),
    node("N-ContextBuilder", "ContextBuilder", "Context assembly", "Builds model-visible system, user, system-context and messages.", ["S-010", "S-011", "S-013"], "context-capability", lifecycle="per-turn"),
    node("N-SystemPrompt", "PromptSource", "System prompt", "Tool/mode/model-aware static and dynamic instruction sections.", ["S-011"], "context-capability", lifecycle="startup/reload"),
    node("N-ClaudeMd", "PromptSource", "CLAUDE.md + rules", "Managed, user, project, local, add-dir and nested instruction sources.", ["S-012"], "context-capability", lifecycle="startup/lazy"),
    node("N-Attachments", "ContextTransformer", "Runtime attachments", "Memory, skill, MCP, agent, task and queued-message deltas.", ["S-013"], "context-capability", lifecycle="per-turn"),
    node("N-Compactor", "Compactor", "Compaction pipeline", "Budget, optional snip, microcompact, optional collapse, autocompact and hard-limit recovery.", ["S-014", "S-015"], "context-capability", lifecycle="threshold/overflow/manual", stage_count=5),
    node("N-ModelAdapter", "ModelAdapter", "Anthropic provider adapter", "Direct, Bedrock, Vertex and Foundry client selection plus retry.", ["S-016", "S-018"], "infrastructure", trust_zone="network"),
    node("N-ModelCall", "ModelCall", "Messages stream", "Anthropic beta Messages request and raw streaming response.", ["S-017"], "infrastructure", trust_zone="external", lifecycle="per-turn"),
    node("N-ToolRegistry", "ToolRegistry", "Capability pool", "Built-ins plus dynamic MCP tools with filtering/dedup/order.", ["S-019", "S-020", "S-021"], "context-capability", trust_zone="process"),
    node("N-ToolRouter", "Router", "Tool execution router", "Lookup, schema validation, hooks, permission and dispatch.", ["S-022"], "orchestration", trust_zone="process"),
    node("N-BuiltinTools", "Tool", "Built-in tools", "Bash, read/edit/write, search, task, agent, plan and other gated tools.", ["S-019"], "context-capability", trust_zone="process", lifecycle="tool-call"),
    node("N-MCP", "MCPServer", "MCP tools", "Dynamically connected external capability servers.", ["S-020"], "extension", trust_zone="external", lifecycle="startup/reload"),
    node("N-Plugins", "Plugin", "Plugins", "Packaging and distribution across commands, agents, skills, hooks, MCP and other registries.", ["S-003", "S-020", "S-046"], "extension", trust_zone="resource-loading"),
    node("N-Skills", "Skill", "Skills", "Prompt/workflow content loaded explicitly, lazily or by agents.", ["S-013", "S-033"], "extension", lifecycle="startup/lazy"),
    node("N-Hooks", "Hook", "Hooks", "Twenty-seven lifecycle events that may observe, modify, block or extend execution.", ["S-022", "S-028", "S-043"], "extension", trust_zone="child-process", event_count=27),
    node("N-Permission", "PermissionGate", "Permission gate", "Rule/mode/safety evaluation before canonical tool side effects.", ["S-023", "S-024"], "governance", trust_zone="process"),
    node("N-Policy", "PolicyRule", "Policy and modes", "Allow/ask/deny rules, managed settings and permission modes; session grants are not restored from transcript.", ["S-023", "S-024", "S-044"], "governance", trust_zone="process", session_grants_durable=False),
    node("N-Sandbox", "Sandbox", "Sandbox runtime", "Optional platform execution wrapper for command/filesystem/network constraints.", ["S-026", "S-027"], "governance", trust_zone="child-process"),
    node("N-Shell", "ExecutionBackend", "Shell/process backend", "Spawns Bash commands with cwd/env/cancellation and optional sandbox wrapper.", ["S-025", "S-027"], "execution", trust_zone="host"),
    node("N-Workspace", "Workspace", "Current workspace", "Shared cwd and files unless an explicit worktree is selected.", ["S-025", "S-032", "S-035"], "execution", trust_zone="host", persistence_tier="filesystem"),
    node("N-SessionStore", "SessionStore", "Transcript JSONL", "Project-scoped append-oriented message and metadata storage.", ["S-029"], "state", persistence_tier="durable"),
    node("N-Recovery", "RecoveryPolicy", "Retry and recovery", "Provider retry, compaction recovery, cancellation and graceful shutdown.", ["S-008", "S-018", "S-041"], "infrastructure", persistence_tier="live"),
    node("N-AgentTool", "Tool", "AgentTool", "Delegation entry for normal, forked, sync, async and worktree children.", ["S-032"], "orchestration", agent_role="supervisor"),
    node("N-Subagent", "Subagent", "Agent child", "Recursive query loop with separate agent context/tools/MCP/transcript.", ["S-032", "S-033"], "orchestration", agent_role="worker", persistence_tier="live"),
    node("N-Team", "Subagent", "Swarm teammate", "In-process or terminal-pane team member with independent task identity.", ["S-034", "S-036"], "orchestration", agent_role="worker", persistence_tier="live"),
    node("N-Mailbox", "Artifact", "Team mailbox", "File-locked durable inbox for teammate messages and protocols.", ["S-037"], "state", persistence_tier="durable"),
    node("N-Worktree", "Workspace", "Agent worktree", "Optional isolated git working tree retained when modified.", ["S-032", "S-035"], "execution", trust_zone="host", persistence_tier="filesystem"),
    node("N-Telemetry", "TelemetrySink", "Events and traces", "Analytics, OTel, query profile and optional Perfetto trace.", ["S-038", "S-039", "S-040"], "observability", trust_zone="external"),
    node("N-Exit", "ExitCondition", "Turn/session exit", "Completed, limits, hook stop, abort, error or process shutdown.", ["S-008", "S-041"], "orchestration", persistence_tier="live"),
]


EDGES = [
    edge("E-001", "N-CLI", "N-CLIEntry", "enters", ["S-002"]),
    edge("E-002", "N-CLIEntry", "N-Interactive", "routes_if", ["S-002", "S-003"], "default"),
    edge("E-003", "N-CLIEntry", "N-Headless", "routes_if", ["S-002", "S-003"], "--print / SDK"),
    edge("E-004", "N-Interactive", "N-Session", "enters", ["S-004"]),
    edge("E-005", "N-Headless", "N-Session", "enters", ["S-005"]),
    edge("E-006", "N-Session", "N-QueryLoop", "calls", ["S-004", "S-005", "S-006"]),
    edge("E-007", "N-QueryLoop", "N-ContextBuilder", "assembles", ["S-006", "S-010"]),
    edge("E-008", "N-SystemPrompt", "N-ContextBuilder", "injects", ["S-011"]),
    edge("E-009", "N-ClaudeMd", "N-ContextBuilder", "injects", ["S-012"]),
    edge("E-010", "N-Attachments", "N-ContextBuilder", "injects", ["S-013"]),
    edge("E-011", "N-SessionStore", "N-ContextBuilder", "restores", ["S-029", "S-030"]),
    edge("E-012", "N-ContextBuilder", "N-Compactor", "calls", ["S-014"]),
    edge("E-013", "N-Compactor", "N-ContextBuilder", "compacts", ["S-015"]),
    edge("E-014", "N-ContextBuilder", "N-ModelCall", "calls", ["S-007", "S-017"]),
    edge("E-015", "N-ModelAdapter", "N-ModelCall", "calls", ["S-016", "S-017"]),
    edge("E-016", "N-ModelCall", "N-ToolRouter", "proposes", ["S-007", "S-022"], "tool_use"),
    edge("E-017", "N-ToolRegistry", "N-ModelCall", "registers", ["S-019", "S-020"], "visible schemas"),
    edge("E-018", "N-ToolRegistry", "N-BuiltinTools", "registers", ["S-019"]),
    edge("E-019", "N-MCP", "N-ToolRegistry", "registers", ["S-020"]),
    edge("E-020", "N-Plugins", "N-MCP", "registers", ["S-003", "S-020"]),
    edge("E-021", "N-Skills", "N-ContextBuilder", "injects", ["S-013", "S-033"]),
    edge("E-022", "N-ToolRouter", "N-Hooks", "triggers", ["S-022"]),
    edge("E-023", "N-ToolRouter", "N-Permission", "calls", ["S-022", "S-024"]),
    edge("E-024", "N-Policy", "N-Permission", "authorizes", ["S-023", "S-024"]),
    edge("E-025", "N-Permission", "N-BuiltinTools", "authorizes", ["S-022", "S-024"]),
    edge("E-026", "N-Permission", "N-Exit", "denies", ["S-022", "S-024"], "model-facing denial"),
    edge("E-027", "N-BuiltinTools", "N-Shell", "executes", ["S-025"]),
    edge("E-028", "N-Sandbox", "N-Shell", "executes", ["S-026", "S-027"], "optional wrapper", feature="sandbox.enabled"),
    edge("E-029", "N-Shell", "N-Workspace", "writes", ["S-025", "S-027"]),
    edge("E-030", "N-BuiltinTools", "N-ContextBuilder", "returns", ["S-009", "S-022"], "tool_result"),
    edge("E-031", "N-ContextBuilder", "N-QueryLoop", "returns", ["S-008"], "follow-up"),
    edge("E-032", "N-QueryLoop", "N-SessionStore", "persists", ["S-029"]),
    edge("E-033", "N-QueryLoop", "N-Recovery", "calls", ["S-008", "S-018"]),
    edge("E-034", "N-Recovery", "N-ModelCall", "retries", ["S-018"]),
    edge("E-035", "N-Recovery", "N-Compactor", "falls_back_to", ["S-008", "S-014"]),
    edge("E-036", "N-QueryLoop", "N-Exit", "exits_to", ["S-008"]),
    edge("E-037", "N-QueryLoop", "N-AgentTool", "calls", ["S-032"]),
    edge("E-038", "N-AgentTool", "N-Subagent", "delegates", ["S-032", "S-033"]),
    edge("E-039", "N-Subagent", "N-QueryLoop", "calls", ["S-033"], "recursive query"),
    edge("E-040", "N-Subagent", "N-QueryLoop", "isolates_context_from", ["S-033"]),
    edge("E-041", "N-Subagent", "N-Workspace", "shares_workspace_with", ["S-032"], "default"),
    edge("E-042", "N-AgentTool", "N-Worktree", "calls", ["S-032", "S-035"], "isolation=worktree"),
    edge("E-043", "N-Subagent", "N-Worktree", "writes", ["S-032", "S-035"]),
    edge("E-044", "N-Subagent", "N-QueryLoop", "returns", ["S-032", "S-033"], "result/notification"),
    edge("E-045", "N-Session", "N-Team", "delegates", ["S-034", "S-036"]),
    edge("E-046", "N-Team", "N-Mailbox", "writes", ["S-037"]),
    edge("E-047", "N-Mailbox", "N-Team", "returns", ["S-037"], "unread attachment"),
    edge("E-048", "N-QueryLoop", "N-Telemetry", "emits_trace", ["S-038", "S-039"]),
    edge("E-049", "N-Subagent", "N-Telemetry", "emits_trace", ["S-040"]),
    edge("E-050", "N-Exit", "N-SessionStore", "persists", ["S-041"]),
    edge("E-051", "N-Hooks", "N-Shell", "executes", ["S-028", "I-001"], "separate audit path"),
    edge("E-052", "N-Plugins", "N-Skills", "registers", ["S-046"], "packaged skill"),
    edge("E-053", "N-Plugins", "N-Hooks", "registers", ["S-043", "S-046"], "packaged hook"),
    edge("E-054", "N-Hooks", "N-ContextBuilder", "injects", ["S-028", "S-043"], "lifecycle context"),
]


SCENARIOS = {
    "schema_version": "1.0",
    "scenarios": [
        {
            "id": "X-SCENARIO-001",
            "title": "Source snapshot completeness",
            "mode": "fault",
            "status": "completed",
            "claims_tested": ["C-001", "C-025"],
            "configuration": {"commit": COMMIT, "entrypoint": "source tree"},
            "expected_discriminating_events": ["manifest.present", "relative_import.resolved"],
            "forbidden_events": [],
            "result": {
                "outcome": "failed_precondition",
                "source_files": 1902,
                "relative_imports": 12958,
                "missing_relative_imports": 657,
                "build_manifests": [],
                "evidence_ids": ["X-001"],
            },
            "notes": "This is a source integrity experiment, not a Claude Code runtime execution.",
        },
        {
            "id": "X-SCENARIO-002",
            "title": "SiFlow Anthropic Messages dialect probe",
            "mode": "real",
            "status": "completed",
            "claims_tested": ["C-009", "C-025"],
            "configuration": {
                "provider": "siflow",
                "model": "qwen3.6-35ba3b",
                "credentials_sent": False,
                "private_prompt_data": False,
            },
            "expected_discriminating_events": ["message_start", "tool_use", "message_stop"],
            "forbidden_events": [],
            "result": {
                "outcome": "passed_protocol_subset",
                "http_status": 200,
                "forced_tool": "echo",
                "tool_input": {"text": "hello"},
                "evidence_ids": ["X-002"],
            },
            "notes": "Endpoint compatibility does not prove harness compatibility.",
        },
        {
            "id": "X-SCENARIO-008",
            "title": "v2.1.88 paper corpus fingerprint",
            "mode": "scripted",
            "status": "completed",
            "claims_tested": ["C-026"],
            "configuration": {
                "benchmark": "https://arxiv.org/html/2604.14228v2",
                "paper_version": "Claude Code v2.1.88",
                "local_commit": COMMIT,
            },
            "expected_discriminating_events": ["typescript_count.match", "named_symbol.match", "feature_gate.match"],
            "forbidden_events": ["claim.exact_tree_identity_without_hash"],
            "result": {
                "outcome": "strong_fingerprint_match",
                "typescript_files": 1884,
                "javascript_files": 18,
                "exact_tree_equality": "unproven",
                "evidence_ids": ["X-003"],
            },
            "notes": "The benchmark narrows release identity but does not replace a package manifest or tree hash.",
        },
        {
            "id": "X-SCENARIO-003",
            "title": "Scripted text-only query",
            "mode": "scripted",
            "status": "blocked",
            "claims_tested": ["C-003", "C-004"],
            "configuration": {"entrypoint": "query deps.callModel"},
            "result": {"outcome": "not_executed", "reason": "snapshot is not self-contained"},
        },
        {
            "id": "X-SCENARIO-004",
            "title": "Permission denial prevents shell side effect",
            "mode": "scripted",
            "status": "blocked",
            "claims_tested": ["C-012", "C-013", "C-014"],
            "configuration": {"permission_mode": "default", "workspace": "disposable"},
            "result": {"outcome": "not_executed", "reason": "snapshot is not self-contained"},
        },
        {
            "id": "X-SCENARIO-005",
            "title": "Context overflow and compaction survivors",
            "mode": "fault",
            "status": "blocked",
            "claims_tested": ["C-006", "C-007"],
            "configuration": {"model": "scripted", "workspace": "disposable"},
            "result": {"outcome": "not_executed", "reason": "snapshot is not self-contained"},
        },
        {
            "id": "X-SCENARIO-006",
            "title": "Session resume and fork",
            "mode": "scripted",
            "status": "blocked",
            "claims_tested": ["C-015", "C-016"],
            "configuration": {"entrypoint": "print", "workspace": "disposable"},
            "result": {"outcome": "not_executed", "reason": "snapshot is not self-contained"},
        },
        {
            "id": "X-SCENARIO-007",
            "title": "Subagent context/workspace/cancellation matrix",
            "mode": "scripted",
            "status": "blocked",
            "claims_tested": ["C-017", "C-018", "C-019", "C-020"],
            "configuration": {"modes": ["sync", "async", "worktree", "in-process teammate"]},
            "result": {"outcome": "not_executed", "reason": "snapshot is not self-contained"},
        },
    ],
}

MODULE_FILES = {
    "interfaces": ["src/entrypoints/cli.tsx", "src/main.tsx", "src/screens/REPL.tsx", "src/QueryEngine.ts"],
    "core_loop": ["src/query.ts", "src/query/config.ts", "src/query/deps.ts"],
    "context_assembly": ["src/context.ts", "src/constants/prompts.ts", "src/utils/claudemd.ts", "src/utils/attachments.ts"],
    "compaction": ["src/query.ts", "src/services/compact/autoCompact.ts", "src/services/compact/compact.ts", "src/services/compact/microCompact.ts"],
    "model_abstraction": ["src/services/api/client.ts", "src/services/api/claude.ts", "src/services/api/withRetry.ts", "src/utils/model/providers.ts"],
    "tools_extensions": ["src/Tool.ts", "src/tools.ts", "src/services/tools/toolExecution.ts", "src/services/tools/toolOrchestration.ts"],
    "permissions_safety": ["src/types/permissions.ts", "src/utils/permissions/permissions.ts", "src/hooks/useCanUseTool.tsx"],
    "sandbox_execution": ["src/tools/BashTool/BashTool.tsx", "src/tools/BashTool/shouldUseSandbox.ts", "src/utils/sandbox/sandbox-adapter.ts", "src/utils/Shell.ts"],
    "workspace": ["src/utils/cwd.ts", "src/utils/worktree.ts", "src/tools/AgentTool/AgentTool.tsx"],
    "sessions_persistence": ["src/utils/sessionStorage.ts", "src/utils/sessionRestore.ts"],
    "subagents": ["src/tools/AgentTool/AgentTool.tsx", "src/tools/AgentTool/runAgent.ts", "src/utils/swarm/spawnInProcess.ts"],
    "orchestration": ["src/query.ts", "src/services/tools/toolOrchestration.ts", "src/coordinator/coordinatorMode.ts"],
    "observability": ["src/services/analytics/index.ts", "src/utils/telemetry/sessionTracing.ts", "src/utils/telemetry/perfettoTracing.ts"],
    "recovery": ["src/services/api/withRetry.ts", "src/utils/gracefulShutdown.ts", "src/services/compact/compact.ts"],
}


def build_coverage() -> dict:
    modules = {}
    for module_id in MODULES:
        modules[module_id] = {
            "status": "partial",
            "directories": sorted({str(Path(p).parent) for p in MODULE_FILES[module_id]}),
            "files": MODULE_FILES[module_id],
            "symbols": [],
            "configurations": ["source-visible external/default candidate"],
            "scenarios": [
                s["id"] for s in SCENARIOS["scenarios"]
                if any(c in {claim["id"] for claim in CLAIMS if module_id in claim["coverage_refs"]} for c in s["claims_tested"])
            ],
            "excluded_surfaces": ["compiled feature set", "official package manifests"],
            "unresolved": ["No target runtime trace at this commit."],
            "notes": "Static source coverage is focused and evidence-backed; runtime coverage is absent.",
        }
    return {
        "schema_version": "1.0",
        "modules": modules,
        "global": {
            "entrypoints_examined": ["src/entrypoints/cli.tsx", "src/main.tsx", "src/screens/REPL.tsx", "src/QueryEngine.ts"],
            "configurations_tested": ["source snapshot integrity", "SiFlow protocol subset", "v2.1.88 paper corpus fingerprint", "first-party documentary pass"],
            "platforms_tested": ["Linux host for analysis scripts only"],
            "providers_tested": ["SiFlow qwen3.6-35ba3b protocol probe"],
            "search_limits": {"max_files": 20000, "max_file_size": 1000000, "max_hits_per_category": 120},
            "inaccessible_surfaces": [
                "original package.json and lockfile",
                "original bun:bundle feature manifest",
                "657 unresolved relative imports",
                "official build/release metadata",
            ],
            "unresolved_high_value_questions": [
                "Which feature() branches are in the external production bundle?",
                "Does every side-effecting path pass a common process-level policy boundary?",
                "What exactly is shared across sync, async, teammate and pane-based children at runtime?",
                "What survives compaction and resume under observed long-context workloads?",
            ],
        },
    }


CONFLICTS = [
    {
        "id": "CF-001",
        "record_type": "conflict",
        "subject_id": "C-001",
        "evidence_ids": ["S-001", "X-001"],
        "description": "Source entrypoints exist, but the snapshot lacks the build inputs and many relative modules needed to execute them.",
        "status": "resolved",
        "resolution": "Treat the target as a source-only architectural snapshot and do not claim runtime verification.",
    },
    {
        "id": "CF-002",
        "record_type": "conflict",
        "subject_id": "C-009",
        "evidence_ids": ["X-001", "X-002"],
        "description": "The authorized model endpoint supports the expected protocol subset, but the target snapshot cannot launch a harness request.",
        "status": "accepted_unknown",
        "resolution": "Retain provider compatibility as a narrow X claim and leave full-harness compatibility unverified.",
    },
]


def main() -> int:
    integrity = json.loads((ROOT / "experiments" / "snapshot-integrity.json").read_text(encoding="utf-8"))
    manifest = {
        "schema_version": "1.0",
        "analysis_status": "static_complete_runtime_limited",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "target": {
            "repository_root": str(TARGET),
            "repository_url": "https://github.com/IcyFeather233/claude-code",
            "commit": COMMIT,
            "branch": "main",
            "tag": None,
            "dirty": False,
            "source_kind": "public source-only mirror",
            "official_release_identity": "strong fingerprint match to the v2.1.88 corpus analyzed by arXiv:2604.14228v2; exact artifact identity unproven",
        },
        "scope": {
            "entrypoints": ["src/entrypoints/cli.tsx", "src/main.tsx", "src/QueryEngine.ts"],
            "configurations": ["source-visible external/default candidate"],
            "enabled_features": [],
            "disabled_features": [],
            "inaccessible_surfaces": build_coverage()["global"]["inaccessible_surfaces"],
            "documentary_sources": [
                "https://www.anthropic.com/news/our-framework-for-developing-safe-and-trustworthy-agents",
                "https://code.claude.com/docs/en/how-claude-code-works",
                "https://www.anthropic.com/engineering/claude-code-auto-mode",
                "https://www.anthropic.com/engineering/claude-code-sandboxing",
                "https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents",
                "https://code.claude.com/docs/en/memory",
                "https://code.claude.com/docs/en/agent-teams",
                "https://www.anthropic.com/constitution",
            ],
        },
        "execution": {
            "runtime_versions": {"python": "3", "target_bun": "unavailable", "target_node": "unavailable"},
            "model_mode": "protocol_probe_only",
            "model_provider": "siflow/qwen3.6-35ba3b",
            "network_policy": "Public paper/first-party documentation retrieval and two sanitized provider probes were authorized and executed.",
            "filesystem_policy": "Target repository read-only; generated artifacts stay in analysis bundle.",
            "credential_policy": "No credential was read, sent or stored.",
            "isolation": "No target harness process executed.",
        },
        "tooling": {"skill": "harness-analysis", "skill_commit": "uncommitted paper-benchmark revision"},
        "snapshot_integrity": {
            "source_file_count": integrity["source_file_count"],
            "typescript_source_file_count": 1884,
            "javascript_source_file_count": 18,
            "missing_relative_import_count": integrity["missing_relative_import_count"],
            "present_build_manifests": integrity["present_build_manifests"],
            "paper_benchmark": "arXiv:2604.14228v2 (Claude Code v2.1.88)",
            "identity_confidence": "strong fingerprint match; not cryptographically proven",
        },
    }
    hir = {
        "schema_version": "1.0",
        "repository": {
            "root": str(TARGET),
            "commit": COMMIT,
            "entrypoints": manifest["scope"]["entrypoints"],
            "configurations": manifest["scope"]["configurations"],
        },
        "nodes": NODES,
        "edges": EDGES,
    }
    questions = {
        "schema_version": "1.0",
        "selection_rule": "Prioritize architectural importance, uncertainty, counterexample value and testability.",
        "queue": [
            {"id": "Q-001", "question": "What exact build feature set produced the public external package?", "priority": "critical", "status": "blocked"},
            {"id": "Q-002", "question": "Do hooks and non-tool subsystems share an equivalent policy boundary?", "priority": "critical", "status": "open"},
            {"id": "Q-003", "question": "What is the observed inheritance matrix for each child mechanism?", "priority": "high", "status": "blocked"},
            {"id": "Q-004", "question": "What survives long-context compaction and subsequent resume?", "priority": "high", "status": "blocked"},
        ],
    }
    write_json(ROOT / "manifest.json", manifest)
    write_json(ROOT / "hir.json", hir)
    write_jsonl(ROOT / "evidence" / "claims.jsonl", CLAIMS)
    write_jsonl(ROOT / "evidence" / "observations.jsonl", OBSERVATIONS)
    write_jsonl(ROOT / "evidence" / "conflicts.jsonl", CONFLICTS)
    write_json(ROOT / "evidence" / "coverage.json", build_coverage())
    write_json(ROOT / "scenarios" / "catalog.json", SCENARIOS)
    write_json(ROOT / "questions.json", questions)
    print(f"Compiled {len(CLAIMS)} claims, {len(OBSERVATIONS)} evidence records, {len(NODES)} nodes and {len(EDGES)} edges")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
