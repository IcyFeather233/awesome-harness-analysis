#!/usr/bin/env python3
"""Compile the Codex v0.144.5 evidence model and Chinese report."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from augment_mailbox_evidence import augment_structured_evidence
from enrich_report_explanations import enrich_reports


ROOT = Path(__file__).resolve().parent.parent
COMMIT = "87db9bc18ba5bc82c1cb4e4381b44f693ee35623"
TAG_OBJECT = "efea0e66996d4e7f4f805f3df32a169d327f2f73"
SOURCE = f"https://github.com/openai/codex/blob/{COMMIT}"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, values: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n" for value in values),
        encoding="utf-8",
    )


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.strip() + "\n", encoding="utf-8")


def source_url(path: str, line: int) -> str:
    return f"{SOURCE}/{path}#L{line}"


def evidence(
    evidence_id: str,
    kind: str,
    summary: str,
    locator: str,
    supports: list[str],
    *,
    path: str | None = None,
    line: int | None = None,
    end: int | None = None,
    symbol: str | None = None,
    scenario: str | None = None,
    command: str | None = None,
    conditions: dict | None = None,
    confidence: str = "high",
    notes: str | None = None,
) -> dict:
    record = {
        "id": evidence_id,
        "record_type": "evidence",
        "kind": kind,
        "summary": summary,
        "source": {
            "locator": locator,
            "path": path,
            "start_line": line,
            "end_line": end,
            "symbol": symbol,
            "url": source_url(path, line) if path and line else None,
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
    importance: str = "high",
    conditions: dict | None = None,
) -> dict:
    return {
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
        "coverage_refs": modules,
        "falsification_test": falsification,
    }


CLAIMS = [
    claim("C-001", "Codex CLI、TUI、exec、app-server 与 MCP server 是不同产品表面，但会收敛到同一 core session/thread runtime。", "rust-v0.144.5 product surfaces", ["D-001", "D-003", "S-001", "R-001"], ["interfaces", "orchestration"], "为每个入口寻找独立 agent loop；本轮静态追踪未发现，app-server 仍通过 thread/session core。"),
    claim("C-002", "常规 turn 是一个显式采样循环：组装 prompt、流式读取 Responses、并行或独占执行工具、把结果写回 history，并在需要时继续采样。", "RegularTask and run_turn", ["S-002", "S-003", "X-001", "X-002"], ["core_loop", "orchestration"], "脚本化一次 function_call，检查是否存在不回填 tool output 的直接退出；X-002 观察到两次请求和 output 回填。"),
    claim("C-003", "模型请求由 base instructions、会话 history、world-state 更新、每 turn 输入和当前可见 tool specs 共同构成。", "default exec/read-only configuration", ["D-007", "S-004", "S-005"], ["context_assembly"], "分别关闭项目指令、skills、MCP 与动态工具后比较请求体；本轮只验证了最小配置，完整差分未执行。", confidence="medium"),
    claim("C-004", "Codex 把对话历史与可差分的 world state 分开管理：history 保留模型可见 items，world state 用 RFC 7386 风格 snapshot/diff 减少重复注入。", "core context manager", ["D-007", "S-005", "S-006", "I-001"], ["context_assembly", "workspace"], "修改 cwd、AGENTS.md、subagent 列表并比较 world-state items；源码支持，动态差分仍待专项实验。", confidence="medium"),
    claim("C-005", "自动 compaction 既可能在 turn 前触发，也可能在 tool follow-up 中触发；实现还区分 remote v2、remote v1 与 local compaction，并处理模型上下文下调。", "core compaction", ["S-007"], ["compaction", "recovery"], "使用 scripted provider 推高 token estimate，分别触发 pre-turn、mid-turn 和 model-switch；本轮未执行超长上下文场景。", confidence="medium"),
    claim("C-006", "ModelClientSession 在 turn 内跨 retry 复用 transport 状态，WebSocket 不可用时会 session-scoped 回退，增量请求依赖前缀匹配。", "Responses model boundary", ["S-008", "S-024"], ["model_abstraction", "recovery"], "构造 WebSocket 首次失败、随后成功的 provider，并检查回退是否只在该 session 生效；未动态执行。", confidence="medium"),
    claim("C-007", "工具 registry 与模型可见 exposure 是两层：工具可已注册但延迟/隐藏；当前 turn 再把内置工具、MCP、connectors、extensions 与 dynamic tools 合成为 specs。", "tool spec planning", ["S-004", "S-009", "S-026"], ["tools_extensions", "context_assembly"], "注册 hidden/deferred tool 并要求模型调用，检查 router 是否保有实现但请求 specs 不暴露；静态实现明确。"),
    claim("C-008", "ToolRouter 统一解析调用，registry 在 handler 前执行 pre-tool hooks；ToolCallRuntime 以读写锁允许只读工具并行、要求独占的工具串行。", "core tool runtime", ["S-010", "S-011", "S-025"], ["tools_extensions", "orchestration"], "脚本化两个 read-only 与一个 exclusive 工具，比较开始/结束事件；本轮只验证单工具往返。", confidence="medium"),
    claim("C-009", "真正启动进程的 exec 路径先计算 approval/exec-policy requirement，再进入 sandbox；在 approval_policy=never 时，模型请求 require_escalated 会在创建进程前被拒绝。", "exec tool, never/read-only", ["S-012", "S-013", "S-014", "X-004", "X-007"], ["permissions_safety", "sandbox_execution"], "请求 touch 文件并声明 require_escalated；X-004 返回 policy error，X-007 证实目录与文件哈希未变。"),
    claim("C-010", "sandbox 是 platform-specific execution transform：Linux、macOS、Windows 使用不同后端，权限 profile 还独立表达 filesystem 与 network；它不是单一布尔开关。", "platform execution layer", ["D-002", "S-014", "I-002"], ["sandbox_execution", "permissions_safety"], "在三平台运行相同 side-effect matrix；本轮只在 Linux 主机验证 policy 前置拒绝，未覆盖实际 sandbox backend。", confidence="medium"),
    claim("C-011", "ThreadStore/LiveThread 是持久化边界，rollout 采用追加式 JSONL；resume 会加载历史并保持同一 thread id。", "local rollout store", ["D-004", "S-018", "S-019", "X-006"], ["sessions_persistence", "recovery"], "新进程恢复首轮 session 并比较 thread id 与请求历史；X-006 观察到同 id 和增加的 assistant/user items。"),
    claim("C-012", "subagent 是独立 Codex child session：拥有自己的 channel、context 与 history，继承有效配置/审批/sandbox/cwd，并通过共享 AgentControl 受父树治理。", "multi_agent V1", ["S-015", "S-016", "S-017", "X-005"], ["subagents", "orchestration", "workspace"], "创建 child 后比较 request digest、工具集合、cwd 与 policy；X-005 证实独立请求和不同 tool exposure，完整隔离矩阵未跑。", confidence="medium"),
    claim("C-013", "V1 与 V2 multi-agent 是分离 feature gate；v0.144.5 默认 V1 开启、V2 关闭，默认并发/深度限制阻止无界递归。", "feature configuration", ["S-015", "X-005"], ["subagents", "orchestration"], "分别启用 V1/V2 并检查工具 namespace、child depth 与并发上限；本轮仅运行 V1。", confidence="medium"),
    claim("C-014", "长期 memories 是默认关闭的实验性两阶段流水线：Phase 1 从 rollout 提取结构化记忆，Phase 2 在全局锁下由专用 agent 聚合到 durable memory 文件。", "experimental memories feature", ["D-005", "S-020"], ["context_assembly", "sessions_persistence"], "启用 memories 后创建多个 eligible rollout，等待 phase1/phase2 并检查租约、红action与合并结果；本轮未启用。", confidence="medium"),
    claim("C-015", "app-server 用双向 JSON-RPC 暴露 thread 生命周期，并把处理 loop 与 outbound writer loop 分开，以避免慢客户端阻塞请求处理。", "app-server", ["D-003", "S-023"], ["interfaces", "observability"], "构造慢 writer 和突发通知，观察有界队列背压与 processor 是否继续；未动态执行。", confidence="medium"),
    claim("C-016", "Codex 同时暴露产品事件与 OTel logs/traces/metrics；turn、tool call、conversation id 和 token/timing 是主要关联键，默认不记录用户 prompt。", "observability surfaces", ["D-006", "S-021"], ["observability"], "启用本地 OTel exporter 并执行 tool turn，校验 trace-parent 与 prompt redaction；本轮 exporter 关闭。", confidence="medium"),
    claim("C-017", "恢复不是一个全局 retry：provider stream retry 有界，tool/turn cancellation 由 token 传播，turn 结束前会尝试 flush rollout；失败 turn 不必销毁 session。", "turn recovery", ["S-002", "S-003", "S-008", "S-022"], ["recovery", "core_loop"], "分别注入 stream timeout、tool hang、rollout I/O failure 和 user interrupt，检查边界与 session 后续可用性；未完整执行。", confidence="medium"),
    claim("C-018", "用户提供的 SiFlow endpoint 支持基础 Responses SSE，但不能直接接受 Codex 0.144.5 的完整请求方言：最小路径拒绝 developer role，V1 路径拒绝 namespace tool。", "SiFlow qwen3.6-35ba3b compatibility on 2026-07-16", ["S-024", "R-002", "R-003"], ["model_abstraction", "recovery"], "不改 Codex 请求直接运行真实 endpoint；两种配置均在模型输出前稳定返回 HTTP 400。", conditions={"provider": "siflow/qwen3.6-35ba3b"}),
    claim("C-019", "确定性 Responses fixture 观察到 function_call -> exec_command -> function_call_output -> 第二次 model request 的闭环，工具结果进入了下一轮 context。", "X-SCENARIO-002", ["S-003", "S-010", "X-002"], ["core_loop", "tools_extensions"], "让第二次响应仅在看到指定 call_id 的 function_call_output 时返回验证码；场景通过。"),
    claim("C-020", "未知工具和被 policy 拒绝的工具调用都会变成模型可消费的结果，而不是让整个 session 无条件崩溃。", "scripted failure paths", ["S-010", "S-011", "X-003", "X-004"], ["tools_extensions", "permissions_safety", "recovery"], "请求不存在工具与禁止提权命令，要求 fixture 只在收到 tool output 后结束；两场景均继续到 final answer。"),
    claim("C-021", "一次持久化 turn 与随后 resume 在两个进程中保持同一 thread id，且恢复后的 provider input 包含首轮 assistant 消息。", "X-SCENARIO-006", ["S-018", "S-019", "X-006"], ["sessions_persistence", "recovery"], "恢复时不重发首轮输出，只检查第二次 provider input；观察到 input_count 从 3 增至 5。"),
    claim("C-022", "V1 child 的初始请求与 root 独立，且达到默认深度后不再暴露 multi_agent namespace；root 与 child 仍共享同一 workspace 语义。", "X-SCENARIO-005 and default max_depth=1", ["S-015", "S-016", "X-005"], ["subagents", "workspace"], "在 child 请求中检查 namespace tool 是否消失，并尝试继续 spawn；本轮请求日志证实 tool exposure 消失，未再请求 spawn。", confidence="medium"),
    claim("C-023", "并发工具语义由 handler 的 parallel/exclusive 分类控制，而不是对所有 tool calls 一律并行。", "ToolCallRuntime", ["S-025"], ["tools_extensions", "orchestration"], "脚本化并发读写工具并记录锁获取顺序；本轮仅有源码证据。", confidence="medium", importance="medium"),
    claim("C-024", "shell 与 unified-exec handler 会在通用 exec-policy requirement 之前识别 apply_patch，并把它路由到具有独立 patch safety、按路径 approval cache 与 sandbox runtime 的专用治理路径；因此 exec-policy → sandbox 不能泛化为所有 shell tool 输入。", "apply_patch interception in shell and unified exec", ["S-028"], ["tools_extensions", "permissions_safety", "sandbox_execution"], "分别通过 shell、unified exec 和直接 apply_patch tool 提交同一补丁，比较是否都进入 ApplyPatchRuntime、是否按文件路径请求 approval，并确认没有普通进程 spawn。", confidence="medium", importance="high"),
]


OBSERVATIONS = [
    evidence("D-001", "D", "仓库 README 将 Codex CLI 定义为本地运行的 coding agent，并给出 CLI 产品边界。", "README.md", ["C-001"], path="README.md", line=1, end=40),
    evidence("D-002", "D", "core README 记录 Linux/macOS/Windows 的 sandbox 后端、fallback 与用户命名空间约束。", "codex-rs/core/README.md", ["C-010"], path="codex-rs/core/README.md", line=1, end=180),
    evidence("D-003", "D", "app-server README 定义双向 JSON-RPC、thread start/resume/fork 与通知协议。", "codex-rs/app-server/README.md", ["C-001", "C-015"], path="codex-rs/app-server/README.md", line=1, end=180),
    evidence("D-004", "D", "thread-store README 明确 ThreadStore/LiveThread 是 storage-neutral durable thread API。", "codex-rs/thread-store/README.md", ["C-011"], path="codex-rs/thread-store/README.md", line=1, end=180),
    evidence("D-005", "D", "memories README 说明记忆提取与 consolidation 的两阶段设计。", "codex-rs/memories/README.md", ["C-014"], path="codex-rs/memories/README.md", line=1, end=220),
    evidence("D-006", "D", "OTel README 说明 logs/traces/metrics exporter、W3C propagation 与显式 shutdown。", "codex-rs/otel/README.md", ["C-016"], path="codex-rs/otel/README.md", line=1, end=180),
    evidence("D-007", "D", "仓库 AGENTS.md 要求模型可见 context 增量化、避免改写历史、片段有界，并把动态注入建模为 ContextualUserFragment。", "AGENTS.md", ["C-003", "C-004"], path="AGENTS.md", line=1, end=220),
    evidence("S-001", "S", "CLI subcommands 将 exec、mcp-server、app-server 与默认 TUI 分派到对应入口。", "codex-rs/cli/src/main.rs:Subcommand", ["C-001"], path="codex-rs/cli/src/main.rs", line=124, end=160, symbol="Subcommand"),
    evidence("S-002", "S", "RegularTask 发出 TurnStarted、调用 run_turn，并只为排队用户输入启动下一 turn。", "codex-rs/core/src/tasks/regular.rs:RegularTask::run", ["C-002", "C-017"], path="codex-rs/core/src/tasks/regular.rs", line=37, end=89, symbol="RegularTask::run"),
    evidence("S-003", "S", "run_turn 的主循环构造 prompt、调用 model、收集并发 tool futures、判断 follow-up/compaction/stop。", "codex-rs/core/src/session/turn.rs:run_turn", ["C-002", "C-017", "C-019"], path="codex-rs/core/src/session/turn.rs", line=224, end=417, symbol="run_turn"),
    evidence("S-004", "S", "请求 prompt 由 input、当前可见 tool specs、base instructions 与 output schema 构造，turn 内再构建工具。", "codex-rs/core/src/session/turn.rs:build_prompt", ["C-003", "C-007"], path="codex-rs/core/src/session/turn.rs", line=1084, end=1350, symbol="build_prompt"),
    evidence("S-005", "S", "ContextManager 维护 oldest-first history、token info、reference context 和 world-state baseline，并只记录 API messages。", "codex-rs/core/src/context_manager/history.rs:ContextManager", ["C-003", "C-004"], path="codex-rs/core/src/context_manager/history.rs", line=36, end=204, symbol="ContextManager"),
    evidence("S-006", "S", "WorldState 按类型保留 sections，并生成 RFC 7386 snapshot/diff。", "codex-rs/core/src/context/world_state/mod.rs:WorldState", ["C-004"], path="codex-rs/core/src/context/world_state/mod.rs", line=206, end=328, symbol="WorldState"),
    evidence("S-007", "S", "compaction selector 处理 token budget、remote v2/v1、local fallback、pre-turn 与 mid-turn 触发。", "codex-rs/core/src/session/turn.rs:compact", ["C-005"], path="codex-rs/core/src/session/turn.rs", line=798, end=1029, symbol="compact"),
    evidence("S-008", "S", "ModelClientSession 持有 turn 内稳定状态、WebSocket fallback 和 x-codex-turn-state。", "codex-rs/core/src/client.rs:ModelClientSession", ["C-006", "C-017"], path="codex-rs/core/src/client.rs", line=194, end=285, symbol="ModelClientSession"),
    evidence("S-009", "S", "ToolSpecPlan 分离 registry 与 exposure，并从 shell、MCP、collaboration、extensions、dynamic、hosted tools 合并能力。", "codex-rs/core/src/tools/spec_plan.rs:ToolSpecPlan", ["C-007"], path="codex-rs/core/src/tools/spec_plan.rs", line=158, end=594, symbol="ToolSpecPlan"),
    evidence("S-010", "S", "ToolRouter 解析 function、custom 与 namespace calls，绑定精确 StepContext 后交给 registry。", "codex-rs/core/src/tools/router.rs:ToolRouter", ["C-008", "C-019", "C-020"], path="codex-rs/core/src/tools/router.rs", line=35, end=263, symbol="ToolRouter"),
    evidence("S-011", "S", "ToolRegistry 拒绝重复注册，执行 telemetry/pre-tool hooks，并把 unsupported tool 转成 model-facing error。", "codex-rs/core/src/tools/registry.rs:dispatch", ["C-008", "C-020"], path="codex-rs/core/src/tools/registry.rs", line=322, end=539, symbol="dispatch"),
    evidence("S-012", "S", "ExecPolicy 将命令拆分成 segments，综合规则、fallback 与 approval mode 决定 forbid/prompt/allow。", "codex-rs/core/src/exec_policy.rs:ExecPolicy", ["C-009"], path="codex-rs/core/src/exec_policy.rs", line=169, end=393, symbol="ExecPolicy"),
    evidence("S-013", "S", "Sandboxing helper 维护 session approval cache，并按 key 复用 ApprovedForSession。", "codex-rs/core/src/tools/sandboxing.rs", ["C-009"], path="codex-rs/core/src/tools/sandboxing.rs", line=41, end=118),
    evidence("S-014", "S", "SandboxManager 将 permission profile 转为 runtime permissions，并把命令变换到 platform sandbox executor。", "codex-rs/core/src/exec.rs:SandboxManager", ["C-009", "C-010"], path="codex-rs/core/src/exec.rs", line=117, end=413, symbol="SandboxManager"),
    evidence("S-015", "S", "配置给出 multi-agent V1/V2 feature gate、默认并发 6/4、max_depth=1 与共享 workspace 指令。", "codex-rs/core/src/config/mod.rs:MultiAgentConfig", ["C-012", "C-013", "C-022"], path="codex-rs/core/src/config/mod.rs", line=203, end=269, symbol="MultiAgentConfig"),
    evidence("S-016", "S", "CodexDelegate 创建具有独立 channels/session/context/history 的 child，并继承有效 policy、cwd、MCP 与 tools。", "codex-rs/core/src/codex_delegate.rs:spawn", ["C-012", "C-022"], path="codex-rs/core/src/codex_delegate.rs", line=70, end=258, symbol="CodexDelegate::spawn"),
    evidence("S-017", "S", "spawn control 可完整 fork 历史或要求 child 重建截断上下文。", "codex-rs/core/src/agent/control/spawn.rs", ["C-012"], path="codex-rs/core/src/agent/control/spawn.rs", line=45, end=78),
    evidence("S-018", "S", "ThreadStore trait 与 LiveThread 实现 create/resume/append/persist/flush，并在 resume 时加载历史。", "codex-rs/thread-store/src/store.rs and live_thread.rs", ["C-011", "C-021"], path="codex-rs/thread-store/src/live_thread.rs", line=91, end=216, symbol="LiveThread"),
    evidence("S-019", "S", "rollout recorder 写入 rollout-*.jsonl，后台 writer 在 I/O error 时保留 pending suffix。", "codex-rs/rollout/src/recorder.rs", ["C-011", "C-021"], path="codex-rs/rollout/src/recorder.rs", line=1511, end=1779),
    evidence("S-020", "S", "memories Phase 1 领取并提取 rollout，Phase 2 在锁与租约下启动 consolidation agent；feature 默认 false。", "codex-rs/core/src/memories", ["C-014"], path="codex-rs/memories/write/src/start.rs", line=18, end=78),
    evidence("S-021", "S", "turn span 和 codex.tool_call log 记录 conversation/turn/tool/call/timing/token 等字段。", "codex-rs/core/src/tasks/mod.rs and tools/parallel.rs", ["C-016"], path="codex-rs/core/src/tasks/mod.rs", line=384, end=400),
    evidence("S-022", "S", "Task abort 使用 cancellation token；turn completion 前 flush rollout，失败时产生 warning/retry。", "codex-rs/core/src/tasks/mod.rs:Task", ["C-017"], path="codex-rs/core/src/tasks/mod.rs", line=313, end=430, symbol="Task"),
    evidence("S-023", "S", "app-server 将 processor 与 outbound writer 放在不同 loop，并通过有界队列表达背压。", "codex-rs/app-server/src/lib.rs", ["C-015"], path="codex-rs/app-server/src/lib.rs", line=150, end=156),
    evidence("S-024", "S", "ProviderInfo 定义 base URL、auth、wire transport 与有界 request/stream retry；custom provider 可接入 Responses。", "codex-rs/model-provider-info/src/lib.rs:ModelProviderInfo", ["C-006", "C-018"], path="codex-rs/model-provider-info/src/lib.rs", line=90, end=363, symbol="ModelProviderInfo"),
    evidence("S-025", "S", "ToolCallRuntime 对 parallel-capable tool 使用读锁，对 exclusive tool 使用写锁，取消时 abort/wait。", "codex-rs/core/src/tools/parallel.rs:ToolCallRuntime", ["C-008", "C-023"], path="codex-rs/core/src/tools/parallel.rs", line=42, end=202, symbol="ToolCallRuntime"),
    evidence("S-026", "S", "MCP 与 dynamic handlers 生成运行时 specs；dynamic tool call 等待 host response，MCP output 会截断。", "codex-rs/core/src/tools/handlers", ["C-007"], path="codex-rs/core/src/tools/handlers/dynamic.rs", line=32, end=240),
    evidence("S-028", "S", "shell 与 unified exec 在创建普通 exec approval requirement 前调用 intercept_apply_patch；匹配后由 ApplyPatchRuntime 使用 patch safety、文件路径 approval keys、session cache 与 sandboxable runtime 执行。", "codex-rs/core/src/tools/handlers/shell.rs:intercept_apply_patch", ["C-024"], path="codex-rs/core/src/tools/handlers/shell.rs", line=142, end=177, symbol="intercept_apply_patch", notes="Dedicated implementation continues in tools/handlers/apply_patch.rs:546-648 and tools/runtimes/apply_patch.rs:129-235."),
    evidence("R-001", "R", "GitHub release 官方 musl 二进制报告 codex-cli 0.144.5。", "command: codex --version", ["C-001"], command="/tmp/codex-x86_64-unknown-linux-musl --version", conditions={"artifact": "official GitHub release"}),
    evidence("R-002", "R", "真实 SiFlow 最小运行在 turn.started 后因 Unexpected message role 返回 HTTP 400，未产生 tool call。", "traces/raw/real-siflow-minimal.jsonl", ["C-018"], path="traces/raw/real-siflow-minimal.jsonl", scenario="R-SCENARIO-001", conditions={"multi_agent": False, "wire_api": "responses"}),
    evidence("R-003", "R", "真实 SiFlow 启用 V1 时拒绝 type=namespace 的 tool schema；原始长错误已删除，仅保留归一化摘要。", "traces/normalized/R-002-siflow-namespace.normalized.jsonl", ["C-018"], path="traces/normalized/R-002-siflow-namespace.normalized.jsonl", scenario="R-SCENARIO-002", conditions={"multi_agent": True, "wire_api": "responses"}),
    evidence("X-001", "X", "确定性 SSE fixture 返回单个 assistant message；Codex 发出 turn.completed。", "traces/normalized/X-001-text-stop.normalized.jsonl", ["C-002"], path="traces/normalized/X-001-text-stop.normalized.jsonl", scenario="X-SCENARIO-001"),
    evidence("X-002", "X", "read_tool 场景的第二次 request 含 function_call 与 function_call_output，最后返回 HXA-1445。", "traces/raw/read-tool-requests.jsonl", ["C-002", "C-019"], path="traces/raw/read-tool-requests.jsonl", scenario="X-SCENARIO-002"),
    evidence("X-003", "X", "不存在的 tool 产生 unsupported call error，但 tool output 回流后 turn 正常完成。", "traces/normalized/X-003-unknown-tool.normalized.jsonl", ["C-020"], path="traces/normalized/X-003-unknown-tool.normalized.jsonl", scenario="X-SCENARIO-003"),
    evidence("X-004", "X", "never policy 拒绝 require_escalated，fixture 收到结果后返回 DENIAL_REPORTED。", "traces/normalized/X-004-denied-escalation.normalized.jsonl", ["C-009", "C-020"], path="traces/normalized/X-004-denied-escalation.normalized.jsonl", scenario="X-SCENARIO-004"),
    evidence("X-005", "X", "V1 spawn_agent 产生独立 child thread；三次 provider request 中 child request 的 digest 与 tool exposure 不同。", "traces/raw/subagent-spawn-requests.jsonl", ["C-012", "C-013", "C-022"], path="traces/raw/subagent-spawn-requests.jsonl", scenario="X-SCENARIO-005"),
    evidence("X-006", "X", "两个进程中的 persisted turn/resume 共享 thread id；第二次 request input_count=5 并包含 assistant history。", "traces/raw/resume-requests.jsonl", ["C-011", "C-021"], path="traces/raw/resume-requests.jsonl", scenario="X-SCENARIO-006"),
    evidence("X-007", "X", "拒绝场景前后 FACTS.txt SHA-256 相同，目录中没有 forbidden-marker。", "traces/normalized/X-007-side-effect-check.normalized.jsonl", ["C-009"], path="traces/normalized/X-007-side-effect-check.normalized.jsonl", scenario="X-SCENARIO-004"),
    evidence("I-001", "I", "把 history 与 world-state diff 分离可降低重复上下文，但同步正确性成为独立状态机问题；这是分析者综合，不是作者意图声明。", "analyst synthesis from S-005/S-006", ["C-004"], conditions={"epistemic_status": "analyst_synthesis"}, confidence="medium"),
    evidence("I-002", "I", "Codex 的主要安全边界是 policy decision 与 platform sandbox 的组合，而非任一单层；这是分析者综合。", "analyst synthesis from D-002/S-012/S-014", ["C-010"], conditions={"epistemic_status": "analyst_synthesis"}, confidence="medium"),
]


def node(node_id: str, kind: str, name: str, summary: str, evidence_ids: list[str], layer: str, *, status: str = "static_only", lifecycle: str = "runtime", trust: str = "process", conditions: dict | None = None, refs: list[dict] | None = None) -> dict:
    return {"id": node_id, "type": kind, "name": name, "summary": summary, "attributes": {"layer": layer, "lifecycle": lifecycle, "trust_zone": trust}, "conditions": conditions or {}, "evidence_ids": evidence_ids, "confidence": "high" if status != "inferred" else "medium", "status": status, "source_refs": refs or []}


NODES = [
    node("N-CLI", "Interface", "CLI/TUI/exec", "Human and automation surfaces.", ["S-001", "R-001"], "interface", status="runtime_verified"),
    node("N-AppServer", "Interface", "App Server", "Bidirectional JSON-RPC thread API.", ["D-003", "S-023"], "interface"),
    node("N-MCPServer", "Interface", "MCP Server", "Codex exposed as an MCP server surface.", ["S-001"], "interface"),
    node("N-ThreadManager", "Session", "Thread Manager", "Creates, resumes, forks and owns sessions.", ["D-003", "S-018"], "orchestration"),
    node("N-RegularTask", "AgentLoop", "Regular Task", "Starts a turn and drains queued user input.", ["S-002", "X-001"], "orchestration", status="experimental_verified"),
    node("N-TurnLoop", "AgentLoop", "Turn Loop", "Model/tool iteration and stop decisions.", ["S-003", "X-002"], "orchestration", status="experimental_verified"),
    node("N-Context", "ContextBuilder", "Context Manager", "Model-visible history and token accounting.", ["S-005", "X-002"], "context-capability", status="experimental_verified", lifecycle="carry-forward"),
    node("N-WorldState", "ContextTransformer", "World State", "Typed snapshots and diffs for dynamic state.", ["S-006"], "context-capability", lifecycle="per-turn"),
    node("N-Compactor", "Compactor", "Compactor", "Remote/local summary and history replacement.", ["S-007"], "context-capability", lifecycle="threshold/overflow/manual"),
    node("N-ModelSession", "ModelAdapter", "Model Client Session", "Stable transport and retry state.", ["S-008", "S-024"], "infrastructure"),
    node("N-Responses", "ModelCall", "Responses API", "Streaming model boundary.", ["S-024", "X-001"], "infrastructure", status="experimental_verified", trust="external"),
    node("N-SpecPlan", "ToolRegistry", "Tool Spec Plan", "Registry plus model-visible exposure.", ["S-009", "X-005"], "context-capability", status="experimental_verified"),
    node("N-ToolRouter", "Router", "Tool Router", "Parses and binds response tool calls.", ["S-010", "X-002"], "orchestration", status="experimental_verified"),
    node("N-ToolRuntime", "Tool", "Tool Runtime", "Parallel/exclusive handler execution.", ["S-025", "X-002"], "execution", status="experimental_verified"),
    node("N-MCP", "MCPServer", "MCP/Extensions", "Externally supplied capability surface.", ["S-026"], "extension", trust="external"),
    node("N-Hooks", "Hook", "Hooks", "Pre-tool policy/rewrite and lifecycle hooks.", ["S-011"], "extension"),
    node("N-ExecPolicy", "PolicyRule", "Exec Policy", "Rule and approval-mode decision.", ["S-012", "X-004"], "governance", status="experimental_verified", trust="policy"),
    node("N-Approval", "PermissionGate", "Approval Cache", "Per-call and per-session approval state.", ["S-013", "X-004"], "governance", status="experimental_verified", trust="policy"),
    node("N-Sandbox", "Sandbox", "Sandbox Manager", "Platform-specific permission transform.", ["D-002", "S-014"], "governance", trust="sandbox"),
    node("N-ExecBackend", "ExecutionBackend", "Execution Backend", "Process/filesystem/network side effects.", ["S-014", "X-007"], "execution", status="experimental_verified", trust="sandbox"),
    node("N-Workspace", "Workspace", "Workspace", "Shared working directory and files.", ["S-015", "X-007"], "state", status="experimental_verified", trust="workspace"),
    node("N-LiveThread", "SessionStore", "Live Thread", "Storage-neutral active persistence boundary.", ["D-004", "S-018", "X-006"], "state", status="experimental_verified", lifecycle="durable"),
    node("N-Rollout", "Checkpoint", "Rollout JSONL", "Append-oriented durable event history.", ["S-019", "X-006"], "state", status="experimental_verified", lifecycle="durable"),
    node("N-Memory", "MemoryStore", "Two-phase Memory", "Experimental extraction and consolidation.", ["D-005", "S-020"], "state", lifecycle="durable", conditions={"feature": "memories", "default": False}),
    node("N-AgentControl", "Planner", "Agent Control", "Shared governance for one root agent tree.", ["S-015", "S-016", "X-005"], "orchestration", status="experimental_verified", conditions={"feature": "multi_agent"}),
    node("N-Subagent", "Subagent", "Child Session", "Independent child context/history with inherited policy.", ["S-016", "X-005"], "orchestration", status="experimental_verified", conditions={"feature": "multi_agent"}),
    node("N-Telemetry", "TelemetrySink", "Events + OTel", "Product events, logs, traces and metrics.", ["D-006", "S-021"], "observability"),
    node("N-Recovery", "RecoveryPolicy", "Recovery", "Bounded retry, cancellation and flush behavior.", ["S-008", "S-022"], "orchestration"),
    node("N-Exit", "ExitCondition", "Turn Complete", "No follow-up, queued input or cancellation.", ["S-002", "S-003", "X-001"], "orchestration", status="experimental_verified"),
]


def edge(edge_id: str, source: str, target: str, kind: str, label: str, evidence_ids: list[str], *, status: str = "static_only", conditions: dict | None = None) -> dict:
    return {"id": edge_id, "source": source, "target": target, "type": kind, "label": label, "conditions": conditions or {}, "evidence_ids": evidence_ids, "confidence": "high", "status": status, "source_refs": []}


EDGES = [
    edge("E-CLI-Thread", "N-CLI", "N-ThreadManager", "enters", "start/resume", ["S-001", "X-006"], status="experimental_verified"),
    edge("E-App-Thread", "N-AppServer", "N-ThreadManager", "enters", "JSON-RPC", ["D-003", "S-023"]),
    edge("E-MCP-Thread", "N-MCPServer", "N-ThreadManager", "enters", "server op", ["S-001"]),
    edge("E-Thread-Task", "N-ThreadManager", "N-RegularTask", "calls", "start turn", ["S-002", "X-001"], status="experimental_verified"),
    edge("E-Task-Loop", "N-RegularTask", "N-TurnLoop", "calls", "run_turn", ["S-002", "X-001"], status="experimental_verified"),
    edge("E-Loop-Context", "N-TurnLoop", "N-Context", "assembles", "history", ["S-003", "S-005", "X-002"], status="experimental_verified"),
    edge("E-World-Context", "N-WorldState", "N-Context", "injects", "snapshot/diff", ["S-006"]),
    edge("E-Context-Compact", "N-Context", "N-Compactor", "compacts", "over budget", ["S-007"]),
    edge("E-Compact-Context", "N-Compactor", "N-Context", "returns", "replacement", ["S-007"]),
    edge("E-Context-Model", "N-Context", "N-ModelSession", "calls", "prompt", ["S-004", "X-002"], status="experimental_verified"),
    edge("E-Spec-Model", "N-SpecPlan", "N-ModelSession", "injects", "visible specs", ["S-004", "S-009", "X-005"], status="experimental_verified"),
    edge("E-Session-Responses", "N-ModelSession", "N-Responses", "calls", "stream", ["S-008", "S-024", "X-001"], status="experimental_verified"),
    edge("E-Responses-Router", "N-Responses", "N-ToolRouter", "proposes", "tool call", ["S-010", "X-002"], status="experimental_verified"),
    edge("E-Router-Runtime", "N-ToolRouter", "N-ToolRuntime", "executes", "dispatch", ["S-010", "S-025", "X-002"], status="experimental_verified"),
    edge("E-MCP-Spec", "N-MCP", "N-SpecPlan", "registers", "specs", ["S-026"]),
    edge("E-Spec-Router", "N-SpecPlan", "N-ToolRouter", "registers", "handlers", ["S-009", "S-010"]),
    edge("E-Hooks-Runtime", "N-Hooks", "N-ToolRuntime", "triggers", "pre/post", ["S-011"]),
    edge("E-Runtime-Policy", "N-ToolRuntime", "N-ExecPolicy", "authorizes", "command", ["S-012", "X-004"], status="experimental_verified"),
    edge("E-Policy-Approval", "N-ExecPolicy", "N-Approval", "routes_if", "ask/cache", ["S-012", "S-013"]),
    edge("E-Policy-Deny", "N-ExecPolicy", "N-ToolRuntime", "denies", "model-facing error", ["S-012", "X-004"], status="experimental_verified"),
    edge("E-Approval-Sandbox", "N-Approval", "N-Sandbox", "authorizes", "approved", ["S-013", "S-014"]),
    edge("E-Sandbox-Exec", "N-Sandbox", "N-ExecBackend", "executes", "transform", ["D-002", "S-014"]),
    edge("E-Exec-Workspace", "N-ExecBackend", "N-Workspace", "writes", "side effect", ["S-014", "X-007"], status="experimental_verified"),
    edge("E-Runtime-Context", "N-ToolRuntime", "N-Context", "appends_to_context", "tool output", ["S-003", "X-002"], status="experimental_verified"),
    edge("E-Loop-Live", "N-TurnLoop", "N-LiveThread", "persists", "items", ["S-018", "X-006"], status="experimental_verified"),
    edge("E-Live-Rollout", "N-LiveThread", "N-Rollout", "persists", "append/flush", ["S-019", "X-006"], status="experimental_verified"),
    edge("E-Rollout-Live", "N-Rollout", "N-LiveThread", "restores", "resume", ["S-018", "X-006"], status="experimental_verified"),
    edge("E-Rollout-Memory", "N-Rollout", "N-Memory", "reads", "phase 1", ["D-005", "S-020"], conditions={"feature": "memories"}),
    edge("E-Agent-Child", "N-AgentControl", "N-Subagent", "delegates", "spawn", ["S-016", "X-005"], status="experimental_verified", conditions={"feature": "multi_agent"}),
    edge("E-Child-Workspace", "N-Subagent", "N-Workspace", "shares_workspace_with", "same cwd", ["S-015", "S-016"]),
    edge("E-Child-Context", "N-Subagent", "N-Context", "isolates_context_from", "own history", ["S-016", "X-005"], status="experimental_verified"),
    edge("E-Child-Loop", "N-Subagent", "N-TurnLoop", "calls", "child turn", ["S-016", "X-005"], status="experimental_verified"),
    edge("E-Task-Telemetry", "N-RegularTask", "N-Telemetry", "emits_trace", "turn span", ["S-021"]),
    edge("E-Runtime-Telemetry", "N-ToolRuntime", "N-Telemetry", "emits_trace", "tool log", ["S-021"]),
    edge("E-Model-Recovery", "N-ModelSession", "N-Recovery", "retries", "bounded", ["S-008"]),
    edge("E-Recovery-Loop", "N-Recovery", "N-TurnLoop", "returns", "continue/fail", ["S-022"]),
    edge("E-Loop-Exit", "N-TurnLoop", "N-Exit", "exits_to", "no follow-up", ["S-003", "X-001"], status="experimental_verified"),
]


MODULE_FILES = {
    "interfaces": ["codex-rs/cli/src/main.rs", "codex-rs/app-server/src/lib.rs"],
    "core_loop": ["codex-rs/core/src/tasks/regular.rs", "codex-rs/core/src/session/turn.rs"],
    "context_assembly": ["codex-rs/core/src/context_manager/history.rs", "codex-rs/core/src/context/world_state/mod.rs", "codex-rs/core/src/session/world_state.rs"],
    "compaction": ["codex-rs/core/src/session/turn.rs", "codex-rs/core/src/compact_remote_v2.rs"],
    "model_abstraction": ["codex-rs/core/src/client.rs", "codex-rs/model-provider-info/src/lib.rs"],
    "tools_extensions": ["codex-rs/core/src/tools/spec_plan.rs", "codex-rs/core/src/tools/router.rs", "codex-rs/core/src/tools/registry.rs", "codex-rs/core/src/tools/handlers/apply_patch.rs"],
    "permissions_safety": ["codex-rs/core/src/exec_policy.rs", "codex-rs/core/src/tools/sandboxing.rs", "codex-rs/core/src/tools/handlers/shell.rs"],
    "sandbox_execution": ["codex-rs/core/src/exec.rs", "codex-rs/core/README.md"],
    "workspace": ["codex-rs/core/src/session/world_state.rs", "codex-rs/core/src/config/mod.rs"],
    "sessions_persistence": ["codex-rs/thread-store/src/store.rs", "codex-rs/thread-store/src/live_thread.rs", "codex-rs/rollout/src/recorder.rs"],
    "subagents": ["codex-rs/core/src/codex_delegate.rs", "codex-rs/core/src/agent/control/spawn.rs"],
    "orchestration": ["codex-rs/core/src/session/turn.rs", "codex-rs/core/src/agent/control.rs"],
    "observability": ["codex-rs/otel/README.md", "codex-rs/core/src/tasks/mod.rs"],
    "recovery": ["codex-rs/core/src/tasks/mod.rs", "codex-rs/core/src/client.rs"],
}


PARTIAL = {"compaction", "model_abstraction", "sandbox_execution", "workspace", "observability", "recovery"}
SCENARIOS_BY_MODULE = {
    "interfaces": ["X-SCENARIO-001", "X-SCENARIO-006"],
    "core_loop": ["X-SCENARIO-001", "X-SCENARIO-002", "X-SCENARIO-003"],
    "context_assembly": ["X-SCENARIO-002", "X-SCENARIO-006"],
    "compaction": [],
    "model_abstraction": ["R-SCENARIO-001", "R-SCENARIO-002", "X-SCENARIO-001"],
    "tools_extensions": ["X-SCENARIO-002", "X-SCENARIO-003", "X-SCENARIO-005"],
    "permissions_safety": ["X-SCENARIO-004"],
    "sandbox_execution": ["X-SCENARIO-004"],
    "workspace": ["X-SCENARIO-004", "X-SCENARIO-005"],
    "sessions_persistence": ["X-SCENARIO-006"],
    "subagents": ["X-SCENARIO-005"],
    "orchestration": ["X-SCENARIO-002", "X-SCENARIO-005"],
    "observability": ["X-SCENARIO-001", "X-SCENARIO-002"],
    "recovery": ["R-SCENARIO-001", "R-SCENARIO-002", "X-SCENARIO-003", "X-SCENARIO-004", "X-SCENARIO-006"],
}


UNRESOLVED = {
    "compaction": ["未用 oversized tool output 或 token fixture 动态触发 pre-turn/mid-turn/remote compaction。"],
    "model_abstraction": ["SiFlow 需要 role/namespace translation adapter 才能执行真实 agent turn；本报告没有修改 target code。"],
    "sandbox_execution": ["宿主没有 Rust toolchain，且当前执行环境无法直接复现所有 platform sandbox backend。"],
    "workspace": ["未验证 worktree、remote environment 与并发 child 文件冲突。"],
    "observability": ["OTel exporter 关闭，未检查 collector 端 span 拓扑。"],
    "recovery": ["未注入 stream idle timeout、tool process crash、rollout corruption 与 SIGINT。"],
}


SCENARIOS = {
    "schema_version": "1.0",
    "safety_gate": {
        "authorization": "User explicitly authorized the supplied SiFlow endpoint for agent tests.",
        "credentials": "Credentials were read from existing Codex configuration and never persisted in the bundle.",
        "target_mutation": "The pinned source checkout was read-only and unchanged.",
        "workspace": "/tmp/codex-analysis-workspace",
        "home": "/tmp/codex-analysis-home",
        "network": "Only the user-authorized SiFlow endpoint; deterministic scenarios used 127.0.0.1.",
    },
    "scenarios": [
        {"id": "R-SCENARIO-001", "title": "SiFlow minimal Responses compatibility", "mode": "real", "status": "failed_as_expected", "result": "HTTP 400: Unexpected message role", "claims_tested": ["C-018"], "trace": "traces/raw/real-siflow-minimal.jsonl"},
        {"id": "R-SCENARIO-002", "title": "SiFlow namespace tool compatibility", "mode": "real", "status": "failed_as_expected", "result": "HTTP 400: namespace tool schema unsupported", "claims_tested": ["C-018"], "trace": "traces/normalized/R-002-siflow-namespace.normalized.jsonl"},
        {"id": "X-SCENARIO-001", "title": "Text-only stop", "mode": "scripted-responses", "status": "passed", "result": "SCRIPTED_OK and turn.completed", "claims_tested": ["C-002"], "trace": "traces/normalized/X-001-text-stop.normalized.jsonl"},
        {"id": "X-SCENARIO-002", "title": "Read tool round trip", "mode": "scripted-responses", "status": "passed", "result": "second request contained function_call_output; HXA-1445", "claims_tested": ["C-002", "C-019"], "trace": "traces/raw/read-tool-requests.jsonl"},
        {"id": "X-SCENARIO-003", "title": "Unknown tool recovery", "mode": "scripted-responses", "status": "passed", "result": "unsupported call returned to model; turn completed", "claims_tested": ["C-020"], "trace": "traces/normalized/X-003-unknown-tool.normalized.jsonl"},
        {"id": "X-SCENARIO-004", "title": "Denied escalation and side-effect check", "mode": "scripted-responses", "status": "passed", "result": "never policy denied before process; hash unchanged", "claims_tested": ["C-009", "C-020"], "trace": "traces/normalized/X-004-denied-escalation.normalized.jsonl"},
        {"id": "X-SCENARIO-005", "title": "V1 subagent spawn", "mode": "scripted-responses", "status": "passed", "result": "child thread created; independent request; depth-limited tool exposure", "claims_tested": ["C-012", "C-013", "C-022"], "trace": "traces/raw/subagent-spawn-requests.jsonl"},
        {"id": "X-SCENARIO-006", "title": "Persist and resume", "mode": "scripted-responses", "status": "passed", "result": "same thread id; restored assistant history; rollout JSONL present", "claims_tested": ["C-011", "C-021"], "trace": "traces/raw/resume-requests.jsonl"},
    ],
}


REPORTS: dict[str, str] = {}

REPORTS["00-design-space-and-running-example.md"] = """# 设计空间与 Running Example

