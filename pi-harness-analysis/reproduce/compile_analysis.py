#!/usr/bin/env python3
"""Compile the evidence store and HIR for the pinned Pi v0.80.7 analysis."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TARGET = "/volume/med/work/users/mzchen/lab/pi"
COMMIT = "818d67457cdd6b60bce6b121d16b23141c252dd8"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, values: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n" for value in values),
        encoding="utf-8",
    )


def source(path: str, start: int | None = None, end: int | None = None, **extra: object) -> dict:
    locator = path if start is None else f"{path}:{start}" if end in (None, start) else f"{path}:{start}-{end}"
    return {"locator": locator, "path": path, "start_line": start, "end_line": end, **extra}


def evidence(
    evidence_id: str,
    kind: str,
    summary: str,
    source_value: dict,
    supports: list[str],
    *,
    confidence: str = "high",
    conditions: dict | None = None,
    notes: str | None = None,
) -> dict:
    value = {
        "id": evidence_id,
        "record_type": "evidence",
        "kind": kind,
        "summary": summary,
        "source": source_value,
        "supports_claims": supports,
        "contradicts_claims": [],
        "conditions": conditions or {},
        "confidence": confidence,
    }
    if notes:
        value["notes"] = notes
    return value


def claim(
    claim_id: str,
    statement: str,
    scope: str,
    importance: str,
    evidence_ids: list[str],
    coverage_refs: list[str],
    falsification_test: str,
    *,
    confidence: str = "high",
    conditions: dict | None = None,
    notes: str | None = None,
) -> dict:
    value = {
        "id": claim_id,
        "record_type": "claim",
        "statement": statement,
        "scope": scope,
        "importance": importance,
        "status": "supported",
        "evidence_ids": evidence_ids,
        "counterevidence_ids": [],
        "confidence": confidence,
        "conditions": conditions or {},
        "coverage_refs": coverage_refs,
        "falsification_test": falsification_test,
    }
    if notes:
        value["notes"] = notes
    return value


CLAIMS = [
    claim("C-001", "Pi 的产品入口由同一 Coding Agent runtime 支撑交互式 TUI、print/JSON 与 RPC 模式，底层能力拆分为 ai、agent、coding-agent、tui 等包。", "v0.80.7 monorepo and CLI", "high", ["D-001", "S-012", "S-013", "S-014"], ["interfaces", "orchestration"], "从任一模式入口追踪到不同的核心循环实现；本轮源码检查和 JSON 模式运行均未发现。"),
    claim("C-002", "通用 runAgentLoop 是 Pi 的核心模型-工具循环：模型响应后执行工具、追加 toolResult，再决定继续、注入 steering/follow-up 或退出。", "agent-core low-level loop", "high", ["S-001", "R-001", "R-002", "X-001"], ["core_loop", "orchestration"], "构造一次 toolUse 响应并检查是否不经过 runAgentLoop 的工具回填路径；真实轨迹与 faux-provider 测试均支持该循环。"),
    claim("C-003", "Coding Agent 的模型上下文由持久化分支消息、system prompt、项目指令、skills、工具清单及 extension hook 注入共同形成，并在模型边界前转换。", "coding-agent default runtime", "high", ["S-002", "S-004", "S-005", "R-001"], ["context_assembly"], "分别禁用 context files、skills、extensions 并比较 provider request；本轮禁用配置验证了最小上下文路径，完整差分仍未执行。", confidence="medium"),
    claim("C-004", "内置、扩展与 SDK 工具被合并为运行时 registry；tool_call/tool_result hooks 位于实际 execute 前后，可阻断或改写结果。", "coding-agent tool system", "high", ["S-003", "S-017", "R-002", "X-001"], ["tools_extensions"], "注册同名工具或让 hook 返回 block=false/true，检查最终执行目标和副作用；定向测试覆盖了 hook 与排序语义。"),
    claim("C-005", "Pi 没有默认的逐工具权限审批管线；permission popup 与路径保护属于可选 extension，默认工具直接以进程权限执行。", "default coding-agent configuration", "high", ["D-002", "D-004", "S-003", "S-017"], ["permissions_safety"], "在无 extensions 的默认 CLI 中触发 bash/write 并寻找强制 ask/allow/deny 决策；源码未发现，官方文档明确否定。"),
    claim("C-006", "Project trust 只控制项目 settings/resources/extensions 的加载，不是工具权限或执行 sandbox；非交互模式无 UI 时默认 ask 会落到不信任。", "project resource bootstrap", "high", ["D-002", "S-005", "S-006"], ["permissions_safety", "context_assembly"], "在未信任项目放置 extension 与 AGENTS.md，验证 extension 被跳过而 context file 仍可加载；本轮以源码和文档确证，未执行含恶意资源的动态场景。"),
    claim("C-007", "默认 bash backend 在当前 cwd 以继承环境启动本地 shell；timeout 是可选且无默认值，abort/timeout 会终止进程树。", "built-in bash tool", "high", ["D-002", "D-007", "S-007"], ["sandbox_execution", "workspace"], "运行无 timeout 的长命令并观察是否存在隐藏上限，再发送 abort 检查子进程树；本轮因安全边界未执行 shell 动态场景。"),
    claim("C-008", "Coding Agent session 是版本化 append-only JSONL 树，id/parentId 与 leaf 表示分支；恢复时重建 compaction-aware active context。", "coding-agent sessions v3", "high", ["S-008", "S-014", "R-003", "R-004", "X-003"], ["sessions_persistence"], "跨进程恢复同一 session-id 并要求回忆前一进程 token；R-003/R-004 已通过。"),
    claim("C-009", "当前 Coding Agent AgentSession 实现自动 compaction 与有限自动 retry：overflow 最多 compact-and-retry 一次，普通可重试错误指数退避且受 maxRetries 限制。", "coding-agent AgentSession", "high", ["S-009", "S-010", "X-003"], ["compaction", "recovery"], "使用 faux provider 连续返回 overflow 或网络错误，验证上限、事件与上下文保留；定向测试通过。"),
    claim("C-010", "新 packages/agent AgentHarness 是低层 loop 之上的通用编排层，但 v0.80.7 尚未替代 Coding Agent AgentSession，且自身自动 compaction、retry、完整 hooks 与半持久恢复仍未完成。", "new AgentHarness migration state", "high", ["D-003", "D-008", "S-011", "X-002"], ["orchestration", "compaction", "recovery"], "检查 Coding Agent 创建路径是否实例化 AgentHarness，或 AgentHarness 是否包含 auto-compaction/retry decision；均未发现。"),
    claim("C-011", "真实 SiFlow 场景观察到 read 工具形成两轮 turn：模型 toolUse、read 执行、toolResult 回填、第二次模型调用、最终退出。", "R-SCENARIO-002", "high", ["R-002"], ["core_loop", "tools_extensions", "workspace"], "将 fixture 值改为未知随机值并要求必须读取；本轮使用合成未知值 314159 且 trace 显示 read start/end。"),
    claim("C-012", "持久化 session 能跨独立 Pi 进程恢复对话上下文。", "R-SCENARIO-003 and R-SCENARIO-004", "high", ["S-008", "R-003", "R-004"], ["sessions_persistence", "recovery"], "第二个进程不提供前一 token，仅恢复 session 后要求返回；已返回 PI_RESUME_2718。"),
    claim("C-013", "核心 Coding Agent 不内置 MCP 或 subagent；仓库提供的 subagent 是可选 extension，通过独立 pi --mode json --no-session 子进程隔离上下文，并共享指定 cwd。", "default core plus example extension", "high", ["D-004", "D-006", "S-015"], ["subagents", "tools_extensions"], "默认启动后检查 tool registry 是否出现 MCP/subagent；源码与产品文档否定，extension 场景未动态执行。"),
    claim("C-014", "Pi 已提供稳定的 agent/message/tool/compaction/retry 事件及 JSON/RPC 输出，但 OTel 风格 trace/span 仍是设计稿，不是 v0.80.7 的默认核心实现。", "observability surfaces", "high", ["D-005", "D-009", "R-001", "R-002"], ["observability"], "搜索并运行默认 instrumentation，检查是否生成 traceId/spanId 或 exporter 调用；JSON trace 未包含，源码只发现设计说明。", confidence="medium"),
    claim("C-015", "工具批次默认并行执行；全局 sequential 或任一工具声明 executionMode=sequential 会使整批串行，同时最终 toolResult 按模型源码顺序持久化。", "agent-core tool execution", "high", ["S-001", "X-001"], ["core_loop", "tools_extensions"], "脚本化两个不同延迟工具并比较完成事件与持久化结果顺序；定向 agent-loop 测试已通过。"),
    claim("C-016", "新 AgentHarness 通过 turn snapshot 与 save point 隔离在途 provider request：运行时配置变化只在下一个安全点刷新，pending session writes 按序落盘。", "new AgentHarness", "high", ["D-003", "S-011", "X-002"], ["orchestration", "sessions_persistence"], "在 tool hook 中切换 model/tools 并检查当前 request 与下一 request；AgentHarness 定向测试覆盖该语义。"),
    claim("C-017", "扩展可以实现工具阻断，但此控制点是应用可选 hook，不是不可绕过的全局安全边界。", "extension tool hooks", "high", ["S-003", "S-017", "D-002"], ["permissions_safety", "tools_extensions"], "枚举 built-in tools、user ! bash、extension custom tools 与直接进程调用，确认是否全部经过同一 hook；源码表明 extension 自身代码不受该 gate 约束。"),
    claim("C-018", "orchestrator 是实验性的多 Pi RPC 进程 supervisor，负责 spawn、事件复用、session 元数据和退出清理；它不是默认 Coding Agent 内的 subagent 机制。", "packages/orchestrator", "medium", ["D-010", "S-016"], ["subagents", "orchestration"], "从默认 pi CLI 追踪是否自动创建 OrchestratorSupervisor；未发现，orchestrator 包明确标记 experimental。", confidence="medium"),
    claim("C-019", "模型抽象以 provider-owned model catalog、auth resolution 和 stream/streamSimple 为边界；自定义 models.json 可把 OpenAI-compatible endpoint 接入同一循环。", "pi-ai and coding-agent model registry", "high", ["S-012", "R-005", "R-001"], ["model_abstraction"], "通过 models.json 注册 SiFlow 并运行 --list-models 与文本请求；两者均成功。"),
    claim("C-020", "恢复策略按错误类型分层：context overflow 走 compaction，其他 retryable provider error 走指数退避，truncated tool-call 参数则拒绝执行并回送错误。", "coding-agent and agent-core failure paths", "high", ["S-001", "S-009", "S-010", "X-001", "X-003"], ["recovery", "compaction", "core_loop"], "分别注入 length stop、overflow 与网络错误；定向测试覆盖三类分支。"),
]


EVIDENCE = [
    evidence("D-001", "D", "根 README 将 Pi 定义为 agent harness，并列出 coding-agent、agent-core、ai、tui 的职责。", source("README.md", 13, 33), ["C-001"]),
    evidence("D-002", "D", "安全文档明确 project trust 不是 sandbox，默认工具和 extensions 以 Pi 进程权限运行。", source("packages/coding-agent/docs/security.md", 3, 41), ["C-005", "C-006", "C-007", "C-017"]),
    evidence("D-003", "D", "AgentHarness 生命周期文档定义 orchestration、turn snapshot、pending writes、phase 和 save point。", source("packages/agent/docs/agent-harness.md", 1, 218), ["C-010", "C-016"]),
    evidence("D-004", "D", "Coding Agent 产品哲学明确无内置 MCP、subagents、permission popups、plan mode 与 background bash。", source("packages/coding-agent/README.md", 489, 503), ["C-005", "C-013"]),
    evidence("D-005", "D", "JSON mode 文档列出 session、agent、turn、message、tool、compaction 与 retry 事件。", source("packages/coding-agent/docs/json.md", 1, 76), ["C-014"]),
    evidence("D-006", "D", "可选 subagent example 文档说明独立 Pi 进程、隔离 context、并行/chain、abort 与共享 cwd。", source("packages/coding-agent/examples/extensions/subagent/README.md", 1, 175), ["C-013"]),
    evidence("D-007", "D", "容器文档把隔离分成 whole-process 与 tool-routing；host extensions 可能仍绕过 VM。", source("packages/coding-agent/docs/containerization.md", 3, 43), ["C-007"]),
    evidence("D-008", "D", "AgentHarness TODO 明确 auto-compaction、retry、generic hooks、semi-durable recovery 与 Coding Agent migration 尚未完成。", source("packages/agent/docs/agent-harness.md", 291, 411), ["C-010"]),
    evidence("D-009", "D", "Observability Design Notes 要求 vendor-neutral events，并把 trace/span adapter 描述为目标设计而非已完成 API。", source("packages/agent/docs/observability.md", 3, 169), ["C-014"], confidence="medium"),
    evidence("D-010", "D", "Orchestrator README 将包标为 experimental、API/行为不稳定。", source("packages/orchestrator/README.md", 1, 5), ["C-018"]),
    evidence("S-001", "S", "runAgentLoop 实现双层循环、模型流、toolUse、steering/follow-up、并行/串行工具、length-stop 拒绝执行与 hooks。", source("packages/agent/src/agent-loop.ts", 95, 755), ["C-002", "C-015", "C-020"]),
    evidence("S-002", "S", "AgentSession prompt pipeline 处理 extension command/input、skill/template、queue、auth、pre-prompt compaction 与 before_agent_start。", source("packages/coding-agent/src/core/agent-session.ts", 1023, 1223), ["C-003"]),
    evidence("S-003", "S", "AgentSession 把 extension tool_call/tool_result 安装为 agent before/afterToolCall，并动态刷新统一 tool registry。", source("packages/coding-agent/src/core/agent-session.ts", 415, 493), ["C-004", "C-005", "C-017"]),
    evidence("S-004", "S", "buildSystemPrompt 注入工具说明、project context、skills 与 cwd。", source("packages/coding-agent/src/core/system-prompt.ts", 27, 161), ["C-003"]),
    evidence("S-005", "S", "DefaultResourceLoader 先以不信任状态加载 bootstrap extensions，再解析 trust 并加载最终资源集合。", source("packages/coding-agent/src/core/resource-loader.ts", 330, 413), ["C-003", "C-006"]),
    evidence("S-006", "S", "resolveProjectTrusted 优先 override/extension/store，default ask 且无 UI 时返回 false。", source("packages/coding-agent/src/core/project-trust.ts", 46, 95), ["C-006"]),
    evidence("S-007", "S", "内置 bash 使用 cwd、继承环境和 detached process group；timeout 无默认值，abort/timeout kill process tree。", source("packages/coding-agent/src/core/tools/bash.ts", 27, 148), ["C-007"]),
    evidence("S-008", "S", "SessionManager 实现 v3 append-only JSONL tree、active leaf、compaction-aware context、restore 与 fork。", source("packages/coding-agent/src/core/session-manager.ts", 457, 1540), ["C-008", "C-012"]),
    evidence("S-009", "S", "AgentSession 把 overflow 与 threshold 分开处理，overflow 最多一次 compact-and-retry，并持久化 compaction entry 后重建 context。", source("packages/coding-agent/src/core/agent-session.ts", 1890, 2161), ["C-009", "C-020"]),
    evidence("S-010", "S", "普通 retryable assistant error 使用受 maxRetries 限制的指数退避，error 留在 session 但从 live context 移除。", source("packages/coding-agent/src/core/agent-session.ts", 2573, 2637), ["C-009", "C-020"]),
    evidence("S-011", "S", "新 AgentHarness 直接调用 runAgentLoop，创建 turn snapshot，在 turn_end flush writes 与发出 save_point。", source("packages/agent/src/harness/agent-harness.ts", 314, 616), ["C-010", "C-016"]),
    evidence("S-012", "S", "pi-ai Models 将 provider catalog、auth resolution 与 stream dispatch 统一在运行时 collection。", source("packages/ai/src/models.ts", 24, 369), ["C-019"]),
    evidence("S-013", "S", "main 根据 appMode 分派 RPC、interactive 或 print/JSON，并共享 createAgentSessionRuntime。", source("packages/coding-agent/src/main.ts", 650, 857), ["C-001"]),
    evidence("S-014", "S", "AgentSessionRuntime 在 session switch/fork/import 时 teardown 并重建 cwd-bound services。", source("packages/coding-agent/src/core/agent-session-runtime.ts", 67, 353), ["C-001", "C-008"]),
    evidence("S-015", "S", "subagent example 注册 extension tool，以 pi --mode json --no-session 子进程执行并通过 cwd 共享 workspace。", source("packages/coding-agent/examples/extensions/subagent/index.ts", 239, 698), ["C-013"]),
    evidence("S-016", "S", "OrchestratorSupervisor 为每个 instance 创建独立 RPC Pi 进程、转发 events、同步 session metadata 并处理退出。", source("packages/orchestrator/src/supervisor.ts", 63, 318), ["C-018"]),
    evidence("S-017", "S", "protected-paths example 通过可选 tool_call hook 阻断 write/edit，表明权限策略属于 extension。", source("packages/coding-agent/examples/extensions/protected-paths.ts", 1, 29), ["C-004", "C-005", "C-017"]),
    evidence("R-001", "R", "真实 SiFlow 文本场景观察到 session -> agent/turn -> assistant stream -> turn_end -> agent_end -> settled，最终 PI_TEXT_OK。", source("traces/normalized/R-001-text-only.normalized.jsonl", scenario_id="R-SCENARIO-001", trace_id="R-001"), ["C-002", "C-003", "C-014", "C-019"], conditions={"mode": "json", "tools": "disabled", "session": "ephemeral", "provider": "siflow"}),
    evidence("R-002", "R", "真实 read 场景观察到两次 turn、read start/end、toolResult 回填与最终值 314159。", source("traces/normalized/R-002-read-tool.normalized.jsonl", scenario_id="R-SCENARIO-002", trace_id="R-002"), ["C-002", "C-004", "C-011", "C-014"], conditions={"mode": "json", "tools": ["read"], "session": "ephemeral", "provider": "siflow"}),
    evidence("R-003", "R", "第一个独立 Pi 进程创建持久化 session 并写入合成 token，最终 ACK。", source("traces/normalized/R-003-session-create.normalized.jsonl", scenario_id="R-SCENARIO-003", trace_id="R-003"), ["C-008", "C-012"], conditions={"session_id": "analysis-resume-001", "provider": "siflow"}),
    evidence("R-004", "R", "第二个独立 Pi 进程恢复同一 session-id，并在未重给 token 的情况下返回 PI_RESUME_2718。", source("traces/normalized/R-004-session-resume.normalized.jsonl", scenario_id="R-SCENARIO-004", trace_id="R-004"), ["C-008", "C-012"], conditions={"session_id": "analysis-resume-001", "provider": "siflow"}),
    evidence("R-005", "R", "Pi --list-models 成功解析自定义 SiFlow models.json，显示 qwen3.6-35ba3b、262.1K context 与 16.4K max output。", source("runtime-tests.md", scenario_id="R-SCENARIO-000", command="pi-test.sh --list-models siflow"), ["C-019"], conditions={"provider": "siflow"}),
    evidence("X-001", "X", "agent-core 定向 Vitest：agent-loop.test.ts 与 agent.test.ts 共 39/39 通过。", source("runtime-tests.md", scenario_id="X-SCENARIO-001", command="vitest --run test/agent-loop.test.ts test/agent.test.ts"), ["C-002", "C-015", "C-020"]),
    evidence("X-002", "X", "新 AgentHarness 定向 Vitest：agent-harness、session、compaction 共 61/61 通过。", source("runtime-tests.md", scenario_id="X-SCENARIO-002", command="vitest --config vitest.harness.config.ts ..."), ["C-010", "C-016"]),
    evidence("X-003", "X", "Coding Agent 定向 Vitest：compaction、network retry、session context 共 31/31 通过。", source("runtime-tests.md", scenario_id="X-SCENARIO-003", command="vitest --config vitest.config.ts ..."), ["C-008", "C-009", "C-020"]),
]


def ref(path: str, start: int, end: int, symbol: str | None = None) -> dict:
    return {"path": path, "start_line": start, "end_line": end, "symbol": symbol}


def node(node_id: str, node_type: str, name: str, summary: str, evidence_ids: list[str], layer: str, *, status: str = "static_only", confidence: str = "high", lifecycle: str = "runtime", trust_zone: str = "process", persistence_tier: str = "live", conditions: dict | None = None, source_refs: list[dict] | None = None, **attributes: object) -> dict:
    return {
        "id": node_id,
        "type": node_type,
        "name": name,
        "summary": summary,
        "attributes": {"layer": layer, "lifecycle": lifecycle, "trust_zone": trust_zone, "persistence_tier": persistence_tier, **attributes},
        "conditions": conditions or {},
        "evidence_ids": evidence_ids,
        "confidence": confidence,
        "status": status,
        "source_refs": source_refs or [],
    }


def edge(edge_id: str, source_id: str, target_id: str, edge_type: str, label: str, evidence_ids: list[str], *, status: str = "static_only", confidence: str = "high", conditions: dict | None = None, source_refs: list[dict] | None = None) -> dict:
    return {"id": edge_id, "source": source_id, "target": target_id, "type": edge_type, "label": label, "conditions": conditions or {}, "evidence_ids": evidence_ids, "confidence": confidence, "status": status, "source_refs": source_refs or []}


NODES = [
    node("N-CLI", "Interface", "pi CLI / JSON / RPC / TUI", "Shared user and embedding interfaces.", ["S-013", "R-001"], "interface", status="runtime_verified", source_refs=[ref("packages/coding-agent/src/main.ts", 650, 857, "main")]),
    node("N-Main", "Entrypoint", "main()", "Parses mode, trust, resources, session and model configuration.", ["S-013", "R-001"], "interface", status="runtime_verified", source_refs=[ref("packages/coding-agent/src/main.ts", 473, 857, "main")]),
    node("N-SessionRuntime", "Router", "AgentSessionRuntime", "Owns one AgentSession and recreates cwd-bound services on structural session changes.", ["S-014", "R-004"], "orchestration", status="runtime_verified", source_refs=[ref("packages/coding-agent/src/core/agent-session-runtime.ts", 67, 353, "AgentSessionRuntime")]),
    node("N-AgentSession", "AgentLoop", "Coding Agent AgentSession", "Current product orchestration for prompt expansion, retry, compaction, extensions and persistence.", ["S-002", "S-003", "R-001", "X-003"], "orchestration", status="runtime_verified", source_refs=[ref("packages/coding-agent/src/core/agent-session.ts", 269, 2740, "AgentSession")]),
    node("N-AgentHarness", "AgentLoop", "New AgentHarness", "New generic orchestration layer with snapshots and save points; migration incomplete.", ["D-003", "S-011", "X-002"], "orchestration", status="experimental_verified", conditions={"surface": "agent-core API, not default coding-agent"}, source_refs=[ref("packages/agent/src/harness/agent-harness.ts", 152, 1010, "AgentHarness")]),
    node("N-LowLoop", "AgentLoop", "runAgentLoop", "Low-level model/tool/queue loop shared by Agent and AgentHarness.", ["S-001", "R-001", "R-002", "X-001"], "orchestration", status="runtime_verified", source_refs=[ref("packages/agent/src/agent-loop.ts", 95, 755, "runAgentLoop")]),
    node("N-Context", "ContextBuilder", "Context assembly", "Builds system + transcript + tools before the provider call.", ["S-001", "S-002", "S-004", "R-001"], "context-capability", status="runtime_verified", lifecycle="per-turn", source_refs=[ref("packages/agent/src/agent-loop.ts", 281, 314, "streamAssistantResponse")]),
    node("N-ResourceLoader", "ContextTransformer", "DefaultResourceLoader", "Discovers trusted resources, extensions, prompts, themes and skills.", ["S-005", "S-006"], "context-capability", lifecycle="startup/reload", source_refs=[ref("packages/coding-agent/src/core/resource-loader.ts", 159, 1025, "DefaultResourceLoader")]),
    node("N-ProjectContext", "PromptSource", "AGENTS/CLAUDE + SYSTEM", "Project/user instruction sources embedded in the system prompt.", ["S-004", "D-002"], "context-capability", lifecycle="startup/reload", trust_zone="workspace", source_refs=[ref("packages/coding-agent/src/core/system-prompt.ts", 43, 159, "buildSystemPrompt")]),
    node("N-Skills", "Skill", "Skills", "Metadata is advertised in system prompt and full skill content is injected on invocation.", ["S-002", "S-004"], "context-capability", lifecycle="startup/lazy", trust_zone="workspace"),
    node("N-Compactor", "Compactor", "Coding Agent compaction", "Summarizes older branch content and persists a compaction boundary.", ["S-009", "X-003"], "orchestration", status="experimental_verified", lifecycle="threshold/overflow/manual", persistence_tier="durable", source_refs=[ref("packages/coding-agent/src/core/agent-session.ts", 1890, 2161, "_checkCompaction")]),
    node("N-Models", "ModelAdapter", "pi-ai Models / ModelRegistry", "Provider catalog, auth and API dispatch boundary.", ["S-012", "R-005", "R-001"], "infrastructure", status="runtime_verified", trust_zone="network", source_refs=[ref("packages/ai/src/models.ts", 24, 369, "ModelsImpl")]),
    node("N-ModelCall", "ModelCall", "Provider request", "Streaming model request and response boundary.", ["S-001", "S-012", "R-001", "R-002"], "infrastructure", status="runtime_verified", trust_zone="network", lifecycle="per-turn"),
    node("N-ToolRegistry", "ToolRegistry", "Unified tool registry", "Merges built-in, extension and SDK tools with allow/exclude filters.", ["S-003", "R-002"], "context-capability", status="runtime_verified", source_refs=[ref("packages/coding-agent/src/core/agent-session.ts", 2397, 2487, "_refreshToolRegistry")]),
    node("N-ReadTool", "Tool", "read tool", "Built-in read capability observed in the real tool scenario.", ["R-002", "S-003"], "execution", status="runtime_verified", trust_zone="process", lifecycle="tool-call"),
    node("N-Bash", "ExecutionBackend", "Local bash backend", "Spawns inherited-environment shell in cwd with optional timeout.", ["S-007", "D-002"], "execution", trust_zone="host", lifecycle="tool-call", source_refs=[ref("packages/coding-agent/src/core/tools/bash.ts", 27, 148, "createLocalBashOperations")]),
    node("N-Hooks", "Hook", "Extension hooks", "Optional control/mutation hooks around input, context, tools, sessions and provider boundaries.", ["S-002", "S-003", "S-017", "X-001"], "governance", status="experimental_verified", trust_zone="process"),
    node("N-OptionalGate", "PermissionGate", "Optional extension gate", "Application-defined tool_call blocking; absent by default.", ["D-004", "S-017"], "governance", conditions={"extension_required": True}, trust_zone="process"),
    node("N-ProjectTrust", "PolicyRule", "Project trust", "Gates project-local settings/resources/extensions, not tool execution.", ["D-002", "S-005", "S-006"], "governance", lifecycle="startup/reload", trust_zone="resource-loading"),
    node("N-ExternalSandbox", "Sandbox", "External container / VM", "Optional OS/VM boundary; not part of the default process.", ["D-007"], "execution", conditions={"external_configuration": True}, trust_zone="external"),
    node("N-Workspace", "Workspace", "cwd workspace", "Shared filesystem root for built-in tools and optional child agents.", ["S-007", "R-002"], "execution", status="runtime_verified", trust_zone="host", persistence_tier="filesystem"),
    node("N-Session", "Session", "Live active session", "In-memory active branch and model context.", ["S-008", "R-003", "R-004"], "state", status="runtime_verified", persistence_tier="live"),
    node("N-SessionStore", "SessionStore", "Session JSONL v3", "Append-only durable tree with header, entries and parent links.", ["S-008", "R-003", "R-004"], "state", status="runtime_verified", persistence_tier="durable", source_refs=[ref("packages/coding-agent/src/core/session-manager.ts", 780, 1540, "SessionManager")]),
    node("N-Retry", "RecoveryPolicy", "Retry / overflow recovery", "Exponential provider retry and one-shot overflow compaction recovery.", ["S-009", "S-010", "X-003"], "orchestration", status="experimental_verified", lifecycle="failure"),
    node("N-Events", "TelemetrySink", "Agent events + JSON/RPC", "Structured lifecycle event output; not a native span exporter.", ["D-005", "R-001", "R-002"], "observability", status="runtime_verified", persistence_tier="stream"),
    node("N-SubagentPlugin", "Plugin", "Subagent example extension", "Optional tool that spawns separate Pi processes.", ["D-006", "S-015"], "extension", conditions={"extension_required": True}, trust_zone="process"),
    node("N-Subagent", "Subagent", "Child pi process", "Separate context, same configured cwd unless overridden.", ["D-006", "S-015"], "orchestration", conditions={"extension_required": True}, trust_zone="child-process", agent_role="worker"),
    node("N-Orchestrator", "Planner", "Experimental OrchestratorSupervisor", "Supervises independent RPC Pi instances; outside default CLI.", ["D-010", "S-016"], "orchestration", conditions={"package": "experimental"}, trust_zone="supervisor", agent_role="supervisor"),
    node("N-Exit", "ExitCondition", "agent_end / agent_settled", "No more tool calls or queued messages; product-level retry/compaction also settled.", ["S-001", "R-001", "R-002"], "orchestration", status="runtime_verified", lifecycle="turn-end"),
]


EDGES = [
    edge("E-CLI-Main", "N-CLI", "N-Main", "enters", "invoke", ["S-013", "R-001"], status="runtime_verified"),
    edge("E-Main-Runtime", "N-Main", "N-SessionRuntime", "calls", "create runtime", ["S-013", "R-001"], status="runtime_verified"),
    edge("E-Runtime-Session", "N-SessionRuntime", "N-AgentSession", "calls", "own/rebind", ["S-014", "R-004"], status="runtime_verified"),
    edge("E-AgentSession-Loop", "N-AgentSession", "N-LowLoop", "calls", "prompt/continue", ["S-002", "R-001", "R-002"], status="runtime_verified"),
    edge("E-AgentHarness-Loop", "N-AgentHarness", "N-LowLoop", "calls", "direct loop", ["S-011", "X-002"], status="experimental_verified", conditions={"surface": "new AgentHarness"}),
    edge("E-Session-Context", "N-Session", "N-Context", "reads", "active branch", ["S-008", "R-004"], status="runtime_verified"),
    edge("E-Resource-Context", "N-ResourceLoader", "N-Context", "assembles", "resources", ["S-002", "S-005"]),
    edge("E-Project-Context", "N-ProjectContext", "N-Context", "injects", "project instructions", ["S-004"]),
    edge("E-Skills-Context", "N-Skills", "N-Context", "injects", "metadata/invocation", ["S-002", "S-004"]),
    edge("E-Trust-Resource", "N-ProjectTrust", "N-ResourceLoader", "authorizes", "load project resources", ["D-002", "S-005", "S-006"]),
    edge("E-Loop-Context", "N-LowLoop", "N-Context", "assembles", "convert before request", ["S-001", "R-001"], status="runtime_verified"),
    edge("E-Context-Model", "N-Context", "N-ModelCall", "calls", "system/messages/tools", ["S-001", "R-001"], status="runtime_verified"),
    edge("E-Models-Call", "N-Models", "N-ModelCall", "executes", "auth + dispatch", ["S-012", "R-001"], status="runtime_verified"),
    edge("E-Model-Tool", "N-ModelCall", "N-ReadTool", "proposes", "toolUse", ["R-002"], status="runtime_verified"),
    edge("E-Registry-Tool", "N-ToolRegistry", "N-ReadTool", "registers", "active tool", ["S-003", "R-002"], status="runtime_verified"),
    edge("E-Loop-Tool", "N-LowLoop", "N-ReadTool", "executes", "dispatch", ["S-001", "R-002"], status="runtime_verified"),
    edge("E-Hook-Gate", "N-Hooks", "N-OptionalGate", "calls", "tool_call policy", ["S-003", "S-017", "X-001"], status="experimental_verified", conditions={"extension_required": True}),
    edge("E-Gate-Tool", "N-OptionalGate", "N-ReadTool", "authorizes", "allow/block", ["S-003", "S-017"], conditions={"extension_required": True}),
    edge("E-Read-Workspace", "N-ReadTool", "N-Workspace", "reads", "fixture.txt", ["R-002"], status="runtime_verified"),
    edge("E-Tool-Context", "N-ReadTool", "N-Context", "appends_to_context", "toolResult", ["S-001", "R-002"], status="runtime_verified"),
    edge("E-Bash-Workspace", "N-Bash", "N-Workspace", "executes", "local shell", ["S-007", "D-002"]),
    edge("E-Sandbox-Bash", "N-ExternalSandbox", "N-Bash", "executes", "optional routed backend", ["D-007"], conditions={"external_configuration": True}),
    edge("E-AgentSession-Session", "N-AgentSession", "N-Session", "writes", "live messages", ["S-002", "S-008", "R-003"], status="runtime_verified"),
    edge("E-Session-Store", "N-Session", "N-SessionStore", "persists", "append JSONL", ["S-008", "R-003"], status="runtime_verified"),
    edge("E-Store-Session", "N-SessionStore", "N-Session", "restores", "active branch", ["S-008", "R-004"], status="runtime_verified"),
    edge("E-Compactor-Session", "N-Compactor", "N-Session", "compacts", "summary boundary", ["S-009", "X-003"], status="experimental_verified"),
    edge("E-Compactor-Store", "N-Compactor", "N-SessionStore", "persists", "compaction entry", ["S-008", "S-009", "X-003"], status="experimental_verified"),
    edge("E-Retry-Agent", "N-Retry", "N-AgentSession", "retries", "bounded continue", ["S-009", "S-010", "X-003"], status="experimental_verified"),
    edge("E-Loop-Events", "N-LowLoop", "N-Events", "emits_trace", "lifecycle events", ["D-005", "R-001", "R-002"], status="runtime_verified"),
    edge("E-Loop-Exit", "N-LowLoop", "N-Exit", "exits_to", "no tools/queues", ["S-001", "R-001"], status="runtime_verified"),
    edge("E-Plugin-Registry", "N-SubagentPlugin", "N-ToolRegistry", "registers", "subagent tool", ["S-015"], conditions={"extension_required": True}),
    edge("E-Plugin-Subagent", "N-SubagentPlugin", "N-Subagent", "delegates", "spawn pi --mode json", ["D-006", "S-015"], conditions={"extension_required": True}),
    edge("E-Subagent-Workspace", "N-Subagent", "N-Workspace", "shares_workspace_with", "same cwd by default", ["D-006", "S-015"], conditions={"extension_required": True}),
    edge("E-Subagent-Context", "N-Subagent", "N-AgentSession", "isolates_context_from", "separate process/no session", ["D-006", "S-015"], conditions={"extension_required": True}),
    edge("E-Orchestrator-Subagent", "N-Orchestrator", "N-Subagent", "delegates", "independent RPC instance", ["D-010", "S-016"], conditions={"package": "experimental"}),
]


MODULES = {
    "interfaces": ("analyzed", ["packages/coding-agent/src/main.ts", "packages/coding-agent/src/modes/print-mode.ts", "packages/coding-agent/src/modes/rpc/rpc-mode.ts"], ["R-SCENARIO-001", "R-SCENARIO-002"], []),
    "core_loop": ("analyzed", ["packages/agent/src/agent-loop.ts", "packages/agent/src/agent.ts", "packages/coding-agent/src/core/agent-session.ts"], ["R-SCENARIO-001", "R-SCENARIO-002", "X-SCENARIO-001"], []),
    "context_assembly": ("partial", ["packages/coding-agent/src/core/system-prompt.ts", "packages/coding-agent/src/core/resource-loader.ts", "packages/coding-agent/src/core/agent-session.ts"], ["R-SCENARIO-001"], ["未代理捕获完整 provider request；未动态差分 skills/context files/extensions。"]),
    "compaction": ("analyzed", ["packages/coding-agent/src/core/compaction", "packages/coding-agent/src/core/agent-session.ts", "packages/agent/src/harness/compaction"], ["X-SCENARIO-002", "X-SCENARIO-003"], ["未用真实模型触发 262K 上下文 overflow。"]),
    "model_abstraction": ("analyzed", ["packages/ai/src/models.ts", "packages/coding-agent/src/core/model-registry.ts", "packages/coding-agent/docs/models.md"], ["R-SCENARIO-000", "R-SCENARIO-001"], ["SiFlow 服务端默认 thinking 与 Pi reasoning=false 存在兼容差异。"]),
    "tools_extensions": ("analyzed", ["packages/agent/src/agent-loop.ts", "packages/coding-agent/src/core/agent-session.ts", "packages/coding-agent/src/core/extensions"], ["R-SCENARIO-002", "X-SCENARIO-001"], ["未动态运行自定义 extension tool。"]),
    "permissions_safety": ("analyzed", ["packages/coding-agent/docs/security.md", "packages/coding-agent/src/core/project-trust.ts", "packages/coding-agent/examples/extensions/protected-paths.ts"], [], ["未执行破坏性 allow/deny side-effect 场景；结论主要来自明确文档与源码。"]),
    "sandbox_execution": ("partial", ["packages/coding-agent/src/core/tools/bash.ts", "packages/coding-agent/docs/containerization.md", "packages/coding-agent/examples/extensions/gondolin"], [], ["Gondolin 要求 Node >=23.6 与 QEMU，本轮 Node 22.19 环境未运行；Docker/OpenShell 未运行。"]),
    "workspace": ("analyzed", ["packages/coding-agent/src/core/tools", "packages/coding-agent/src/core/agent-session-runtime.ts"], ["R-SCENARIO-002"], ["只验证只读 workspace；写/edit/bash 未动态执行。"]),
    "sessions_persistence": ("analyzed", ["packages/coding-agent/src/core/session-manager.ts", "packages/coding-agent/src/core/agent-session-runtime.ts", "packages/agent/src/harness/session"], ["R-SCENARIO-003", "R-SCENARIO-004", "X-SCENARIO-003"], ["未做 corrupted JSONL 注入与跨版本 migration 动态测试。"]),
    "subagents": ("partial", ["packages/coding-agent/examples/extensions/subagent", "packages/orchestrator/src"], [], ["核心无内置 subagent；可选 extension 与 experimental orchestrator 均未动态运行。"]),
    "orchestration": ("analyzed", ["packages/agent/src/harness/agent-harness.ts", "packages/coding-agent/src/core/agent-session.ts", "packages/orchestrator/src/supervisor.ts"], ["R-SCENARIO-001", "X-SCENARIO-002"], ["Coding Agent 迁移到新 AgentHarness 尚未完成。"]),
    "observability": ("partial", ["packages/agent/src/types.ts", "packages/coding-agent/docs/json.md", "packages/agent/docs/observability.md"], ["R-SCENARIO-001", "R-SCENARIO-002"], ["默认没有 trace/span correlation IDs；OTel adapter 设计未实现。"]),
    "recovery": ("analyzed", ["packages/coding-agent/src/core/agent-session.ts", "packages/coding-agent/src/core/agent-session-runtime.ts", "packages/agent/src/harness/agent-harness.ts"], ["R-SCENARIO-004", "X-SCENARIO-003"], ["未执行真实 SIGINT、tool timeout、进程 crash 或半持久 turn recovery。"]),
}


def coverage_record(status: str, files: list[str], scenarios: list[str], unresolved: list[str]) -> dict:
    return {
        "status": status,
        "directories": sorted({str(Path(file).parent) for file in files}),
        "files": files,
        "symbols": [],
        "configurations": ["v0.80.7", "default-source", "isolated-json-mode"],
        "scenarios": scenarios,
        "excluded_surfaces": [],
        "unresolved": unresolved,
        "notes": "Source inspected at pinned commit; runtime occurrence is configuration-specific.",
    }


SCENARIOS = {
    "schema_version": "1.0",
    "safety_gate": {
        "authorization": "User explicitly authorized use of the supplied SiFlow endpoint for agent tests.",
        "workspace": "/tmp/pi-analysis-runtime/fixture",
        "home": "/tmp/pi-analysis-runtime/home",
        "session_dir": "/tmp/pi-analysis-runtime/sessions",
        "network": "Only the configured SiFlow HTTPS endpoint; npm/node downloads occurred during setup.",
        "credentials": "No API key stored or required; models.json used a non-secret placeholder.",
        "limits": {"tools": "disabled or read-only", "shell_side_effects": "not exercised", "cost_rates": 0},
    },
    "scenarios": [
        {"id": "R-SCENARIO-000", "mode": "real", "title": "Custom model discovery", "status": "passed", "result": "siflow/qwen3.6-35ba3b listed"},
        {"id": "R-SCENARIO-001", "mode": "real", "title": "Text-only stop", "status": "passed", "claims_tested": ["C-002", "C-019"], "result": "PI_TEXT_OK", "trace": "traces/normalized/R-001-text-only.normalized.jsonl"},
        {"id": "R-SCENARIO-002", "mode": "real", "title": "Read tool loop", "status": "passed", "claims_tested": ["C-002", "C-004", "C-011"], "result": "read executed; final 314159", "trace": "traces/normalized/R-002-read-tool.normalized.jsonl"},
        {"id": "R-SCENARIO-003", "mode": "real", "title": "Create persistent session", "status": "passed", "claims_tested": ["C-008", "C-012"], "result": "ACK and JSONL persisted", "trace": "traces/normalized/R-003-session-create.normalized.jsonl"},
        {"id": "R-SCENARIO-004", "mode": "real", "title": "Resume persistent session", "status": "passed", "claims_tested": ["C-008", "C-012"], "result": "PI_RESUME_2718 recovered in a new process", "trace": "traces/normalized/R-004-session-resume.normalized.jsonl"},
        {"id": "X-SCENARIO-001", "mode": "scripted-faux", "title": "agent-core loop tests", "status": "passed", "result": "39/39"},
        {"id": "X-SCENARIO-002", "mode": "scripted-faux", "title": "new AgentHarness tests", "status": "passed", "result": "61/61"},
        {"id": "X-SCENARIO-003", "mode": "scripted-faux", "title": "Coding Agent compaction/retry/session tests", "status": "passed", "result": "31/31"},
    ],
}


QUESTIONS = {
    "schema_version": "1.0",
    "questions": [
        {"id": "Q-001", "priority": "high", "status": "open", "question": "Coding Agent 何时以及如何迁移到新 AgentHarness？迁移前两套编排语义会怎样保持一致？", "next_experiment": "对同一 faux script 做 AgentSession/AgentHarness differential test。"},
        {"id": "Q-002", "priority": "high", "status": "open", "question": "外部 Gondolin/Docker/OpenShell 路径是否覆盖全部 extension tools、用户 ! bash 与凭证边界？", "next_experiment": "在 Node 24 + QEMU 或容器环境运行 side-effect matrix。"},
        {"id": "Q-003", "priority": "medium", "status": "open", "question": "部分损坏 JSONL 的恢复策略是跳过、拒绝还是可能静默改变 active branch？", "next_experiment": "复制合成 session，逐类破坏 header/middle/tail/parentId 并恢复。"},
        {"id": "Q-004", "priority": "medium", "status": "open", "question": "可选 subagent extension 的 project-agent confirmation 在 JSON/RPC headless 模式下如何退化？", "next_experiment": "用 faux provider 分别在 interactive/json/rpc 触发 project agent。"},
        {"id": "Q-005", "priority": "medium", "status": "open", "question": "SiFlow endpoint 如何在 Pi models.json 中稳定关闭服务端 thinking？", "next_experiment": "确认 provider 是否支持 request body extension/chat_template_kwargs。"},
        {"id": "Q-006", "priority": "low", "status": "open", "question": "experimental orchestrator 的 crash/restart 是否可恢复运行中的 RPC instance，而非仅把记录标记 stopped？", "next_experiment": "spawn instance 后 kill supervisor 并运行 recoverAfterRestart。"},
    ],
}


MANIFEST = {
    "schema_version": "1.0",
    "analysis_status": "complete_with_known_gaps",
    "created_at": "2026-07-15T09:16:46.703822+00:00",
    "completed_at": "2026-07-15T10:00:00+00:00",
    "target": {"repository_root": TARGET, "tag": "v0.80.7", "commit": COMMIT, "branch": None, "dirty": False, "changed_path_count": 0},
    "scope": {
        "entrypoints": ["coding-agent CLI interactive", "coding-agent print/JSON", "coding-agent RPC", "agent-core SDK", "experimental orchestrator (static only)"],
        "configurations": ["v0.80.7 source snapshot", "isolated JSON mode", "SiFlow qwen3.6-35ba3b", "faux-provider unit scenarios"],
        "enabled_features": ["read tool in R-SCENARIO-002", "session persistence in R-SCENARIO-003/004"],
        "disabled_features": ["project extensions", "skills", "prompt templates", "context files", "write/edit/bash in real-model scenarios"],
        "inaccessible_surfaces": ["Gondolin/QEMU", "Docker/OpenShell", "production usage flags/configuration", "maintainer design intent beyond repository docs"],
    },
    "execution": {
        "isolation": "Disposable /tmp HOME, fixture and session directory; target source snapshot not modified.",
        "filesystem_policy": "Real-model runs limited to no tools or read-only fixture; generated analysis artifacts under external bundle.",
        "network_policy": "SiFlow endpoint for authorized model scenarios; dependency/runtime downloads during setup.",
        "credential_policy": "No API key stored; non-secret placeholder only; normalized traces remove prompts, reasoning, tool args and contents.",
        "model_mode": "real SiFlow for representative paths; repository faux provider for deterministic controller tests",
        "model_provider": "siflow/qwen3.6-35ba3b",
        "runtime_versions": {"node": "22.19.0", "npm": "10.9.3", "vitest": "4.1.9", "python": "3.x"},
    },
    "tooling": {"skill": "harness-analysis", "skill_schema_version": "1.0", "skill_commit": "7f2847d3cfa5d1964576ea99265ca83bbe234bf8"},
}


def main() -> int:
    write_json(ROOT / "manifest.json", MANIFEST)
    write_jsonl(ROOT / "evidence" / "claims.jsonl", CLAIMS)
    write_jsonl(ROOT / "evidence" / "observations.jsonl", EVIDENCE)
    write_jsonl(ROOT / "evidence" / "conflicts.jsonl", [])
    write_json(
        ROOT / "evidence" / "coverage.json",
        {
            "schema_version": "1.0",
            "global": {
                "entrypoints_examined": MANIFEST["scope"]["entrypoints"],
                "configurations_tested": MANIFEST["scope"]["configurations"],
                "providers_tested": ["siflow/qwen3.6-35ba3b", "pi-ai faux provider"],
                "platforms_tested": ["linux x86_64, Node 22.19.0"],
                "inaccessible_surfaces": MANIFEST["scope"]["inaccessible_surfaces"],
                "unresolved_high_value_questions": ["Q-001", "Q-002", "Q-003"],
                "search_limits": {"max_files": 20000, "max_file_size": 1000000, "max_hits_per_category": 120, "file_limit_reached": False},
            },
            "modules": {module_id: coverage_record(*record) for module_id, record in MODULES.items()},
        },
    )
    write_json(ROOT / "hir.json", {"schema_version": "1.0", "repository": {"root": TARGET, "commit": COMMIT, "entrypoints": MANIFEST["scope"]["entrypoints"], "configurations": MANIFEST["scope"]["configurations"]}, "nodes": NODES, "edges": EDGES})
    write_json(ROOT / "scenarios" / "catalog.json", SCENARIOS)
    write_json(ROOT / "questions.json", QUESTIONS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