![Codex design space](../diagrams/generated/codex-design-space.png)

> 图 8（gpt-image-2 读者插图）：四行把可观察约束、恢复出的机制和分析者综合的 tradeoff 分开；右列不是作者声明。Evidence: `D-002`, `D-004`, `D-007`, `S-005`, `S-009`, `S-012`, `S-014`, `S-018`, `S-025`, `X-002`, `X-004`, `X-006`。

<!-- EXPLANATION:design-space-figure -->
## 怎么读图 8

每一行都从左向右读：`Constraint` 是 harness 必须面对的问题，`Recovered mechanism` 是在 v0.144.5 源码中找到的当前实现，`Analyst synthesis` 是由实现推导出的工程代价。最后一列带 `INFERENCE`，是为了明确它不是 OpenAI 作者声明。

例如第一行不是说“rollout 一定会损坏”，而是说：既然跨进程 resume 依赖 `LiveThread + Rollout`，那么 flush 失败、尾部截断和 corruption 就成为必须测试的边界。第四行同理：`Exec Policy + Sandbox` 提供分层治理，但跨平台实现不同，所以不能用一次 Linux deny 实验推出所有平台都等价。[S: `S-012`–`S-014`, `S-018`, `S-019`] [X: `X-004`, `X-006`]

## 六个反复出现的设计问题

| 问题 | v0.144.5 的当前机制 | 可替代方案 | 部署约束、权衡与边界 | 证据与置信度 |
|---|---|---|---|---|
| 谁拥有耐久状态？ | `ThreadStore` 定义后端中立接口，`LiveThread` 负责活动 thread 的 append/flush，local backend 用 rollout JSONL 保存 canonical history。 | 只保存在 UI 进程内存，或为每轮建立数据库/文件系统事务 checkpoint。 | 跨进程 resume/fork 清晰，但 flush、尾部损坏和 workspace drift 成为 correctness 边界；本轮只验证正常尾部写入。 | `S-018`, `S-019`, `X-006`；高 |
| 每轮模型看见什么？ | `ContextManager` 保留 history，`WorldState` 维护 typed snapshot/diff，`StepContext` 冻结本次请求的 model、cwd、policy 与 tool exposure。 | 每轮从一个 canonical store 重建完整 prompt snapshot。 | 减少重复注入并保护并发请求配置，但 baseline、cache prefix 与动态状态同步更难推理；完整 source differential 未跑。 | `S-004`–`S-006`, `I-001`；中 |
| 能力何时可见？ | ToolSpecPlan 把 registered handler 与本轮 model-visible specs 分开，并按 provider、feature、agent depth、MCP/extension 状态选择 exposure。 | 所有已注册工具始终发送给模型。 | 动态适配能力强，但静态 registry、模型可见、实际 requested、获准执行是四个不同事实。 | `S-009`, `X-005`；高 |
| 副作用如何治理？ | 真正的进程 exec 先计算 rule/approval requirement，再经 permission profile 选择 platform sandbox；apply_patch 走专用 patch governance。 | 只做用户审批、只做 OS sandbox，或所有 action 统一 capability broker。 | 分层治理能区分“允许”与“可触达范围”，但平台/mode/tool handler 矩阵复杂；一次 Linux deny 不能覆盖 MCP、dynamic tool 或 patch 路径。 | `D-002`, `S-012`–`S-014`, `S-028`, `I-002`；中 |
| 多 agent 如何隔离？ | Child 拥有独立 thread/channel/context/history，继承 effective model/policy/cwd，并共享 AgentControl 与 workspace；V1/V2 分 gate。 | 单 context 角色切换，或每 child 独立 worktree/container/remote runtime。 | Root context 增长受控，但共享文件会竞争；本轮只运行 V1，V2 mailbox 与多 child 冲突仍是静态边界。 | `S-015`–`S-017`, `S-027`, `X-005`；中 |
| 失败后从哪恢复？ | Provider stream retry、tool/turn cancellation、rollout flush 和跨进程 thread resume 分别处理不同失败域。 | Fail-fast 整体重启，或统一事务 checkpoint/rollback。 | 局部恢复成本低且 session 可继续，但不存在覆盖 provider、tool、process、durable state 与 workspace 的单一回滚点。 | `S-008`, `S-022`, `X-006`；中 |

## Running example：一次确定性的 read tool turn

本报告用 `X-SCENARIO-002` 作为主线，因为它只要求 harness 机制，不依赖模型随机选择工具：本地 Responses fixture 首次强制返回 `exec_command(cat FACTS.txt)`；只有第二次请求包含同一 `call_id` 的 `function_call_output` 时，fixture 才返回 `HXA-1445`。

观测顺序是：请求 1（3 个 message items）→ function call → 只读执行 → tool output 进入 history → 请求 2（新增 function call/output）→ assistant final → turn complete。这个 trace 支持核心循环和 context feedback，但**不支持** compaction、MCP、write sandbox 或 subagent 等没有发生的路径。[X: `X-002`]

权限拒绝、subagent 与 resume 分别来自 `X-SCENARIO-004/005/006`，在后文作为独立支路附着，避免把多个实验拼成一次不存在的“全功能运行”。
"""

REPORTS["01-scope-and-method.md"] = """# 范围与方法

## 冻结快照

- Repository: `openai/codex`
- Annotated tag: `rust-v0.144.5`（tag object `efea0e66996d4e7f4f805f3df32a169d327f2f73`）
- Peeled commit: `87db9bc18ba5bc82c1cb4e4381b44f693ee35623`
- Source worktree: clean，分析后 `git status --short` 为空
- Official release binary: `codex-cli 0.144.5`
- Host: Linux；宿主没有 `rustc`/`cargo`/`just`

因此，本轮没有用另一个工具链重编译 target，也没有修改 Codex 源码。动态实验使用官方 release binary；确定性分支由本地 Responses SSE fixture 驱动。

## 证据规则

- `D`: 仓库文档/README/AGENTS 直接声明。
- `S`: 固定 commit 的源码结构与潜在路径。
- `R`: 官方 binary 对真实 SiFlow endpoint 的实际运行。
- `X`: 受控 scripted model、权限拒绝、文件哈希或 resume 实验。
- `I`: 基于多条证据的分析者综合，不代表作者动机。

运行观察只能证明“在命名配置下发生过”。静态存在也不能证明生产启用频率。完整记录见 [manifest](../manifest.json)、[coverage](../evidence/coverage.json)、[scenarios](../scenarios/catalog.json)。

## 配置与安全

测试使用独立 `/tmp/codex-analysis-home` 与 `/tmp/codex-analysis-workspace`，默认 `approval_policy=never`、`sandbox_mode=read-only`、memories/V1/V2 multi-agent 关闭；subagent 场景只临时启用 V1。真实网络只访问用户明确授权的 SiFlow endpoint；fixture 只监听 `127.0.0.1`。凭据没有写入 bundle，provider request 只保留 item type、role、tool name 与内容哈希。

<!-- EXPLANATION:method-terms -->
## 如何理解“验证过”

本文把“源码中存在”“本轮真的发生过”和“推断的设计代价”分开。`S` 证据能证明一条路径在固定 commit 中可见；`R/X` 能证明它至少在某个命名配置下发生；二者都不能证明生产使用频率。`partial` 也不是“模块只读了一半”，而是指静态机制已经恢复，但关键平台、feature flag 或失败路径没有动态覆盖。

因此，图上的 `OBSERVED` 只对应具体 scenario；`CONDITIONAL`、`EXPERIMENTAL`、`V1/V2` 或 `NOT TESTED` 都必须结合 manifest 中的 feature/configuration 阅读。

## 主要限制

没有 Rust toolchain，因此未运行仓库 `just test`；没有动态触发 compaction、MCP、OTel exporter、真实 sandbox backend、V2 multi-agent、memory consolidation、fork/corrupt rollout。真实 SiFlow 也无法完整接收 stock Codex 请求方言，详见运行实验。
"""

REPORTS["02-interfaces-lifecycle.md"] = """# 接口与生命周期

Codex 的接口层比“CLI 包一层 core”更丰富，但共享同一个 thread/session 概念。

`codex-rs/cli/src/main.rs` 的 `Subcommand` 将 `exec`、`mcp-server`、`app-server` 等模式显式分派；无 subcommand 时进入 TUI。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/cli/src/main.rs#L124) [S: `S-001`]

app-server 不是另一个 agent runtime。它把 thread start/resume/fork、turn start/interrupt 与通知映射成双向 JSON-RPC；processor 与 outbound writer 分离，避免慢客户端直接卡住处理 loop。[文档](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/app-server/README.md#L1) [源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/app-server/src/lib.rs#L150) [D: `D-003`] [S: `S-023`]

常规生命周期可压缩为：surface 创建/恢复 thread → session 接受 op → `RegularTask` 发出 `TurnStarted` → `run_turn` → flush rollout → `TurnComplete/TurnAborted` → session 仍可接受后续 turn。tool follow-up 发生在同一次 `run_turn` 的 sampling loop 内；如果存在排队或 steer 的新用户输入，`RegularTask` 还可以在同一外层 turn 里再执行一次 `run_turn`。是否是新 turn 应以 `TurnStarted/TurnComplete` 及 `turn_id` 为准，不能按模型请求次数判断。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tasks/regular.rs#L37) [S: `S-002`]

这一区分很关键：**turn、session、process 的终止条件不同**。一次 model/tool error 可以结束 turn，却不必销毁 thread；app-server 客户端断开也不能被简单等同于 durable thread 删除。

<!-- EXPLANATION:lifecycle-terms -->
## Thread、Session、Turn 的包含关系

先把它们看成三种不同时间尺度的对象：**thread 是可持久化的对话身份，session 是当前进程中运行该 thread 的实例，turn 是 session 正在处理的一次任务边界**。用运行时所有权表示是：

```text
Codex process
└─ ThreadManager                         0..N 个已加载 thread
   └─ thread_id = T                    可持久化的逻辑身份
      └─ CodexThread handle
         └─ Session S                  当前进程的 live runtime
            └─ active_turn = None | U  同一时刻最多 1 个
               └─ Turn U
                  ├─ model request 1
                  ├─ tool call / tool result
                  └─ model request 2 ... N
```

这是运行时关系，不是持久化文件的目录结构。`ThreadManager` 在内存中维护 `ThreadId -> Arc<CodexThread>` 映射；`CodexThread` 是向 interface 提供 submit/event/shutdown 的 handle，内部包装真正的 `Session`。对同一个 manager，如果某个 thread 已经在运行，resume 会返回现有 handle，而不是再建一个并发 session。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/thread_manager.rs#L182) [源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/thread_manager.rs#L1526)

### 1. Thread：“这是哪段对话”

Thread 是跨 turn、也可以跨进程的逻辑身份。它的核心是 `thread_id`、会话历史和 metadata，而不是某个常驻 Rust 对象。

- `start` 产生新 `thread_id` 和新历史。
- `resume` 使用原 `thread_id` 加载原历史；新进程会为它创建新的 live session。
- `fork` 复制选定的历史快照，但分配**新** `thread_id`，因此不是在原 thread 内新建一个 turn。
- local store 通常用 rollout JSONL 保存 canonical history，用 SQLite 保存可查询 metadata；`LiveThread` 隔离了 core 与具体存储后端。

Thread 记录“Codex 看过和产生过什么”，但它不拥有 workspace 的版本。恢复 thread 会恢复对话 history，不会自动把文件系统回滚到旧状态。[D: `D-004`] [S: `S-018`] [X: `X-006`]

### 2. Session：“谁正在运行这段对话”

Session 是一个 live、in-process 的运行对象。它带着同一个 `thread_id`，但还拥有只在当前运行期有意义的状态：event channel、model/provider 配置、permission profile、MCP/services、input queue、内存 conversation state，以及指向持久化后端的 `LiveThread` handle。

`Session` 源码明确声明“at most 1 running task at a time”，并以 `active_turn: Mutex<Option<ActiveTurn>>` 表示这个约束。它在生命周期中可以顺序处理多个 turn；开始替代任务时，旧任务会通过 cancellation 边界中止。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/session/session.rs#L25) [源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tasks/mod.rs#L325)

因此，一个 thread 在时间上可以对应多个先后出现的 session：进程 A 中的 `S1` 退出后，进程 B resume 同一 thread 会创建 `S2`。`S1` 与 `S2` 的内存地址、channel 和 service 对象不同，但它们共享同一个 `thread_id` 和已持久化历史。

### 3. Turn：“这一次任务什么时候结束”

Turn 是 `TurnStarted` 到 `TurnComplete` 或 `TurnAborted` 之间的调度单位。它有自己的 `turn_id`/`TurnContext` 和 mutable `TurnState`：本轮使用的 model、cwd/environment、approval/permission profile、dynamic tools、取消 token、token usage，以及正在等待的 approval、user input 或 dynamic-tool response。

**Turn 不等于一次模型 API 请求。** 一个 turn 可以是：

```text
TurnStarted(U1)
  -> model request #1
  -> model proposes exec_command
  -> permission + sandbox + tool execution
  -> tool result appended to history
  -> model request #2
  -> final assistant message
  -> flush rollout
TurnComplete(U1)
```

两次 model request、tool call 和 tool result 都属于同一个 `U1`。只有下一次发出新的 `TurnStarted(U2)` 才是新 turn。`TurnComplete/TurnAborted` 后，`active_turn` 被清空并再次 flush terminal event，session 回到 idle，thread 不因此消失。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tasks/mod.rs#L756) [S: `S-002`]

### 4. 一个跨进程的具体例子

| 时间点 | 发生的机制 | 保持不变的身份/状态 | 已变化的运行边界 | 不能推出什么 |
|---|---|---|---|---|
| 进程 A 启动 | ThreadManager 创建 thread `T`，并用 session `S1` 承载当前 live services、channels、policy 和 input queue。 | `thread_id=T` 作为新 durable identity。 | `S1` 是只属于进程 A 的 live object。 | 不能推出 thread 已经完成持久化；仍取决于 rollout append/flush。 |
| 用户提问 | `S1` 发出 `TurnStarted(U1)`；`run_turn` 内可出现两次 model request 和一次 tool call。 | `T`、`S1`、`U1` 在整个模型-工具闭环中保持同一。 | Request/StepContext 随 sampling step 变化。 | 不能按 API request 次数把一个 turn 错拆成多个 turn。 |
| `U1` 完成 | Terminal event 与 history 尝试 flush，`active_turn` 清空，`S1` 回到 idle。 | `T` 与 `S1` 仍可继续接受后续操作。 | `active_turn: U1 -> None`。 | Turn 完成不等于 session shutdown、thread 删除或 workspace checkpoint。 |
| 进程 A 退出 | `S1`、channels 和当前内存 services 消失；成功写入的 rollout 保留。 | `T` 与已 flush 的 durable history。 | Live session 不再存在。 | 不能推出所有尾部记录都已安全落盘；partial write/corruption 未注入。 |
| 进程 B resume | Store 按 `T` 加载 rollout，并建立新 live session `S2` 与新 services。 | 同一 `thread_id=T` 和可恢复 history。 | `S2` 的进程、内存对象、channels 与当前配置都是新的。 | Resume 不会复活 `S1`，也不会自动复用旧的临时 approval state。 |
| 用户再提问 | `S2` 发出新 `TurnStarted(U2)`，在恢复 history 上继续 sampling。 | Durable identity 仍是 `T`。 | Session 已是 `S2`，turn 已是 `U2`。 | 对话连续不代表 workspace 回滚或外部副作用被撤销。 |

本轮的跨进程实验已观察到：第二个进程 resume 后 `thread_id` 不变，provider input 包含首轮 assistant history。这直接验证了“thread 跨进程，session 不跨进程”的主路径。[X: `X-006`]

### 5. 失败会影响到哪一层

| 事件 | 通常结束或改变的边界 | 不能自动推出的结论 |
|---|---|---|
| 单次 provider stream 错误 | 当前 sampling/request，可能在 turn 内有界 retry | 不等于 thread 已删除 |
| tool error | 错误可以作为 tool output 回到当前 turn | 不一定结束 session |
| `TurnAborted` | 当前 turn | session 仍可接受新 turn |
| interface/websocket 断开 | 客户端连接 | 不等于 durable thread 被删除 |
| session/process shutdown | live runtime | flush 成功时 thread 仍可 resume |
| thread archive/delete | durable identity/history 的可见性或存在性 | 不会自动回滚 workspace |

所以最简短的记忆方式是：**Thread 回答“哪段对话”，Session 回答“哪个 live runtime 正在处理它”，Turn 回答“当前这次任务的边界在哪里”。** Interface 只决定这些操作通过 TUI、`exec`、app-server 还是 MCP server 进入 core。[D: `D-003`, `D-004`] [S: `S-002`, `S-018`]

动态验证覆盖了 `exec` 的 start 与 resume，但没有启动 TUI、app-server websocket 或 MCP server。因此“共享 core”是高置信静态结论，接口特有背压/序列化行为仍是局部覆盖。
"""

REPORTS["03-core-loop.md"] = """# 核心循环与编排

![Observed Codex turn](../diagrams/generated/codex-observed-turn.png)

> 图 2（gpt-image-2 读者插图）：严格对应 `X-SCENARIO-002` 的两次 Responses 请求；permission、compaction、subagent 等未发生路径没有混入主轴。Evidence: `S-002`, `S-003`, `S-010`, `S-025`, `X-002`。

<!-- EXPLANATION:turn-figure -->
## 图 2 的逐步阅读

1. `User request` 进入外层 `RegularTask`。外侧长括号表示这个 task 管理完整 turn。
2. 内层 `run_turn` 建立 `Request 1`，`Build prompt` 把 history、当前输入和可见工具规格组装成 Responses 请求。
3. 第一次 `Responses` 没有给最终答案，而是返回 `exec_command` function call。
4. harness 读取 `FACTS.txt`，把结果包装成 `function_call_output`。黑色回箭头表示它进入 history，不是直接显示给用户。
5. `Request 2` 使用 `Updated history` 再调用一次 Responses；此时请求里同时存在原 function call 和对应 output。
6. fixture 只有确认 output 存在后才返回 `HXA-1445`，所以第二次请求不是图示假设，而是实验门槛。
7. 没有新的 tool call、pending input 或 follow-up 后，turn 才进入 `Turn complete`。[X: `X-002`]

图里重复出现的 `Responses` 表示同一 model boundary 的两次调用，不是两个模型实例；`RegularTask` 与 `run_turn` 也不是并列的两个 agent loop，而是 turn 调度层与内部 sampling/tool loop。

## 两层循环

外层 `RegularTask` 管一个用户 turn：发开始事件、调用 `run_turn`、处理排队输入。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tasks/regular.rs#L37) 内层 `run_turn` 才是 agent loop：检查 compaction、刷新 world state/skills/hooks、构造 prompt、采样、dispatch tools、判断 follow-up，最后执行 stop hooks 和结束事件。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/session/turn.rs#L224) [S: `S-002`, `S-003`]

`OutputItemDone` 遇到 function/custom tool 时不会同步阻塞整个 stream parser，而是创建 tool future；Response completed 后再综合 `needs_follow_up`、pending input 与 compaction 条件。只读/parallel-capable handler 可共享读锁，exclusive handler 获取写锁。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tools/parallel.rs#L42) [S: `S-025`]

## 被实验验证的闭环

`X-SCENARIO-002` 的 provider 日志显示第一次 input types 是三条 `message`；第二次变成 `message ×3 + function_call + function_call_output`。fixture 只有看到 `call-read` output 才返回最终值，因此“tool result 确实进入下一轮模型上下文”不是根据最终文本猜测。[X: `X-002`]

`X-SCENARIO-003` 又验证错误分支：未知工具在 router/registry 处产生 unsupported error，但该错误作为 tool output 回到模型，turn 仍可结束。[X: `X-003`]

## 停止与恢复

正常停止条件是 response complete 且没有 tool follow-up/pending input；取消由 token 传播到 tool runtime，provider stream retry 有界。开始新 task 会 abort 旧 task；turn 完成前尝试 flush rollout。[S: `S-008`, `S-022`]

未覆盖：并行多 tool 的真实 interleaving、user interrupt、stream idle、stop hook 阻断和中途 compaction。因此图 2 只表达已经发生的 read-only 主线。
"""

REPORTS["04-context-memory-compaction.md"] = """# 上下文、记忆与压缩

![Codex context lifecycle](../diagrams/generated/codex-context-lifecycle.png)

> 图 3（gpt-image-2 读者插图）：区分 durable history、per-turn world-state diff、请求级 StepContext 与条件 compaction；所有来源必须先汇入 Context Manager 才到模型。Evidence: `D-007`, `S-004`–`S-007`, `S-020`, `X-002`, `X-006`。

<!-- EXPLANATION:context-figure -->
## 图 3 的节点和回路

| 图中节点 | 具体表示什么 |
|---|---|
| Base instructions | config override、persisted conversation metadata 或 model default 选出的基础指令 |
| History | 已规范化的模型可见 message/tool items；图中左右两个 History 图标是同一份 history 的两个视图 |
| World state diff | AGENTS、环境、subagents、apps/plugins 等相对 baseline 的 typed snapshot/diff |
| Visible tool specs | registry 中经过当前 provider、feature 和 exposure 规则筛出的本轮工具 schema |
| Context Manager | 负责 history 顺序、token 估计和 world-state baseline 的内存状态管理器 |
| `StepContext + Prompt` | 把本次请求固定的 cwd/model/policy/tools 与输入组合成 sampling 所需对象 |
| Tool runtime/output | 模型提出调用后，由 harness 执行并产生可追加到 history 的结果 |

右侧闭环要读成 `Responses API → Tool runtime → Tool output → History → Context Manager → next request`。下方 compaction 是另一条条件回路：达到 token/window 阈值后生成 replacement，再用 replacement 改写模型可见 history。`History replacement` 不是回滚 workspace，也不是删除 durable rollout；它改变的是后续模型请求的有效上下文。[S: `S-005`–`S-007`] [X: `X-002`]

`Long-term memory` 带 `EXPERIMENTAL`，表示它属于默认关闭的 memories feature；`WHEN NEEDED` 表示 compaction 是阈值触发，不是每轮固定执行。

## History 与 world state

`ContextManager` 按 oldest-first 保留模型可见 items、token info、reference item 和 world-state baseline；append 时只记录可进入 API 的 messages，并做 prompt normalization / modality filtering。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/context_manager/history.rs#L36) [S: `S-005`]

另一个状态面是 typed world state：AGENTS instructions、environment/subagents、apps、plugins、extension contributors 等可形成 snapshot 或 RFC 7386 风格 diff。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/context/world_state/mod.rs#L206) [S: `S-006`] 这让“当前环境变化”不必反复复制整个历史，但也意味着 history 与 baseline 的同步是 correctness 边界。[I: `I-001`]

每一轮的 `StepContext` 绑定当前 cwd、policy、model、tools 等请求级语义；tool invocation 保存精确 StepContext，避免并发工具读取到下一 turn 的配置。[S: `S-004`, `S-010`]

## Compaction 不是单一路径

源码至少有三种触发：turn 前 token 超限、tool follow-up 中超限、模型兼容性/窗口下调。选择器再区分 remote v2、remote v1 与 local compact；compaction 会安装替换后的 history 并重算 token usage。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/session/turn.rs#L798) [S: `S-007`]

| 顺序/分支 | 条件 | 实际机制 | Survivor 与边界 | 证据状态 |
|---|---|---|---|---|
| 1. Previous-model compatibility check | 新旧 model 的 compaction hash 不同，或切换到更小 context window 且当前 token 已超新限制。 | 在正常 sampling step 创建前，用 previous-model StepContext 发起 pre-turn compact；符合条件时可准备 current-model fallback context。 | 目标是先用旧模型语义总结旧 history；不是每次 model switch 都执行。 | `S-007`；static-only |
| 2. Pre-turn token check | 配置的 auto-compact budget 或 usable context window 已耗尽。 | 捕获当前 StepContext，以 `CompactionPhase::PreTurn` 运行 auto compact。 | 发生在普通 `run_turn` sampling 前；本轮未动态触发。 | `S-007`；static-only |
| 3. Backend selector | Compact 确实被触发后。 | 选择顺序是 TokenBudget feature → remote v2（feature on）→ remote v1 → local；这些是互斥实现分支，不是依次执行四次。 | Remote/local 的 request、fallback 与 replacement 语义不同；源码可见不等于生产配置启用。 | `S-007`；static-only |
| 4. Mid-turn threshold check | Tool follow-up 后 context 再次超过限制。 | 在同一 turn 内进入 mid-turn compaction，再决定是否继续 model sampling。 | 它附着在 tool loop，不创建新的 durable thread；是否形成新 request 取决于 compact 结果。 | `S-007`；static-only |
| 5. Install replacement | Compact 成功返回 replacement/history。 | 更新模型可见 history、world-state/reference baseline 和 token usage，再继续后续 request。 | Survivor 是 replacement 明确保留/重注入的信息；不是 workspace rollback，也不是删除原 rollout。 | `S-005`–`S-007`；static-only |

本轮没有构造足够长的 context，所以表中 compaction 全是源码确认的条件路径，不能据此声明默认任务中的出现频率或摘要信息损失大小。

## 长期 memory

`memories` 默认关闭。启用后 Phase 1 从 eligible rollout 提取结构化记忆并 redaction，Phase 2 在全局锁/租约下由专用 consolidation agent 合并到 durable files。[文档](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/memories/README.md#L1) [S: `S-020`] 它不是普通 turn 的同步 message append，也不等同于 session rollout。
"""

REPORTS["05-models-tools-extensions.md"] = """# 模型、工具与扩展

![Codex tool surface](../diagrams/generated/codex-tool-extension-surface.png)

> 图 4（gpt-image-2 读者插图）：左侧是注册来源，中间区分 registry 与 per-turn exposure，右侧才是 router/hook/handler/result。虚线能力在测试配置中未启用。Evidence: `S-004`, `S-009`–`S-011`, `S-024`–`S-026`, `X-002`, `X-003`, `X-005`。

<!-- EXPLANATION:tool-figure -->
## 图 4 的七段能力管线

这张图最容易误读成“工具注册后马上执行”。实际上必须按编号从左向右读：

1. **Capability sources**：`Built-ins` 是 Codex 自带工具；`MCP + Extensions` 是外部/插件贡献；`Dynamic + Multi-agent` 是 host 在运行时提供的函数和 feature-gated collaboration 工具。
2. **Tool registry**：保存 tool name 到 handler implementation 的映射。进入 registry 只说明 Codex 知道如何处理它，不代表模型现在看得见。
3. **Per-turn exposure**：`VISIBLE NOW` 是本次 request 的公开子集。provider capability、feature flag、agent depth 和 deferred/hidden 规则都会改变它。例如 root 有 `spawn_agent`，达到深度上限的 child 可以没有。
4. **Responses API**：模型收到 prompt 和暴露后的 tool schemas。图上自动生成的 `tool call only` 只是强调这条箭头承载 model-proposed tool call，不是说 Responses 只能返回工具调用；它也可以返回普通 assistant text。
5. **Router + Hooks**：router 解析 function/custom/namespace call，绑定准确的 `StepContext`；pre-tool hooks 可在 handler 前阻断或改写输入。
6. **Handler runtime**：真正执行 handler。`parallel read` 表示允许并行的工具共享读锁；`exclusive write` 表示有副作用或需独占的工具获取写锁。这个分类由 handler capability 决定，并非按工具名称猜测。
7. **Result to Context**：成功值或 model-facing error 被包装成 tool output，追加到 history；`next request` 才让模型看到它。

以报告的 read scenario 为例：`exec_command` 已在 registry，read-only 配置下也处于 exposure；模型提出 call 后 router 找到 handler，runtime 读取文件，结果回到 context，再发第二次 Responses 请求。`X-SCENARIO-003` 的未知工具则在 router/registry 查找阶段失败，但错误仍沿第 7 段返回模型。[S: `S-009`–`S-011`, `S-025`, `S-026`] [X: `X-002`, `X-003`, `X-005`]

## Model boundary

`ModelProviderInfo` 把 base URL、auth、wire transport、request/stream retry 与 remote compaction capability 收拢到 provider abstraction；`ModelClientSession` 保存 turn 内稳定 transport 状态和 WebSocket fallback。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/model-provider-info/src/lib.rs#L90) [S: `S-008`, `S-024`]

请求不是直接由 history 序列化：prompt 还包含 base instructions、output schema 和当前模型可见 tool specs。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/session/turn.rs#L1084) [S: `S-004`]

## Registry != exposure

`ToolSpecPlan` 同时生成 handler registry 与 model-visible specs；hidden/deferred tools 可以存在于 registry 却不出现在请求中。内置 shell、utility、collaboration、MCP runtime、extensions、dynamic 与 hosted tools 在当前 StepContext 下合成。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tools/spec_plan.rs#L158) [S: `S-009`]

这一点被 `X-SCENARIO-005` 直观证实：root 请求带 `multi_agent_v1` namespace；达到默认 child depth 后，child 请求不再带该 namespace。**扫描到 spawn handler 不等于每个 agent 都能 spawn。**

## Dispatch 与 extension points

`ToolRouter` 解析 function/custom/namespace call，构造绑定 StepContext 的 invocation；registry 查找 handler、发 telemetry、运行 pre-tool hooks，再 dispatch。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tools/router.rs#L112) [S: `S-010`, `S-011`]

MCP handler 根据 read-only annotation 决定并行能力并截断 output；dynamic tool 由 host 提供 schema，调用时等待 host response。[S: `S-026`] 这意味着 extension surface 同时跨越“模型可见 schema”和“谁真正执行副作用”两个边界，不能只画一张包依赖图。
"""

REPORTS["06-permissions-sandbox-workspace.md"] = """# 权限、Sandbox 与 Workspace

![Codex permission pipeline](../diagrams/generated/codex-permission-pipeline.png)

> 图 5（gpt-image-2 读者插图）：三分支明确区分 allow 直达 sandbox、ask 经 User Approval，以及 deny；红色拒绝支路是 `X-SCENARIO-004` 实际发生路径，sandbox backend 未执行。Evidence: `D-002`, `S-012`–`S-014`, `X-004`, `X-007`, `I-002`。

<!-- EXPLANATION:permission-figure -->
## 图 5 的三条分支

`Exec Policy` 不是 sandbox，它先回答“是否允许进入执行阶段”：

- `allow`：规则和 mode 已足以授权，不弹用户确认，直接进入 `Platform Sandbox`。
- `ask`：需要 `User Approval`；`Session cache` 只可能复用同一 session 中明确批准的 decision，然后同样进入 sandbox。
- `NEVER + escalation`：当前 policy 明确不允许询问提权，直接产生 `Tool error to model`；图中的 `OBSERVED` 只标记这条本轮实验路径。

两个 allow/ask 分支汇合后，`Filesystem profile` 和 `Network profile` 决定 sandbox 给 process 的实际能力，`Process` 才可能读取/写入 `Workspace`。所以“允许命令”不等于“无限制执行”，“用户批准”也不等于“关闭 sandbox”。[S: `S-012`–`S-014`] [X: `X-004`, `X-007`]

## 决策层

`ExecPolicy` 先把复合命令拆成 segments，综合 rules 与 fallback。只有每个 segment 都显式 allow 才能绕过额外 sandbox 决策；危险/未知命令在不同 approval mode 下会 forbid、prompt 或依赖 sandbox。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/exec_policy.rs#L169) [S: `S-012`]

`AskForApproval` 包含 `UnlessTrusted`、`OnRequest`、`Granular`、`Never`。session approval cache 只复用明确的 `ApprovedForSession`，并不是把一次批准变成全局 allow。[S: `S-013`]

## 执行层

通过 policy 后，`SandboxManager` 将 filesystem/network permission profile 转换为平台执行后端：Linux、macOS、Windows 有不同 transform 与 fallback。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/exec.rs#L117) [D: `D-002`] [S: `S-014`]

因此可审计边界是组合关系：policy 决定是否允许/询问/拒绝，sandbox 限制获准执行能触达什么。[I: `I-002`] 把二者任意一个画成“唯一安全层”都会丢失真实语义。

## 特殊治理路径：apply_patch 不是普通进程 exec

源码复核发现，shell 与 unified-exec handler 会先调用 `intercept_apply_patch`；若输入确实是 patch，它在创建普通 command 的 exec-policy requirement 之前转入 `ApplyPatchRuntime`。该 runtime 仍执行 patch safety assessment、按文件路径生成 approval keys、复用 session approval cache，并作为 sandboxable runtime 落地文件变更；它不是“跳过治理直接 spawn”。[S: `S-028`] [C: `C-024`]

| Tool 输入族 | 进入副作用前的主要路径 | 当前证据能证明什么 | 不能泛化的结论 |
|---|---|---|---|
| 普通 shell/exec command | Escalation mode guard → ExecPolicy decision → optional user approval/cache → permission profile/sandbox transform → process。 | `never + require_escalated` 在本实验中先于进程创建被拒绝。 | 不能据此覆盖 apply_patch、MCP、dynamic host tool 或 startup side effects。 |
| `apply_patch`（直接 tool 或 shell interception） | Patch parse/safety → per-path approval requirement/cache → ApplyPatchRuntime → sandboxed file mutation。 | 源码证明它有独立治理链，并非普通 command policy chain。 | 尚未运行三入口 differential scenario，不能宣称所有入口事件序列完全等价。 |
| MCP / dynamic / extension tool | 各自 handler 与 host callback，是否复用 exec/sandbox 取决于具体实现。 | Registry/router 和 handler source 已覆盖。 | “工具都经过同一个 ExecPolicy”不成立为已证明的 universal claim。 |

## 反例实验

fixture 请求 `touch forbidden-marker` 且显式 `sandbox_permissions=require_escalated`，配置为 `approval_policy=never`。router 返回 “you cannot ask for escalated permissions if the approval policy is Never”；随后 fixture 只有收到 tool output 才结束。运行前后 `FACTS.txt` SHA-256 都是 `277992...8ed`，目录仍只有 `FACTS.txt`。[X: `X-004`, `X-007`]

这证明 **never+require_escalated 的前置拒绝**，但没有证明 read-only sandbox 能阻挡所有绕行，也没有覆盖 MCP/dynamic tool 是否共享相同 exec gate。
"""

REPORTS["07-subagents-delegation.md"] = """# Subagent 与 Delegation

![Codex subagent topology](../diagrams/generated/codex-subagent-topology.png)

> 图 6（gpt-image-2 读者插图）：V1/V2 是两条条件路径；本轮只运行 V1。Child 拥有独立 context/history/thread，继承 policy/cwd，workspace 共享；默认 `max_depth=1` 使 child 不再暴露 spawn namespace。Evidence: `S-015`–`S-017`, `S-027`, `X-005`。

<!-- EXPLANATION:subagent-figure -->
## 图 6 中每个标签是什么意思

`AgentControl` 是一个 root agent tree 共享的控制面，负责 agent registry、并发/深度限制、消息发送、interrupt 和 child 生命周期。`Root Session` 与 `Child Session` 是两个独立 Codex session；`spawn_agent` 创建 child 后，child 拥有自己的 thread id、model-visible context 和 history，因此 child 的中间推理不会自动塞进 root history。[S: `S-015`, `S-016`]

图上方的 `model + policy + cwd` 表示 child 从父 turn 的 effective configuration 继承 model provider、approval policy、sandbox policy 和工作目录；这不是共享 context。下方两条 `shared files` 线表示 root/child 看见同一个 workspace，所以 context 隔离并不能避免文件竞争。`max depth 1` 是本版本默认配置：达到深度上限的 child 不再暴露 spawn namespace，并不表示 child 不能使用普通工具。[S: `S-015`–`S-017`] [X: `X-005`]

### `V2 mailbox` 的准确含义

它不是电子邮件服务，也不是一个额外 agent。它是 MultiAgent V2 的 **session-scoped inter-agent message queue**：child completion 或 agent-to-agent communication 先进入 parent 的 pending mailbox，再由 parent turn 决定何时吸收。

- turn 开始时处于 `CurrentTurn`，pending mail 可以加入当前 turn 的下一次 model request。
- parent 已输出用户可见 final 后，晚到 mail 通常留在队列，推迟到 `NextTurn`，避免悄悄延长已经显示完成的答案。
- 如果 parent 仍在 reasoning/commentary 阶段发现 pending mail，sampling 可以提前结束并进入 follow-up，使新消息更快进入 context。
- V2 child 的 terminal event 会被包装成 completion message 转发给直接 parent。

图上的虚线和 `NOT TESTED` 表示这套逻辑只由固定 commit 的源码确认，本轮没有启用 V2 动态验证；本轮真正观察到的是 V1 `spawn_agent` 路径。[S: `S-027`] [X: `X-005`]

## 静态拓扑

一个 root tree 共享 `AgentControl`、registry/limiter/rollout budget；`CodexDelegate` 创建独立 child Codex，拥有自己的 channels、session、context 与 history，同时继承 effective config、provider、approval、sandbox、cwd、MCP、skills 和 tools。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/codex_delegate.rs#L70) [S: `S-016`]

历史继承不是单一布尔值：full-history fork 保留 user/developer/final assistant 和 metadata；truncated fork 强制 child 重建上下文。[S: `S-017`]

默认配置中 V1 `multi_agent` 开启，V2 关闭；默认最大 child threads 为 6，V2 并发 session 为 4，深度为 1。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/config/mod.rs#L203) [S: `S-015`] 这些数字是版本/配置条件，不应画成 harness 的普遍常数。

## 继承与隔离矩阵

| 维度 | V1 child 的默认语义 | V2 / 条件差异 | 本轮验证边界 |
|---|---|---|---|
| Context/history | Child 创建独立 session、channel、context 与 history；可 full-history fork 或 truncated rebuild。 | V2 还按 `fork_turns`/communication context 选择传播内容。 | V1 请求 digest 与 root 不同；完整 survivor 差分未跑。 |
| Model/provider | 从 parent effective config 派生，child 可继续使用相同 provider/model。 | Role/config 可以覆盖默认值。 | 只验证测试 fixture 下请求可达，没有跑多 provider matrix。 |
| Tools/exposure | 重新构造 child tool surface；达到默认 depth 后不再暴露 spawn namespace。 | V1/V2 namespace、并发限制与 usage hints 不同。 | `X-005` 只覆盖 V1 depth=1。 |
| Approval/sandbox/exec policy | 继承 effective approval、permission/sandbox、cwd；exec policy 只有 config folder/requirement 等价时才可共享 manager。 | V2 可携带额外 communication/policy context。 | 未做 child permission deny 或 escalation experiment。 |
| Workspace/process | 独立 child session/task，但普通 child 使用相同 cwd/filesystem。 | 外部 remote/worktree 隔离不在该默认路径中。 | 未做并发同文件写入或 process crash。 |
| Cancellation/result | 共享 AgentControl 管理 interrupt/lifecycle；result 通过 parent-facing event/message 返回。 | V2 completion 先进入 session mailbox，再按 turn phase 当前轮或下一轮消费。 | V1 spawn 已观察；join/cancel/V2 mailbox 未运行。 |

## 动态观察

`X-SCENARIO-005` 的 root request 暴露一个 `multi_agent_v1` namespace，随后 `spawn_agent` event 返回新的 child thread id。日志出现三个 provider requests：root 首次、root tool-output follow-up、child 首次。child request 有不同 input digest，且不再带 namespace，符合默认 depth limit。[X: `X-005`]

尚未验证：父进程等待/聚合 child final、child crash、cancel propagation、多个 child 同文件写冲突、V2 mailbox/preemption。图中这些未运行机制均不能用实线。
"""

REPORTS["08-sessions-persistence-recovery.md"] = """# Session、持久化与恢复

![Codex persistence lifecycle](../diagrams/generated/codex-persistence-lifecycle.png)

> 图 7（gpt-image-2 读者插图）：主轴是 session items → LiveThread → rollout JSONL → resume → restored history；workspace 是并行现实状态，不会因 resume 自动回滚。Evidence: `D-004`, `S-018`, `S-019`, `S-022`, `X-006`。

<!-- EXPLANATION:persistence-figure -->
## 图 7 的持久化链条

| 阶段 | 作用 |
|---|---|
| Turn items | user/assistant/tool/compaction 等已经规范化、准备持久化的事件 |
| `LiveThread` | 当前活跃 session 使用的高层持久化 handle；过滤 rollout items，并同步派生 metadata |
| `ThreadStore` | storage-neutral 接口；core 不需要知道后端是本地文件、内存还是仓库外实现 |
| Rollout JSONL | local store 的 canonical append history；用于重建 conversation history |
| New process | 原进程结束后启动的另一个 Codex CLI/app-server process |
| Resume same thread | 用同一 thread id 调用 store 的 resume/load history |
| Restored history | 重新进入 `ContextManager`、供后续 model request 使用的有效会话历史 |

`Turn complete → Rollout JSONL` 旁的小箭头表示完成 turn 前会尝试 flush，不表示只有 turn 完成时才 append。`OBSERVED` 覆盖的是正常 create、flush、换进程、resume 路径。[S: `S-018`, `S-019`, `S-022`] [X: `X-006`]

图下方的 `Workspace — not rolled back` 是另一条状态轨道：rollout 记录对话和 tool items，但 resume 不会把文件恢复到旧版本。上方 `Compaction summary — CONDITIONAL` 表示恢复的 history 可能包含压缩后的模型可见表示；它不是另一个 thread store。`Corruption / partial write — NOT TESTED` 是明确的未知项，本轮没有故意截断 JSONL，也没有证明损坏文件能自动修复。

## Live 与 durable state

`ThreadStore` 是 storage-neutral interface，覆盖 create/resume/append/persist/flush/shutdown/load/list/archive/delete；`LiveThread` 是活动持久化边界，resume 时加载 history，append 时先做 persistence filtering 和 metadata patch。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/thread-store/src/live_thread.rs#L91) [D: `D-004`] [S: `S-018`]

local store 的 rollout 文件采用 `rollout-<timestamp>-<thread-id>.jsonl`。后台 writer 在 I/O error 时保留 pending suffix，turn complete 前 task 会 flush，并把失败作为 warning/retry surface。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/rollout/src/recorder.rs#L1511) [S: `S-019`, `S-022`]

## 跨进程验证

首个非 ephemeral exec 创建 thread `019f6985-7c75-7610-b31a-9749f4221892`，并产生相同 id 的 rollout JSONL。第二个进程执行 `exec resume <id>`，输出的 `thread.started` id 不变；fixture 日志显示 provider input 从 3 items 增到 5 items，新增首轮 assistant 与第二轮 user message。[X: `X-006`]

这证明了正常尾部写入后的 resume，不证明中间 JSONL 损坏、flush 半失败、schema 迁移或 workspace drift 的恢复策略。特别是 workspace 是共享外部状态，resume conversation 不等于文件系统 rollback。
"""

REPORTS["09-observability.md"] = """# 可观测性与评估

Codex 有两套互补表面：用户/host 可消费的 thread、turn、item、tool events；以及 OTel logs/traces/metrics。

<!-- EXPLANATION:observability-terms -->
## 三类可观测数据

- **Product events**：`thread.started`、`turn.started`、item/tool/turn completion 等，供 TUI、`exec --json` 和 app-server 客户端驱动 UI 或业务状态。
- **OTel span/log/metric**：供 collector 和 tracing backend 做跨组件关联；span 表示有父子关系的耗时操作，metric 表示可聚合计数/时延，log 记录离散事件。
- **Rollout items**：durable session history，主要用于 resume/replay；它不是为低开销监控设计的 telemetry stream。

三者可能共享 conversation/turn/call id，但目的和保留策略不同。报告中的 provider-side sanitized request log 是本次分析额外加的观察点，不是 Codex 默认对外 API。

任务层创建 turn span，带 conversation/turn/model/token 等字段；tool runtime 发 `codex.tool_call` log，含 trace id、conversation id、turn id、tool/call id 与 duration。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tasks/mod.rs#L384) [S: `S-021`]

OTel 配置默认不记录 user prompts，exporter 可单独关闭，shutdown 必须显式完成。[文档](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/otel/README.md#L1) [D: `D-006`]

app-server 再把内部 events 映射为外部 notifications；exec `--json` 输出本轮观察到的 thread.started、turn.started、agent_message、collab_tool_call、turn.completed/failed。它适合产品集成，却不等同于完整 causal trace：例如 read tool 场景的 exec JSON 没有展示每个内部 handler event，本报告用 provider-side sanitized request log 补足了 tool feedback 证据。

本轮明确关闭 OTel exporter，因而没有声明 span-parent 拓扑、collector delivery 或 telemetry flush 的动态正确性。后续最有价值的实验是启动本地 collector，把同一 deterministic tool turn 对齐到 app-server events、OTel spans 和 rollout items 三个时间轴。
"""

REPORTS["10-design-decisions.md"] = """# 设计决策与权衡

下表的“当前机制”来自代码；“documented intent”只有文档直接支持时才填写；其余 tradeoff 是分析者综合。

<!-- EXPLANATION:decision-table -->
## 怎么读这张表

`当前机制` 只陈述源码实际做法；`Documented intent` 只有仓库文档能直接支持时才填写；`代价/替代方案` 是分析者综合。`置信度=中` 往往不是因为没找到代码，而是因为作者动机未记录、关键 feature 未运行，或结论跨越了多个平台/configuration。

例如“child 独立 context、共享 workspace”的结构证据很明确，但“为什么选择这种隔离粒度”没有作者声明，所以 tradeoff 只能写成可观察后果，不能写成设计团队的真实动机。

| 决策 | 当前机制 | Documented intent | 可观察收益与代价 | 条件/边界 | 证据 | 置信度 | 反例测试 |
|---|---|---|---|---|---|---|---|
| 耐久状态归 thread | `LiveThread` 通过 storage-neutral `ThreadStore` 追加/flush rollout，resume 按 thread id 重建 history。 | Thread-store 文档明确该持久化抽象。 | Resume/fork 语义清晰；代价是 flush、corruption 与 workspace drift 必须分别处理。 | 本轮仅验证 local JSONL 正常尾部与跨进程 resume。 | `D-004`, `S-018`, `S-019`, `X-006` | 高 | 截断 header/middle/tail 并 resume，比较拒绝、降级与 history。 |
| History 与 world state 分离 | Messages 保留 API history；typed world-state snapshot/diff 维护动态环境 baseline。 | AGENTS 要求增量 model-visible context。 | 减少重复注入和 cache churn；baseline 失配会产生陈旧或重复 context。 | Default core；完整 source differential 未执行。 | `D-007`, `S-005`, `S-006`, `I-001` | 中 | 改 cwd/AGENTS/subagent/app 状态并比较 request items 与 diff。 |
| Registry/exposure 分离 | ToolSpecPlan 每 turn 合成 handler registry 与 model-visible specs。 | 未找到直接作者动机。 | 适配 provider/mode/depth；静态工具清单容易被误读为实际能力面。 | Provider capability、feature、MCP、extension、agent depth。 | `S-009`, `X-005` | 高 | 注册 hidden/deferred tool，检查不可见时 model request 与 router 行为。 |
| 进程 exec 使用 policy + sandbox | 普通 command 经 ExecPolicy/approval 后按 permission profile 变换到平台 sandbox；patch 走独立专用链。 | Core README 记录 platform sandbox；统一动机未完整记录。 | 区分授权与隔离；代价是平台、mode 与 handler 矩阵复杂。 | Linux deny 已观察；真实 sandbox backend、MCP/dynamic/patch differential 未跑。 | `D-002`, `S-012`–`S-014`, `S-028`, `I-002` | 中 | 三平台 side-effect matrix，加普通 exec/apply_patch/MCP/dynamic handler 对照。 |
| Child 独立 context、共享 workspace | CodexDelegate/AgentControl 创建独立 child session/history，继承 effective config/cwd。 | 未找到隔离粒度的作者说明。 | 减少 root context；共享 cwd 带来文件竞争与外部状态耦合。 | V1/V2 feature gate；本轮只跑 V1 depth=1。 | `S-015`–`S-017`, `S-027`, `X-005` | 中 | 比较 child context/tools/policy/cwd，并发写同一文件，注入 cancel/crash。 |
| Tool runtime 使用读写锁 | Parallel-capable handler 共享读锁，exclusive handler 获取写锁。 | 未找到直接作者动机。 | 提升只读吞吐并串行化独占副作用；错误分类会破坏安全/顺序假设。 | 由 handler capability 决定，不由工具名称自动推断。 | `S-025` | 中 | 脚本化两 read + 一 exclusive，记录锁、start/end 与 result merge 顺序。 |

## 可证伪性

上述每项都在 [claims](../evidence/claims.jsonl) 中携带 falsification test。特别需要避免两种过度解释：第一，代码的高内聚结构不等于作者明确追求某个价值；第二，一次成功的 deny/resume 实验不等于所有 provider/platform/entrypoint 都具备相同行为。
"""

REPORTS["11-runtime-experiments.md"] = """# 运行实验

## 实验矩阵

| 场景 | 模式与关键配置 | 区分性断言与实际结果 | OS 可见副作用 | 保留工件 | 不能推出什么 |
|---|---|---|---|---|---|
| R-001 | 官方 binary + 真实 SiFlow，最小 Responses。 | Stock request 是否直接可运行；HTTP 400 `Unexpected message role`，在模型输出前失败。 | 无 tool call、无 workspace 写入。 | `traces/raw/real-siflow-minimal.jsonl`。 | 只证明该日期/endpoint 方言不兼容，不证明 Responses 协议整体不可用。 |
| R-002 | 官方 binary + SiFlow + V1 namespace tool。 | Endpoint 是否接受 Codex namespace schema；HTTP 400 schema reject。 | 无 tool call。 | Normalized namespace trace。 | 不能推出关闭 V1 后的所有 tool schema 都失败。 |
| X-001 | Local deterministic SSE，无工具。 | 无 tool 时应正常停止；得到 `SCRIPTED_OK` 与 turn.completed。 | 仅临时 home/workspace。 | Normalized trace + raw request log。 | 不覆盖 tool、policy、compaction 或 persistence。 |
| X-002 | Deterministic SSE，read-only/never，fixture 强制 `exec_command(cat FACTS.txt)`。 | 第二 request 必须包含同 call id 的 output；观察到 function call/output 并返回 `HXA-1445`。 | 只读 `FACTS.txt`。 | `traces/raw/read-tool-requests.jsonl`（未另建 normalized 文件）。 | 不能评价模型自主选 tool 的质量，也不覆盖 write/sandbox。 |
| X-003 | Deterministic SSE，请求不存在工具。 | Unsupported error 是否回流模型；观察到 model-facing output 与 turn completion。 | 无。 | Normalized unknown-tool trace。 | 不证明所有 handler exception 都可恢复。 |
| X-004 | Deterministic SSE，`approval_policy=never`，请求 escalation。 | Policy 是否先于 process 拒绝；观察到 error 回流并完成。 | Marker 未创建，目录清单与文件 hash 不变。 | Denial normalized trace + `X-007` side-effect trace。 | 只覆盖该普通 exec escalation；不覆盖 patch/MCP/dynamic tool。 |
| X-005 | Deterministic SSE + Multi-agent V1，默认 depth=1。 | Child 是否独立 request 且 depth-limited；观察到 child thread、不同 digest、child 无 namespace。 | 共享临时 workspace，无写入。 | `traces/raw/subagent-spawn-requests.jsonl`。 | 不覆盖 join/cancel/crash、并发文件竞争或 V2 mailbox。 |
| X-006 | Deterministic SSE + local rollout，两个进程。 | Resume 是否保持 thread/history；id 相同，provider input 3→5。 | 只写临时 rollout。 | `traces/raw/resume-requests.jsonl` 与临时 rollout 记录。 | 只验证正常尾部；不覆盖 partial write、corruption、fork 或 workspace drift。 |

<!-- EXPLANATION:experiment-modes -->
## 表中模式与结果怎么解释

`R-*` 是官方 Codex binary 连接真实 SiFlow endpoint 的兼容性观察；失败仍是有效结果，因为它说明 stock request 在模型输出前被哪一层拒绝。`X-*` 是 deterministic Responses fixture：fixture 不理解任务，只按预先写好的 call id/item type 强制 Codex 走指定分支，因此适合验证 harness control flow。

`passed` 表示预先声明的区分性断言成立，不表示整个功能面都正确。例如 X-004 证明 `never` 在该 escalation 请求上先于 process 拒绝，并用文件哈希检查了无副作用；它没有证明所有 shell/MCP/dynamic tool 都经过同一 gate。详细配置和 trace 路径在 [scenario catalog](../scenarios/catalog.json)。

## 为什么真实模型没有伪装成成功

SiFlow 的 `/responses` 基础 SSE probe 能返回 reasoning/message/completed，说明 endpoint 不是完全不支持 Responses。但 Codex 发出的真实请求包含更具体的 dialect：developer role，以及 V1 的 namespace tool schema。当前 endpoint 均拒绝，因此本报告不声称完成“真实模型 agent tool turn”。[R: `R-002`, `R-003`]

如果引入 role/namespace translation proxy，就可以继续测真实 Qwen 行为，但那会改变系统边界；报告必须把 proxy 作为新节点和实验条件，而不能把其结果归因于 stock Codex 0.144.5。

## 为什么 deterministic fixture 有效

fixture 不解释 prompt，也不随机选择工具。它以 call id 和 input item type 作为门槛，强制 harness 进入指定分支；请求日志只保留 role/type/tool name 和文本哈希。这适合验证 loop、router、policy、subagent、resume 等机制，但不评价模型质量。

完整定义见 [scenario catalog](../scenarios/catalog.json)，服务器代码见 [scripted_responses_server.py](../experiments/scripted_responses_server.py)。
"""

REPORTS["12-failure-modes-open-questions.md"] = """# 失败模式与开放问题

## 已验证失败

- `Unexpected message role`: supplied SiFlow endpoint 与 stock Codex request role 不兼容。[R: `R-002`]
- `namespace` schema rejected: V1 multi-agent 的 provider capability 要求高于普通 function tools。[R: `R-003`]
- unsupported tool: router 记录 error，但把结果回流并允许 turn 完成。[X: `X-003`]
- forbidden escalation: `never` policy 在进程执行前拒绝。[X: `X-004`, `X-007`]

<!-- EXPLANATION:failure-terms -->
## 这里的“失败”分三类

- **Provider dialect failure**：HTTP endpoint 存在，但不接受 Codex 使用的 message role 或 tool schema；这不是 agent loop 自身失败。
- **Handled tool failure**：unknown tool 或 policy deny 被包装为 model-facing output，当前 turn 仍可能恢复并完成。
- **Durability/recovery failure**：timeout、process crash、partial rollout、corruption 或 workspace drift，可能影响跨 turn/process 恢复；本轮大多尚未故障注入。

因此下面的开放问题既包括产品风险，也包括分析覆盖缺口。`V2 mailbox preemption` 指 parent 在 reasoning/commentary 期间收到 child mail 时提前结束当前 sampling、转入吸收消息的 follow-up；它不等于强制终止整个 parent session。[S: `S-027`]

## 高价值未知项

1. pre-turn、mid-turn、remote/local compaction 是否在同一超长 scenario 下保持语义等价？
2. MCP、dynamic/hosted tools 是否全部经过与 exec 相同的 approval/sandbox 边界？答案很可能按 handler 不同，必须逐类验证。
3. V2 mailbox preemption、child crash 与 root cancel 的事件/rollout 顺序是什么？
4. rollout 尾部截断、中间 corruption、store flush failure 后 resume 是拒绝、修复还是部分恢复？
5. workspace 在 resume/fork 和多个 child 并发写入时如何检测 drift/conflict？
6. OTel、app-server events、rollout items 是否可用同一 turn/call id 无歧义对齐？

## 下一轮优先实验

优先级最高的是一个本地 translation proxy：只把 developer role 与 namespace tools 降解成 endpoint 可接受格式，并完整记录变换。它能把“真实模型不可运行”从 blocker 变成可比较条件，同时诚实保留 stock 与 adapted 两种架构。

其次是 fault injection：oversized tool output 触发 compaction；写入后拒绝/超时验证 side-effect reporting；截断 rollout 验证 resume；两个 child 竞争同一 fixture 文件验证 workspace ownership。

| 优先级 | 实验 | 要区分的机制 | 通过标准 | 仍不能推出 |
|---|---|---|---|---|
| P0 | stock/adapted provider 对照 | endpoint 方言不兼容，还是 Codex loop 本身失败 | adapter 只改 role/schema；两侧请求 hash、变换日志和 tool feedback 均可审计 | adapted 成功不代表 stock Codex 兼容 |
| P0 | shell / unified exec / direct `apply_patch` 对照 | 普通 exec policy 与专用 patch governance 的边界 | 三个入口分别记录 approval key、sandbox runtime 与是否创建 process | 单平台结果不能代表所有 sandbox backend |
| P1 | compaction 阈值与顺序 | pre-turn、mid-turn、remote/local replacement 是否等价 | token snapshot、replacement、rollout 与 resume 顺序可重放 | 一次长上下文不能覆盖所有模型窗口变化 |
| P1 | rollout corruption/flush failure | durable history 在部分写入后的恢复模型 | 对尾部截断、中段损坏、flush error 给出拒绝/修复/部分恢复分类 | conversation 恢复不表示 workspace 回滚 |
| P1 | V2 child crash/cancel/mailbox | parent sampling、mailbox 和 terminal events 的因果顺序 | turn/call/agent id 可在 events、rollout 与 provider log 中对齐 | V1 的结果不能外推到 V2 |
| P2 | 多 child workspace 冲突 | context 隔离下的共享文件竞争 | 两 child 写同一 fixture 时观察到明确冲突、序列化或最后写入语义 | 单文件结果不覆盖 git 或目录级冲突 |
"""

REPORTS["13-coverage-reproducibility.md"] = """# 覆盖率与复现

## 结构化产物

- [manifest.json](../manifest.json): commit、配置、隔离与 runtime
- [inventory.json](../inventory.json): 有界确定性仓库清点
- [hir.json](../hir.json): 29 nodes / 38 edges 的 harness IR
- [claims.jsonl](../evidence/claims.jsonl): 24 个可证伪 claims
- [observations.jsonl](../evidence/observations.jsonl): D/S/R/X/I 证据
- [coverage.json](../evidence/coverage.json): 14 模块局部覆盖与未知项
- [scenarios/catalog.json](../scenarios/catalog.json): 8 个真实/确定性场景
- [questions.json](../questions.json): 下一轮实验队列
- [generated metadata](../diagrams/generated/metadata.json): gpt-image-2 prompt/output hash 与语义审查

<!-- EXPLANATION:artifact-map -->
## 不同产物分别用来回答什么

- 想快速理解系统：从 [report/index.md](index.md) 和八张读者图开始。
- 想确认一句结论：在 [claims.jsonl](../evidence/claims.jsonl) 找 claim id，再跳到对应 D/S/R/X/I evidence。
- 想程序化比较另一个版本：使用 [hir.json](../hir.json) 的 typed nodes/edges 和 conditions。
- 想复现实验：使用 [scenario catalog](../scenarios/catalog.json)、`experiments/` 和 sanitized traces。
- 想判断“没有观察到”究竟意味着什么：查看 [coverage.json](../evidence/coverage.json) 的 configurations、excluded surfaces 和 unresolved。

当前 bundle 包含 29 个 HIR nodes、38 条 edges、24 个 claims 和 47 条 evidence records。图片不新增任何 claim；它们只是这些结构化事实的读者投影。

## 14 模块覆盖矩阵

`analyzed` 表示固定版本的主机制和关键分支已静态恢复；`partial` 表示仍缺少会改变结论边界的平台、feature 或故障路径动态覆盖。状态不是代码阅读比例。

| 模块 | 状态 | 已恢复机制 | 动态边界 | 未解决问题 |
|---|---|---|---|---|
| `interfaces` | analyzed | CLI/TUI/exec/app-server/MCP server 的入口分派与 thread API 收敛 | 运行了 exec JSON；TUI、app-server、MCP server 未端到端运行 | 无额外模块级未知项；仍受全局配置边界约束 |
| `core_loop` | analyzed | run_turn 的 prompt、stream、tool feedback、follow-up 与 stop 条件 | X-001/002/003/004 观察 stop、二次采样和可恢复 tool error | 无额外模块级未知项；仍受全局配置边界约束 |
| `context_assembly` | analyzed | ContextManager、StepContext、WorldState 与可见 tool specs | X-002 观察 tool output 进入下一请求；未做 WorldState 差分矩阵 | 无额外模块级未知项；仍受全局配置边界约束 |
| `compaction` | partial（关键平台、feature 或故障路径尚缺动态覆盖） | pre-turn/mid-turn selector、remote v2/v1 与 local replacement | 未触发超长上下文；结论限于固定源码路径 | 未用 oversized tool output 或 token fixture 动态触发 pre-turn/mid-turn/remote compaction。 |
| `model_abstraction` | partial（关键平台、feature 或故障路径尚缺动态覆盖） | ModelClientSession、provider dialect、transport fallback 与 retry | 真实 SiFlow 两种方言失败，确定性 Responses fixture 成功 | SiFlow 需要 role/namespace translation adapter 才能执行真实 agent turn；本报告没有修改 target code。 |
| `tools_extensions` | analyzed | ToolSpecPlan、registry/exposure、router、hooks、MCP/dynamic handlers | 覆盖 built-in exec、unknown tool 和 V1 namespace；MCP/dynamic 未运行 | 无额外模块级未知项；仍受全局配置边界约束 |
| `permissions_safety` | analyzed | ExecPolicy、approval cache，以及独立 apply_patch governance | X-004/007 验证 never 前置拒绝与无文件副作用；apply_patch 未动态对照 | 无额外模块级未知项；仍受全局配置边界约束 |
| `sandbox_execution` | partial（关键平台、feature 或故障路径尚缺动态覆盖） | permission profile 到 Linux/macOS/Windows sandbox executor 的变换 | 只观察 sandbox 之前的 policy deny；未实际比较三平台 backend | 宿主没有 Rust toolchain，且当前执行环境无法直接复现所有 platform sandbox backend。 |
| `workspace` | partial（关键平台、feature 或故障路径尚缺动态覆盖） | cwd、文件副作用、resume 后现实状态与多 agent 共享目录 | 验证 denied write 的目录/哈希不变；未做 resume drift 或 child 写冲突 | 未验证 worktree、remote environment 与并发 child 文件冲突。 |
| `sessions_persistence` | analyzed | ThreadStore、LiveThread、rollout append/flush/resume | X-006 验证正常 JSONL 尾部跨进程 resume；未注入 corruption | 无额外模块级未知项；仍受全局配置边界约束 |
| `subagents` | analyzed | AgentControl、CodexDelegate、V1/V2 gate、depth/limit/mailbox | 只运行 V1 root/child request 与 depth exposure；V2 未运行 | 无额外模块级未知项；仍受全局配置边界约束 |
| `orchestration` | analyzed | RegularTask、Task 生命周期、active turn 与 tool 并发锁 | X-001/002/003/004/005 覆盖正常、工具反馈、错误与 V1；未做 hang/cancel | 无额外模块级未知项；仍受全局配置边界约束 |
| `observability` | partial（关键平台、feature 或故障路径尚缺动态覆盖） | 产品 events、app-server notifications 与 OTel logs/traces/metrics | 观察 exec 产品 events 和 provider request log；OTel exporter 关闭 | OTel exporter 关闭，未检查 collector 端 span 拓扑。 |
| `recovery` | partial（关键平台、feature 或故障路径尚缺动态覆盖） | provider retry、cancellation、tool error、flush 与恢复边界 | 覆盖 unsupported tool、policy deny 和正常 resume；未做 crash/timeout/flush failure | 未注入 stream idle timeout、tool process crash、rollout corruption 与 SIGINT。 |

## 关键复现条件

```text
tag: rust-v0.144.5
commit: 87db9bc18ba5bc82c1cb4e4381b44f693ee35623
binary: codex-cli 0.144.5 (official x86_64-unknown-linux-musl release)
default test policy: approval=never, sandbox=read-only
deterministic provider: local Responses SSE fixture on 127.0.0.1
real provider: user-authorized SiFlow qwen3.6-35ba3b
```

动态场景的命令模板、配置约束与 trace 路径记录在 catalog；API key 不属于复现产物。

## 覆盖判断

14 个模块均完成源码调查；6 个模块标为 partial，原因是缺少跨平台、超长上下文、OTel、fault injection 或真实 provider 成功路径。没有把 “not observed” 写成 “absent”。目标 checkout 未修改。

## Claim index

`C-001`–`C-024` 的声明、evidence、coverage 与 falsification test 以 [claims.jsonl](../evidence/claims.jsonl) 为唯一索引；图只做语义投影，不新增事实。
"""

REPORTS["14-source-claim-index.md"] = """# 源码与 Claim 索引

本页把正文结论映射回固定 commit 的源码/文档锚点和命名运行场景。Evidence ID 是稳定连接键；链接只用于阅读便利。`置信度`表示在声明 scope 内证据强度，不表示该机制在所有平台、feature 或生产配置中的出现频率。

| Claim | 可证伪结论 | 固定源码/文档锚点 | 动态或推断证据 | Scope / 置信度 | 反证实验 |
|---|---|---|---|---|---|
| `C-001` | Codex CLI、TUI、exec、app-server 与 MCP server 是不同产品表面，但会收敛到同一 core session/thread runtime。 | [D-001: README.md](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/README.md#L1)<br>[D-003: codex-rs/app-server/README.md](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/app-server/README.md#L1)<br>[S-001: codex-rs/cli/src/main.rs:Subcommand](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/cli/src/main.rs#L124) | `R-001`: command: codex --version | rust-v0.144.5 product surfaces; `high`; `supported` | 为每个入口寻找独立 agent loop；本轮静态追踪未发现，app-server 仍通过 thread/session core。 |
| `C-002` | 常规 turn 是一个显式采样循环：组装 prompt、流式读取 Responses、并行或独占执行工具、把结果写回 history，并在需要时继续采样。 | [S-002: codex-rs/core/src/tasks/regular.rs:RegularTask::run](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tasks/regular.rs#L37)<br>[S-003: codex-rs/core/src/session/turn.rs:run_turn](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/session/turn.rs#L224) | `X-001`: [traces/normalized/X-001-text-stop.normalized.jsonl](../traces/normalized/X-001-text-stop.normalized.jsonl)<br>`X-002`: [traces/raw/read-tool-requests.jsonl](../traces/raw/read-tool-requests.jsonl) | RegularTask and run_turn; `high`; `supported` | 脚本化一次 function_call，检查是否存在不回填 tool output 的直接退出；X-002 观察到两次请求和 output 回填。 |
| `C-003` | 模型请求由 base instructions、会话 history、world-state 更新、每 turn 输入和当前可见 tool specs 共同构成。 | [D-007: AGENTS.md](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/AGENTS.md#L1)<br>[S-004: codex-rs/core/src/session/turn.rs:build_prompt](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/session/turn.rs#L1084)<br>[S-005: codex-rs/core/src/context_manager/history.rs:ContextManager](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/context_manager/history.rs#L36) | 未做专项动态验证；当前由固定源码/文档支持 | default exec/read-only configuration; `medium`; `supported` | 分别关闭项目指令、skills、MCP 与动态工具后比较请求体；本轮只验证了最小配置，完整差分未执行。 |
| `C-004` | Codex 把对话历史与可差分的 world state 分开管理：history 保留模型可见 items，world state 用 RFC 7386 风格 snapshot/diff 减少重复注入。 | [D-007: AGENTS.md](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/AGENTS.md#L1)<br>[S-005: codex-rs/core/src/context_manager/history.rs:ContextManager](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/context_manager/history.rs#L36)<br>[S-006: codex-rs/core/src/context/world_state/mod.rs:WorldState](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/context/world_state/mod.rs#L206) | `I-001`: analyst synthesis from S-005/S-006 | core context manager; `medium`; `supported` | 修改 cwd、AGENTS.md、subagent 列表并比较 world-state items；源码支持，动态差分仍待专项实验。 |
| `C-005` | 自动 compaction 既可能在 turn 前触发，也可能在 tool follow-up 中触发；实现还区分 remote v2、remote v1 与 local compaction，并处理模型上下文下调。 | [S-007: codex-rs/core/src/session/turn.rs:compact](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/session/turn.rs#L798) | 未做专项动态验证；当前由固定源码/文档支持 | core compaction; `medium`; `supported` | 使用 scripted provider 推高 token estimate，分别触发 pre-turn、mid-turn 和 model-switch；本轮未执行超长上下文场景。 |
| `C-006` | ModelClientSession 在 turn 内跨 retry 复用 transport 状态，WebSocket 不可用时会 session-scoped 回退，增量请求依赖前缀匹配。 | [S-008: codex-rs/core/src/client.rs:ModelClientSession](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/client.rs#L194)<br>[S-024: codex-rs/model-provider-info/src/lib.rs:ModelProviderInfo](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/model-provider-info/src/lib.rs#L90) | 未做专项动态验证；当前由固定源码/文档支持 | Responses model boundary; `medium`; `supported` | 构造 WebSocket 首次失败、随后成功的 provider，并检查回退是否只在该 session 生效；未动态执行。 |
| `C-007` | 工具 registry 与模型可见 exposure 是两层：工具可已注册但延迟/隐藏；当前 turn 再把内置工具、MCP、connectors、extensions 与 dynamic tools 合成为 specs。 | [S-004: codex-rs/core/src/session/turn.rs:build_prompt](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/session/turn.rs#L1084)<br>[S-009: codex-rs/core/src/tools/spec_plan.rs:ToolSpecPlan](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tools/spec_plan.rs#L158)<br>[S-026: codex-rs/core/src/tools/handlers](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tools/handlers/dynamic.rs#L32) | 未做专项动态验证；当前由固定源码/文档支持 | tool spec planning; `high`; `supported` | 注册 hidden/deferred tool 并要求模型调用，检查 router 是否保有实现但请求 specs 不暴露；静态实现明确。 |
| `C-008` | ToolRouter 统一解析调用，registry 在 handler 前执行 pre-tool hooks；ToolCallRuntime 以读写锁允许只读工具并行、要求独占的工具串行。 | [S-010: codex-rs/core/src/tools/router.rs:ToolRouter](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tools/router.rs#L35)<br>[S-011: codex-rs/core/src/tools/registry.rs:dispatch](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tools/registry.rs#L322)<br>[S-025: codex-rs/core/src/tools/parallel.rs:ToolCallRuntime](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tools/parallel.rs#L42) | 未做专项动态验证；当前由固定源码/文档支持 | core tool runtime; `medium`; `supported` | 脚本化两个 read-only 与一个 exclusive 工具，比较开始/结束事件；本轮只验证单工具往返。 |
| `C-009` | 真正启动进程的 exec 路径先计算 approval/exec-policy requirement，再进入 sandbox；在 approval_policy=never 时，模型请求 require_escalated 会在创建进程前被拒绝。 | [S-012: codex-rs/core/src/exec_policy.rs:ExecPolicy](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/exec_policy.rs#L169)<br>[S-013: codex-rs/core/src/tools/sandboxing.rs](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tools/sandboxing.rs#L41)<br>[S-014: codex-rs/core/src/exec.rs:SandboxManager](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/exec.rs#L117) | `X-004`: [traces/normalized/X-004-denied-escalation.normalized.jsonl](../traces/normalized/X-004-denied-escalation.normalized.jsonl)<br>`X-007`: [traces/normalized/X-007-side-effect-check.normalized.jsonl](../traces/normalized/X-007-side-effect-check.normalized.jsonl) | exec tool, never/read-only; `high`; `supported` | 请求 touch 文件并声明 require_escalated；X-004 返回 policy error，X-007 证实目录与文件哈希未变。 |
| `C-010` | sandbox 是 platform-specific execution transform：Linux、macOS、Windows 使用不同后端，权限 profile 还独立表达 filesystem 与 network；它不是单一布尔开关。 | [D-002: codex-rs/core/README.md](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/README.md#L1)<br>[S-014: codex-rs/core/src/exec.rs:SandboxManager](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/exec.rs#L117) | `I-002`: analyst synthesis from D-002/S-012/S-014 | platform execution layer; `medium`; `supported` | 在三平台运行相同 side-effect matrix；本轮只在 Linux 主机验证 policy 前置拒绝，未覆盖实际 sandbox backend。 |
| `C-011` | ThreadStore/LiveThread 是持久化边界，rollout 采用追加式 JSONL；resume 会加载历史并保持同一 thread id。 | [D-004: codex-rs/thread-store/README.md](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/thread-store/README.md#L1)<br>[S-018: codex-rs/thread-store/src/store.rs and live_thread.rs](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/thread-store/src/live_thread.rs#L91)<br>[S-019: codex-rs/rollout/src/recorder.rs](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/rollout/src/recorder.rs#L1511) | `X-006`: [traces/raw/resume-requests.jsonl](../traces/raw/resume-requests.jsonl) | local rollout store; `high`; `supported` | 新进程恢复首轮 session 并比较 thread id 与请求历史；X-006 观察到同 id 和增加的 assistant/user items。 |
| `C-012` | subagent 是独立 Codex child session：拥有自己的 channel、context 与 history，继承有效配置/审批/sandbox/cwd，并通过共享 AgentControl 受父树治理。 | [S-015: codex-rs/core/src/config/mod.rs:MultiAgentConfig](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/config/mod.rs#L203)<br>[S-016: codex-rs/core/src/codex_delegate.rs:spawn](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/codex_delegate.rs#L70)<br>[S-017: codex-rs/core/src/agent/control/spawn.rs](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/agent/control/spawn.rs#L45) | `X-005`: [traces/raw/subagent-spawn-requests.jsonl](../traces/raw/subagent-spawn-requests.jsonl) | multi_agent V1; `medium`; `supported` | 创建 child 后比较 request digest、工具集合、cwd 与 policy；X-005 证实独立请求和不同 tool exposure，完整隔离矩阵未跑。 |
| `C-013` | V1 与 V2 multi-agent 是分离 feature gate；v0.144.5 默认 V1 开启、V2 关闭，默认并发/深度限制阻止无界递归。V2 还使用 session-scoped mailbox 把 child completion 和其他 inter-agent communication 投递给 parent，并按 turn phase 决定当前轮或下一轮消费。 | [S-015: codex-rs/core/src/config/mod.rs:MultiAgentConfig](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/config/mod.rs#L203)<br>[S-027: codex-rs/core/src/state/turn.rs:MailboxDeliveryPhase](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/state/turn.rs#L35) | `X-005`: [traces/raw/subagent-spawn-requests.jsonl](../traces/raw/subagent-spawn-requests.jsonl) | feature configuration; `medium`; `supported` | 分别启用 V1/V2，检查工具 namespace、child depth 与并发上限；再让 V2 child 在 parent 可见 final 前后完成，比较 mailbox 是进入当前 follow-up 还是留到下一 turn。本轮只运行 V1，mailbox 语义为静态源码结论。 |
| `C-014` | 长期 memories 是默认关闭的实验性两阶段流水线：Phase 1 从 rollout 提取结构化记忆，Phase 2 在全局锁下由专用 agent 聚合到 durable memory 文件。 | [D-005: codex-rs/memories/README.md](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/memories/README.md#L1)<br>[S-020: codex-rs/core/src/memories](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/memories/write/src/start.rs#L18) | 未做专项动态验证；当前由固定源码/文档支持 | experimental memories feature; `medium`; `supported` | 启用 memories 后创建多个 eligible rollout，等待 phase1/phase2 并检查租约、红action与合并结果；本轮未启用。 |
| `C-015` | app-server 用双向 JSON-RPC 暴露 thread 生命周期，并把处理 loop 与 outbound writer loop 分开，以避免慢客户端阻塞请求处理。 | [D-003: codex-rs/app-server/README.md](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/app-server/README.md#L1)<br>[S-023: codex-rs/app-server/src/lib.rs](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/app-server/src/lib.rs#L150) | 未做专项动态验证；当前由固定源码/文档支持 | app-server; `medium`; `supported` | 构造慢 writer 和突发通知，观察有界队列背压与 processor 是否继续；未动态执行。 |
| `C-016` | Codex 同时暴露产品事件与 OTel logs/traces/metrics；turn、tool call、conversation id 和 token/timing 是主要关联键，默认不记录用户 prompt。 | [D-006: codex-rs/otel/README.md](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/otel/README.md#L1)<br>[S-021: codex-rs/core/src/tasks/mod.rs and tools/parallel.rs](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tasks/mod.rs#L384) | 未做专项动态验证；当前由固定源码/文档支持 | observability surfaces; `medium`; `supported` | 启用本地 OTel exporter 并执行 tool turn，校验 trace-parent 与 prompt redaction；本轮 exporter 关闭。 |
| `C-017` | 恢复不是一个全局 retry：provider stream retry 有界，tool/turn cancellation 由 token 传播，turn 结束前会尝试 flush rollout；失败 turn 不必销毁 session。 | [S-002: codex-rs/core/src/tasks/regular.rs:RegularTask::run](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tasks/regular.rs#L37)<br>[S-003: codex-rs/core/src/session/turn.rs:run_turn](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/session/turn.rs#L224)<br>[S-008: codex-rs/core/src/client.rs:ModelClientSession](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/client.rs#L194)<br>[S-022: codex-rs/core/src/tasks/mod.rs:Task](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tasks/mod.rs#L313) | 未做专项动态验证；当前由固定源码/文档支持 | turn recovery; `medium`; `supported` | 分别注入 stream timeout、tool hang、rollout I/O failure 和 user interrupt，检查边界与 session 后续可用性；未完整执行。 |
| `C-018` | 用户提供的 SiFlow endpoint 支持基础 Responses SSE，但不能直接接受 Codex 0.144.5 的完整请求方言：最小路径拒绝 developer role，V1 路径拒绝 namespace tool。 | [S-024: codex-rs/model-provider-info/src/lib.rs:ModelProviderInfo](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/model-provider-info/src/lib.rs#L90) | `R-002`: [traces/raw/real-siflow-minimal.jsonl](../traces/raw/real-siflow-minimal.jsonl)<br>`R-003`: [traces/normalized/R-002-siflow-namespace.normalized.jsonl](../traces/normalized/R-002-siflow-namespace.normalized.jsonl) | SiFlow qwen3.6-35ba3b compatibility on 2026-07-16; `high`; `supported` | 不改 Codex 请求直接运行真实 endpoint；两种配置均在模型输出前稳定返回 HTTP 400。 |
| `C-019` | 确定性 Responses fixture 观察到 function_call -> exec_command -> function_call_output -> 第二次 model request 的闭环，工具结果进入了下一轮 context。 | [S-003: codex-rs/core/src/session/turn.rs:run_turn](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/session/turn.rs#L224)<br>[S-010: codex-rs/core/src/tools/router.rs:ToolRouter](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tools/router.rs#L35) | `X-002`: [traces/raw/read-tool-requests.jsonl](../traces/raw/read-tool-requests.jsonl) | X-SCENARIO-002; `high`; `supported` | 让第二次响应仅在看到指定 call_id 的 function_call_output 时返回验证码；场景通过。 |
| `C-020` | 未知工具和被 policy 拒绝的工具调用都会变成模型可消费的结果，而不是让整个 session 无条件崩溃。 | [S-010: codex-rs/core/src/tools/router.rs:ToolRouter](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tools/router.rs#L35)<br>[S-011: codex-rs/core/src/tools/registry.rs:dispatch](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tools/registry.rs#L322) | `X-003`: [traces/normalized/X-003-unknown-tool.normalized.jsonl](../traces/normalized/X-003-unknown-tool.normalized.jsonl)<br>`X-004`: [traces/normalized/X-004-denied-escalation.normalized.jsonl](../traces/normalized/X-004-denied-escalation.normalized.jsonl) | scripted failure paths; `high`; `supported` | 请求不存在工具与禁止提权命令，要求 fixture 只在收到 tool output 后结束；两场景均继续到 final answer。 |
| `C-021` | 一次持久化 turn 与随后 resume 在两个进程中保持同一 thread id，且恢复后的 provider input 包含首轮 assistant 消息。 | [S-018: codex-rs/thread-store/src/store.rs and live_thread.rs](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/thread-store/src/live_thread.rs#L91)<br>[S-019: codex-rs/rollout/src/recorder.rs](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/rollout/src/recorder.rs#L1511) | `X-006`: [traces/raw/resume-requests.jsonl](../traces/raw/resume-requests.jsonl) | X-SCENARIO-006; `high`; `supported` | 恢复时不重发首轮输出，只检查第二次 provider input；观察到 input_count 从 3 增至 5。 |
| `C-022` | V1 child 的初始请求与 root 独立，且达到默认深度后不再暴露 multi_agent namespace；root 与 child 仍共享同一 workspace 语义。 | [S-015: codex-rs/core/src/config/mod.rs:MultiAgentConfig](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/config/mod.rs#L203)<br>[S-016: codex-rs/core/src/codex_delegate.rs:spawn](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/codex_delegate.rs#L70) | `X-005`: [traces/raw/subagent-spawn-requests.jsonl](../traces/raw/subagent-spawn-requests.jsonl) | X-SCENARIO-005 and default max_depth=1; `medium`; `supported` | 在 child 请求中检查 namespace tool 是否消失，并尝试继续 spawn；本轮请求日志证实 tool exposure 消失，未再请求 spawn。 |
| `C-023` | 并发工具语义由 handler 的 parallel/exclusive 分类控制，而不是对所有 tool calls 一律并行。 | [S-025: codex-rs/core/src/tools/parallel.rs:ToolCallRuntime](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tools/parallel.rs#L42) | 未做专项动态验证；当前由固定源码/文档支持 | ToolCallRuntime; `medium`; `supported` | 脚本化并发读写工具并记录锁获取顺序；本轮仅有源码证据。 |
| `C-024` | shell 与 unified-exec handler 会在通用 exec-policy requirement 之前识别 apply_patch，并把它路由到具有独立 patch safety、按路径 approval cache 与 sandbox runtime 的专用治理路径；因此 exec-policy → sandbox 不能泛化为所有 shell tool 输入。 | [S-028: codex-rs/core/src/tools/handlers/shell.rs:intercept_apply_patch](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tools/handlers/shell.rs#L142) | 未做专项动态验证；当前由固定源码/文档支持 | apply_patch interception in shell and unified exec; `medium`; `supported` | 分别通过 shell、unified exec 和直接 apply_patch tool 提交同一补丁，比较是否都进入 ApplyPatchRuntime、是否按文件路径请求 approval，并确认没有普通进程 spawn。 |

## 使用边界

- `S/D` 证明固定 commit 中存在该结构或文档约束；不证明生产启用频率。
- `R/X` 证明命名 scenario 与配置下发生过该行为；不自动外推到其他 provider、平台或 feature。
- `I` 是从多个事实推出的分析者综合；必须保留可证伪条件，不能改写成作者意图。
- 完整 record、conditions、counterevidence 和 coverage 以 [`claims.jsonl`](../evidence/claims.jsonl) 与 [`observations.jsonl`](../evidence/observations.jsonl) 为准。
"""

REPORTS["16-glossary.md"] = """# 全局术语表

本表定义的是 **Codex 0.144.5 本报告中的用法**。同一名词在产品 UI、Responses API 或其他 agent framework 中可能有不同边界；章节首次出现时应按这里的定义理解。

| 术语 | 精确定义 | 容易混淆但不等价的概念 | 主要证据 |
|---|---|---|---|
| Thread | 由 `thread_id` 标识、可跨 turn 和进程恢复或 fork 的逻辑会话身份；durable history 通过 `LiveThread`/rollout 保存。 | 不是当前 Rust 进程中的 session，也不拥有 workspace 快照。 | `D-004`, `S-018`, `X-006` |
| Session | 当前进程中处理某个 thread 的 live runtime，持有 event channel、provider、policy、services、context 和最多一个 active turn。 | 进程退出后不会原样持久化；resume 同一 thread 会创建新的 session。 | `S-002`, `S-022` |
| Turn | 一次任务的调度边界，从 `TurnStarted` 到 `TurnComplete` 或 `TurnAborted`；内部可以包含多次模型请求和工具调用。 | 不等于单次 Responses API request，也不等于整条 thread。 | `S-002`, `S-003`, `X-002` |
| Model request / sampling | turn 内一次把 prompt、history 和 tool specs 发送给 provider 并消费 stream 的操作。 | 一次 turn 可反复 sampling；tool feedback 后通常会产生下一 request。 | `S-003`, `X-002` |
| `StepContext` | 某次 sampling/tool invocation 固定使用的 model、cwd、approval、sandbox、tools 等请求级快照。 | 不是整个 session 的可变状态，也不是仅包含 message 的 context。 | `S-004`, `S-010` |
| Context | 后续模型请求可见的信息组合：base instructions、history、world-state 更新、当前输入及 tool specs。 | 不等于 rollout 全量，也不等于 workspace 文件内容。 | `S-004`–`S-006` |
| History | `ContextManager` 按 oldest-first 管理的模型可见 API items，包括 message、function call 与 tool output。 | 不包含每个内部 event；compaction 后的有效 history 也不等于原始 rollout 文本。 | `S-005`, `X-002` |
| World state | AGENTS、环境、subagent/apps/plugins 等带类型的运行环境状态，以 snapshot/RFC 7386 风格 diff 增量注入。 | 不是 git diff，也不是任意自然语言 memory。 | `D-007`, `S-006` |
| Compaction | token/window 条件触发的 history replacement；可在 turn 前或 tool follow-up 中发生，并区分 remote/local 实现。 | 不是简单删除最旧字符串，也不回滚 workspace 或 durable rollout。 | `S-007` |
| Long-term memories | 默认关闭的实验性两阶段 pipeline：从 rollout 提取记忆，再由专用 agent consolidation 到 durable 文件。 | 不等于每轮都执行的 compaction。 | `D-005`, `S-020` |
| Registry | 当前进程已经注册、router 能定位 handler implementation 的工具集合。 | 工具在 registry 中不表示本次模型请求可见。 | `S-009`, `S-011` |
| Exposure | 某次 turn/request 实际发送给模型的 tool schema 子集，由 provider capability、feature、depth 和 hidden/deferred 规则决定。 | 不等于 registry，也不等于工具一定会被模型调用。 | `S-009`, `X-005` |
| Tool spec | 发送给 provider 的工具名称、参数 schema 和调用形式描述。 | 它不是 handler 实现，也不授予副作用权限。 | `S-004`, `S-009` |
| Router / Registry / Handler | Router 解析 function/custom/namespace call 并绑定 context；registry 查找实现并运行 hooks；handler 执行具体能力。 | 三者是连续阶段，不是同一个“tool layer”。 | `S-010`, `S-011` |
| Dynamic / hosted tool | host 在运行时提供 schema 或回传结果的工具能力；dynamic handler 可等待 host response。 | 不应默认认为它与进程 exec 共享 approval/sandbox 路径。 | `S-026` |
| MCP | Model Context Protocol；Codex 可从 MCP server 合并工具，并通过专门 handler 调用。 | MCP 是能力来源/协议，不等于 Codex 内置 sandbox。 | `S-009`, `S-026` |
| Namespace tool | provider tool schema 中按 namespace 组织的一类调用形式；本版本 V1 multi-agent 使用它。 | 不等于普通 function tool；SiFlow 本轮接受后者但拒绝该 schema。 | `R-003`, `X-005` |
| Exec policy | 对真正启动进程的命令 segment 计算 `forbid/prompt/allow` requirement 的规则层。 | 不是 platform sandbox；也不能泛化为所有 handler 的副作用治理。 | `S-012` |
| Approval policy/cache | 决定何时可询问用户及是否在同一 session 复用批准；cache key 可由命令或目标路径构成。 | 批准不等于关闭 sandbox，也不是跨 session 的永久授权。 | `S-013`, `S-028` |
| Sandbox / permission profile | 把 filesystem/network 权限转换成 Linux、macOS 或 Windows 的实际执行约束。 | 不是布尔开关，也不是 approval 的同义词。 | `D-002`, `S-014` |
| `apply_patch` 专用路径 | shell/unified-exec 在普通 exec requirement 前识别补丁，交给 patch safety、按路径 approval 和可 sandbox 的 `ApplyPatchRuntime`。 | 它不是先启动 shell 再执行任意命令；也不证明补丁无需审批。 | `S-028` |
| Parallel / exclusive tool | `ToolCallRuntime` 对允许并行的 handler 使用读锁，对需独占的 handler 使用写锁。 | “模型一次返回多个调用”不表示所有调用必然并行。 | `S-025` |
| `AgentControl` | root agent tree 共享的 child registry、并发/深度限制、消息、interrupt 与 lifecycle 控制面。 | 不等于 child context；child 仍有独立 session/history。 | `S-015`–`S-017` |
| V1 / V2 multi-agent | 两个分离 feature gate；本版本默认 V1 开、V2 关。V2 额外有 session-scoped mailbox/preemption 语义。 | V1 动态结果不能直接证明 V2 行为。 | `S-015`, `S-027`, `X-005` |
| Mailbox | V2 session 内暂存 child completion 和 inter-agent message、供 parent 当前或下一 follow-up 消费的队列。 | 不等于操作系统 mailbox，也不是自动终止 parent session。 | `S-027` |
| `ThreadStore` / `LiveThread` | storage-neutral durable thread API 与活动持久化 handle，负责 create/resume/append/flush 等操作。 | 不负责把 workspace 还原到历史版本。 | `D-004`, `S-018` |
| Rollout | 按顺序追加 session items 的 durable JSONL 历史，供 resume/replay。 | 不等于 OTel trace，也不保证每次文件副作用可逆。 | `S-019`, `X-006` |
| Product events | TUI、`exec --json`、app-server 可消费的 thread/turn/item/tool 状态事件。 | 不等于完整内部 causal trace。 | `D-003`, `S-023` |
| OTel | OpenTelemetry logs/traces/metrics 输出层，用 conversation/turn/tool/call 等字段做关联。 | 不等于 rollout；本轮 exporter 关闭，只有静态证据。 | `D-006`, `S-021` |
| Provider dialect | endpoint 对 message role、tool schema、stream event 等具体 wire format 的兼容集合。 | endpoint 支持基础 Responses SSE 不表示兼容 stock Codex 完整请求。 | `S-024`, `R-002`, `R-003` |
| HIR | Harness Intermediate Representation：把入口、loop、context、tool、安全、持久化等恢复成带类型 nodes/edges 的机器可读图。 | HIR 是证据约束下的分析模型，不是源码 AST 或运行时 trace。 | [`hir.json`](../hir.json) |
"""

REPORTS["index.md"] = """# OpenAI Codex 0.144.5 Harness 架构分析

> 冻结对象：`rust-v0.144.5`，peeled commit `87db9bc18ba5bc82c1cb4e4381b44f693ee35623`。本报告分析的是 Codex harness，而不是模型本身，也不把代码形状推断出的理由冒充作者意图。首次遇到内部类型、状态名或缩写时，可查[全局术语表](16-glossary.md)。

![Codex system overview](../diagrams/generated/codex-system-overview.png)

> 图 1（gpt-image-2 读者插图）：中央主轴是本轮恢复出的 canonical path；exec governance 位于主轴；持久化、subagent 与 telemetry 是有明确注入点的支路。图片不是架构真值，结构依据见 [HIR](../hir.json)、[claims](../evidence/claims.jsonl) 与[图像元数据](../diagrams/generated/metadata.json)。Evidence: `S-001`–`S-019`, `X-001`, `X-002`, `X-004`, `X-005`, `X-006`。

<!-- EXPLANATION:report-glossary -->
## 先读懂图 1：这些方框不是源码目录

图 1 把多个 Rust 类型聚合成读者可理解的运行职责。例如 `Thread / Session` 同时概括 thread manager、session 和 active persistence handle；`Tool runtime` 概括 tool spec、router 与 handler execution。它不是“一个方框对应一个文件”的包依赖图。

从左到右的实线是一次使用 `exec_command` 时的主路径：入口创建或恢复 thread，turn loop 组装请求，Responses API 返回模型输出，tool runtime 解释工具调用，`Exec Policy + Sandbox` 决定并约束副作用，最后才触达 workspace。下方红色回路表示 tool output 先进入 context，再触发下一次 model request；它不是 tool 直接调用模型。

图中常用词可以先这样理解：

| 术语 | 本报告中的准确含义 |
|---|---|
| thread | 可持久化、可 resume/fork 的会话身份和历史容器 |
| session | 当前进程中负责处理该 thread 的运行对象 |
| turn | 一次用户请求到 `TurnComplete/TurnAborted` 的调度单位；内部可有多次模型请求 |
| `StepContext` | 某次 sampling/tool invocation 固定使用的 model、cwd、policy、tools 等请求级快照 |
| context | 模型可见 history、动态 world state、当前输入和 tool specs 的组合 |
| rollout | 按顺序记录 session items 的 durable JSONL 事件历史 |
| registry | 当前进程已经有实现的工具集合 |
| exposure | 本次 model request 实际向模型公开的工具子集 |
| mailbox | V2 agent 之间暂存 completion/message 的 session-scoped 通信队列 |
| OTel | OpenTelemetry；独立于产品事件的 logs/traces/metrics 输出层 |

图片只承担“快速建立心智模型”；条件、例外和精确定义以相应章节、[HIR](../hir.json)和 evidence 为准。

## 一句话结论

Codex 0.144.5 不是“一个 while-loop 加几个工具”，而是一个以 **thread/session 为耐久边界、turn 为调度边界、StepContext 为请求边界、policy+sandbox 为副作用边界** 的分层 harness。核心复杂度集中在四处：增量 context/world state、动态 tool exposure、跨 turn/session 的恢复语义，以及 feature-gated 的多 agent 树。

## 五个最重要的发现

1. `run_turn` 是模型-工具闭环；`RegularTask` 负责 turn 生命周期和排队输入，不是第二套 loop。[S: `S-002`, `S-003`] [X: `X-002`]
2. context 不只是 message list：模型可见 history 与可差分 world state 分开维护，compaction 会替换信息而非仅截断字符串。[S: `S-005`–`S-007`]
3. registry 与 exposure 分离，当前 provider/config 决定模型看见哪些已注册能力；V1 multi-agent 的 namespace tool 就是一个条件 surface。[S: `S-009`] [X: `X-005`]
4. 对真正创建进程的 exec 路径，approval/exec policy 在 platform sandbox 前决策；`never` 对提权请求是前置硬拒绝。但 shell 中的 `apply_patch` 会先被识别并进入专用 patch safety、按路径 approval 与 sandbox runtime，不能把普通 exec 顺序泛化到所有工具输入。[S: `S-012`–`S-014`, `S-028`] [X: `X-004`, `X-007`]
5. thread durability 不是 UI 附件：LiveThread/ThreadStore/rollout 构成可恢复状态模型；跨进程 resume 已被本轮实验证实。[S: `S-018`, `S-019`] [X: `X-006`]

## 阅读路径

- [设计空间与 running example](00-design-space-and-running-example.md)
- [范围与方法](01-scope-and-method.md)
- [接口与生命周期](02-interfaces-lifecycle.md)
- [核心循环](03-core-loop.md)
- [上下文、记忆与压缩](04-context-memory-compaction.md)
- [模型、工具与扩展](05-models-tools-extensions.md)
- [权限、sandbox 与 workspace](06-permissions-sandbox-workspace.md)
- [Subagent 与 delegation](07-subagents-delegation.md)
- [Session、持久化与恢复](08-sessions-persistence-recovery.md)
- [可观测性](09-observability.md)
- [设计决策与权衡](10-design-decisions.md)
- [运行实验](11-runtime-experiments.md)
- [失败模式与开放问题](12-failure-modes-open-questions.md)
- [覆盖率与复现](13-coverage-reproducibility.md)
- [源码与 Claim 索引](14-source-claim-index.md)
- [全局术语表](16-glossary.md)
"""

def compile_bundle() -> None:
    manifest = {
        "analysis_status": "complete_with_known_gaps",
        "created_at": "2026-07-16T05:39:43.832311+00:00",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0",
        "target": {"repository_root": "/volume/med/work/users/mzchen/lab/codex", "commit": COMMIT, "tag": "rust-v0.144.5", "tag_object": TAG_OBJECT, "branch": None, "dirty": False, "changed_path_count": 0},
        "scope": {"entrypoints": ["cli", "tui", "exec", "app-server", "mcp-server"], "configurations": ["rust-v0.144.5", "default", "read-only/never", "V1 multi_agent condition"], "enabled_features": ["multi_agent only in X-SCENARIO-005", "exec_permission_approvals only in X-SCENARIO-004"], "disabled_features": ["memories", "multi_agent_v2", "OTel exporters"], "inaccessible_surfaces": ["production flags/frequency", "macOS/Windows sandbox runtime", "remote environments", "maintainer intent beyond repository docs"]},
        "execution": {"model_mode": "real SiFlow compatibility probes plus deterministic local Responses fixture", "model_provider": "siflow/qwen3.6-35ba3b and local scripted-responses", "isolation": "Disposable /tmp CODEX_HOME and workspace; target source checkout read-only", "network_policy": "User-authorized SiFlow only; deterministic fixtures on 127.0.0.1", "filesystem_policy": "read-only/never; explicit denied-side-effect hash check", "credential_policy": "Credentials loaded from existing Codex configuration; never persisted; request contents hashed", "runtime_versions": {"codex": "0.144.5 official musl binary", "python": "3.10", "rust": "not installed", "cargo": "not installed", "just": "not installed"}},
        "tooling": {"skill": "harness-analysis", "skill_commit": "7f2847d3cfa5d1964576ea99265ca83bbe234bf8", "skill_schema_version": "1.0", "image_skill": "gpt-image-2"},
    }
    write_json(ROOT / "manifest.json", manifest)
    write_jsonl(ROOT / "evidence" / "claims.jsonl", CLAIMS)
    write_jsonl(ROOT / "evidence" / "observations.jsonl", OBSERVATIONS)
    write_jsonl(ROOT / "evidence" / "conflicts.jsonl", [])
    write_json(ROOT / "hir.json", {"schema_version": "1.0", "repository": {"root": "/volume/med/work/users/mzchen/lab/codex", "commit": COMMIT, "entrypoints": ["cli", "tui", "exec", "app-server", "mcp-server"], "configurations": ["default", "read-only/never", "V1 multi_agent"]}, "nodes": NODES, "edges": EDGES})

    modules = {}
    for module_id, files in MODULE_FILES.items():
        modules[module_id] = {"status": "partial" if module_id in PARTIAL else "analyzed", "directories": sorted({str(Path(path).parent) for path in files}), "files": files, "symbols": [], "configurations": ["rust-v0.144.5", "default-source", "isolated-exec"], "scenarios": SCENARIOS_BY_MODULE[module_id], "excluded_surfaces": [], "unresolved": UNRESOLVED.get(module_id, []), "notes": "Pinned source inspected; runtime occurrence is scenario/configuration specific."}
    coverage = {"schema_version": "1.0", "global": {"entrypoints_examined": ["cli", "tui", "exec", "app-server", "mcp-server"], "configurations_tested": ["read-only/never", "multi_agent disabled", "multi_agent V1", "persistent resume"], "platforms_tested": ["Linux x86_64 official musl binary"], "providers_tested": ["SiFlow qwen3.6-35ba3b (compatibility failed)", "local deterministic Responses SSE"], "inaccessible_surfaces": ["macOS/Windows runtime", "production configuration", "remote execution", "maintainer private rationale"], "search_limits": {"max_files": 20000, "max_file_size": 1000000, "max_hits_per_category": 160, "file_limit_reached": False}, "unresolved_high_value_questions": ["compaction and corruption fault injection", "MCP/dynamic tool permission coverage", "V2 subagent runtime", "OTel causal alignment"]}, "modules": modules}
    write_json(ROOT / "evidence" / "coverage.json", coverage)
    write_json(ROOT / "scenarios" / "catalog.json", SCENARIOS)
    write_json(ROOT / "questions.json", {"schema_version": "1.0", "questions": [
        {"id": "Q-001", "priority": "high", "status": "open", "question": "role/namespace translation 后，真实 SiFlow tool loop 与 deterministic trace 是否一致？", "next_experiment": "部署透明 adapter，分别保留 stock/adapted request hashes。"},
        {"id": "Q-002", "priority": "high", "status": "open", "question": "MCP、dynamic、hosted tools 是否共享 exec policy/sandbox，哪些 handler 有独立副作用边界？", "next_experiment": "为每类 tool 构造 deny/side-effect matrix。"},
        {"id": "Q-003", "priority": "high", "status": "open", "question": "pre-turn/mid-turn/remote/local compaction 的 replacement 与 persistence 次序是什么？", "next_experiment": "oversized scripted output + token snapshots + resume。"},
        {"id": "Q-004", "priority": "medium", "status": "open", "question": "rollout 截断、flush failure 与 schema drift 时 resume 的失败模型是什么？", "next_experiment": "复制合成 rollout 并逐段 corruption。"},
        {"id": "Q-005", "priority": "medium", "status": "open", "question": "V2 mailbox preemption 和 child cancellation 如何与父 turn events 对齐？", "next_experiment": "启用 V2 scripted child hang/cancel scenario。"},
    ]})

    write_jsonl(ROOT / "traces" / "normalized" / "R-002-siflow-namespace.normalized.jsonl", [{"scenario": "R-SCENARIO-002", "event": "thread.started"}, {"scenario": "R-SCENARIO-002", "event": "turn.started"}, {"scenario": "R-SCENARIO-002", "event": "provider.rejected", "status": 400, "category": "unsupported_namespace_tool_schema", "request_body_retained": False}, {"scenario": "R-SCENARIO-002", "event": "turn.failed", "side_effects": "none_observed"}])
    write_jsonl(ROOT / "traces" / "normalized" / "X-001-text-stop.normalized.jsonl", [{"scenario": "X-SCENARIO-001", "event": "thread.started"}, {"scenario": "X-SCENARIO-001", "event": "turn.started"}, {"scenario": "X-SCENARIO-001", "event": "model.request", "input_count": 3}, {"scenario": "X-SCENARIO-001", "event": "assistant.message", "text_token": "SCRIPTED_OK"}, {"scenario": "X-SCENARIO-001", "event": "turn.completed"}])
    write_jsonl(ROOT / "traces" / "normalized" / "X-003-unknown-tool.normalized.jsonl", [{"scenario": "X-SCENARIO-003", "event": "model.function_call", "tool": "definitely_not_a_tool"}, {"scenario": "X-SCENARIO-003", "event": "tool.failed", "category": "unsupported_call"}, {"scenario": "X-SCENARIO-003", "event": "model.request", "contains_tool_output": True}, {"scenario": "X-SCENARIO-003", "event": "turn.completed"}])
    write_jsonl(ROOT / "traces" / "normalized" / "X-004-denied-escalation.normalized.jsonl", [{"scenario": "X-SCENARIO-004", "event": "model.function_call", "tool": "exec_command", "requested_permission": "require_escalated", "arguments_retained": False}, {"scenario": "X-SCENARIO-004", "event": "policy.denied", "approval_policy": "never"}, {"scenario": "X-SCENARIO-004", "event": "model.request", "contains_tool_output": True}, {"scenario": "X-SCENARIO-004", "event": "turn.completed"}])
    write_jsonl(ROOT / "traces" / "normalized" / "X-007-side-effect-check.normalized.jsonl", [{"scenario": "X-SCENARIO-004", "event": "filesystem.baseline", "files": ["FACTS.txt"], "facts_sha256": "27799224908738a2dacbb3a9de16743054adac7ef6c817061a832bd679b568ed"}, {"scenario": "X-SCENARIO-004", "event": "filesystem.after", "files": ["FACTS.txt"], "facts_sha256": "27799224908738a2dacbb3a9de16743054adac7ef6c817061a832bd679b568ed", "forbidden_marker_present": False}])

    for filename, body in REPORTS.items():
        write_text(ROOT / "report" / filename, body)
    augment_structured_evidence()
    enrich_reports()


if __name__ == "__main__":
    compile_bundle()
