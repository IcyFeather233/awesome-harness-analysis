#!/usr/bin/env python3
"""Write curated story specs and gpt-image-2 prompts for the Codex report."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
GENERATED = ROOT / "diagrams" / "generated"
PROMPTS = GENERATED / "prompts"


COMMON_STYLE = """
Style and visual hierarchy:
- Clean academic systems infographic with friendly hand-sketched geometry, bold dark-gray outlines, flat pastel fills, and large modern sans-serif labels.
- White background, generous whitespace, recognizable icons, thick arrows, and one unmistakable reading direction.
- Use coral for orchestration, blue for model/capabilities, green for durable state, amber for policy, red only for failure, and neutral gray for external boundaries.
- Similar visual language to a polished modern systems-research figure, but do not copy any existing figure or artwork.

Global constraints:
- Use only the exact text listed in the prompt. No title, caption, legend, evidence IDs, source paths, paragraphs, logos, or watermark.
- No gradients, shadows, 3D, photorealism, tiny print, nested cards, crossing arrows, repeated components, or decorative background.
- Keep every label horizontal and readable at 1000 pixels report width.
"""


PROMPT_TEXT = {
    "01-system-overview-v3.txt": """
Use case: infographic-diagram
Asset type: reader-facing software architecture illustration
Primary request: Explain Codex 0.144.5 as one obvious runtime path with governance, state, delegation, and telemetry as secondary branches. The image must be understandable in five seconds.

Architecture facts and layout:
- Draw one straight solid main path across the center with exactly seven large stages: "Surfaces" -> "Thread / Session" -> "Turn loop" -> "Responses API" -> "Tool runtime" -> "Exec Policy + Sandbox" -> "Workspace".
- Draw a two-segment feedback path: "Tool runtime" -> "Context + World state" -> "Turn loop". Put "tool output" only on the first segment. Both arrowheads must point away from Tool runtime and toward Turn loop. Never draw Context + World state pointing into Tool runtime.
- Place "Context + World state" directly below the gap between "Turn loop" and "Responses API", connected into both.
- Place "Rollout JSONL" below "Thread / Session" with a two-way durable-state arrow.
- Keep "Exec Policy + Sandbox" directly on the main path between "Tool runtime" and "Workspace". Never draw a direct Tool runtime to Workspace arrow.
- Place "Child Session" above "Thread / Session" as a dashed conditional branch with badge "V1 / V2". Connect it to the same "Workspace" with a thin shared-state arrow.
- Place "Events + OTel" below the main path as a thin observation rail, not a control-flow stage.
- Use terminal, session, circular loop, cloud/model, wrench, folder, shield, database, child-agent, and pulse icons.

Text (verbatim, case-sensitive):
"Surfaces"
"Thread / Session"
"Turn loop"
"Responses API"
"Tool runtime"
"Workspace"
"tool output"
"Context + World state"
"Rollout JSONL"
"Exec Policy + Sandbox"
"Child Session"
"V1 / V2"
"Events + OTel"

Do not imply that every turn spawns a child or that context, policy, and persistence are sequential main-loop stages.
""" + COMMON_STYLE,
    "02-observed-turn.txt": """
Use case: infographic-diagram
Asset type: reader-facing runtime sequence illustration
Primary request: Show the exact deterministic two-request Codex read-tool turn and why the second request exists.

Architecture facts and layout:
- Use a vertical composition with a start row, two large iteration bands, and one ending row.
- Start with "User request".
- Band "Request 1" contains: "Build prompt" -> "Responses" -> "exec_command" -> "Read FACTS.txt".
- A thick curved arrow labeled "function_call_output" carries the tool result into the second band.
- Band "Request 2" contains: "Updated history" -> "Responses" -> "HXA-1445".
- End with "Turn complete".
- Put a slim side rail labeled "RegularTask" around the full turn and a smaller inner rail labeled "run_turn" around both requests.
- Do not show permission, compaction, write, subagent, retry, or resume; none occurred in this trace.

Text (verbatim, case-sensitive):
"User request"
"Request 1"
"Build prompt"
"Responses"
"exec_command"
"Read FACTS.txt"
"function_call_output"
"Request 2"
"Updated history"
"HXA-1445"
"Turn complete"
"RegularTask"
"run_turn"
""" + COMMON_STYLE,
    "03-context-lifecycle.txt": """
Use case: infographic-diagram
Asset type: reader-facing context data-flow illustration
Primary request: Explain how Codex constructs model context while keeping durable history, dynamic world state, tool exposure, and compaction distinct.

Architecture facts and layout:
- Draw five source icons on the left: "Base instructions", "History", "World state diff", "User input", and "Visible tool specs".
- All five arrows merge into one large center component "Context Manager". No source may bypass it directly to the model.
- Continue right through "StepContext + Prompt" -> "Responses API".
- Draw a solid feedback arrow from "Tool output" below the model back into "History".
- Draw a dashed conditional loop from "Token limit" -> "Compaction" -> "History replacement" -> "Context Manager" with badge "WHEN NEEDED".
- Place "Long-term memory" as a muted dashed optional source into "Context Manager" with badge "EXPERIMENTAL".
- Use document stack, timeline, world/globe, user message, toolbox, funnel, token gauge, summary, memory, and cloud icons.

Text (verbatim, case-sensitive):
"Base instructions"
"History"
"World state diff"
"User input"
"Visible tool specs"
"Context Manager"
"StepContext + Prompt"
"Responses API"
"Tool output"
"Token limit"
"Compaction"
"History replacement"
"WHEN NEEDED"
"Long-term memory"
"EXPERIMENTAL"
""" + COMMON_STYLE,
    "04-tool-extension-surface.txt": """
Use case: infographic-diagram
Asset type: reader-facing capability pipeline illustration
Primary request: Show that tool registration, model exposure, routing, execution, and result feedback are separate control points.

Architecture facts and layout:
- Use four clear columns from left to right.
- Column 1 "Sources" contains exactly: "Built-ins", "MCP", "Extensions", "Dynamic tools", "Multi-agent".
- All source arrows enter "Tool registry" in column 2.
- Continue through a narrow filter "Per-turn exposure" with badge "VISIBLE NOW" into "Responses API".
- A model tool-call arrow goes to column 3 "Tool Router", then "Pre-tool hooks".
- Continue to column 4 "Handler runtime", then return through "Tool result" -> "Context".
- Draw a small lock icon on "Handler runtime" with labels "parallel read" and "exclusive write".
- Use dashed arrows for MCP, Extensions, Dynamic tools, and Multi-agent because they are conditional in the tested configuration.

Text (verbatim, case-sensitive):
"Sources"
"Built-ins"
"MCP"
"Extensions"
"Dynamic tools"
"Multi-agent"
"Tool registry"
"Per-turn exposure"
"VISIBLE NOW"
"Responses API"
"Tool Router"
"Pre-tool hooks"
"Handler runtime"
"Tool result"
"Context"
"parallel read"
"exclusive write"
""" + COMMON_STYLE,
    "05-permission-pipeline.txt": """
Use case: infographic-diagram
Asset type: reader-facing security boundary illustration
Primary request: Explain the exact Codex command side-effect path and the experimentally observed Never-policy denial.

Architecture facts and layout:
- Draw one dominant horizontal allowed path: "Model tool call" -> "Exec Policy" -> "Approval" -> "Platform Sandbox" -> "Process" -> "Workspace".
- Put "Rules + mode" above "Exec Policy" with an input arrow.
- Put "Session cache" above "Approval" with a two-way arrow.
- Put "Filesystem profile" and "Network profile" above "Platform Sandbox" as policy inputs.
- From "Exec Policy", draw a prominent red branch downward: "NEVER + escalation" -> "Denied before process" -> "Tool error to model". Add badge "OBSERVED".
- The red branch must end before "Platform Sandbox" and "Process".
- Use shield, decision split, user approval, OS boundary, process, folder, and blocked-command icons.

Text (verbatim, case-sensitive):
"Model tool call"
"Exec Policy"
"Approval"
"Platform Sandbox"
"Process"
"Workspace"
"Rules + mode"
"Session cache"
"Filesystem profile"
"Network profile"
"NEVER + escalation"
"Denied before process"
"Tool error to model"
"OBSERVED"

Do not draw the observed denied request as entering the sandbox or process. Do not imply that approval alone is the sandbox.
""" + COMMON_STYLE,
    "06-subagent-topology.txt": """
Use case: infographic-diagram
Asset type: reader-facing multi-agent topology illustration
Primary request: Explain V1 child-session isolation and sharing, while keeping V2 visibly separate and untested.

Architecture facts and layout:
- Place a large "Root Session" on the left, governed by a top rail "AgentControl".
- A solid arrow labeled "spawn_agent" goes to "Child Session" on the right. Add badge "V1 OBSERVED".
- Inside or immediately beside the child, show three distinct owned items: "Own thread", "Own context", "Own history".
- Between root and child, show inherited configuration as a thin top arrow labeled "model + policy + cwd".
- At the bottom, place one shared "Workspace" connected from both root and child. Label the shared connection "shared files".
- Place a hard stop after child spawn labeled "max depth 1"; do not draw grandchildren.
- Place "V2 mailbox" as a muted dashed branch below AgentControl with badge "NOT TESTED"; do not merge it into the V1 observed path.
- Use root-agent, child-agent, thread, message stack, history, folder, governance rail, mailbox, and stop icons.

Text (verbatim, case-sensitive):
"Root Session"
"AgentControl"
"spawn_agent"
"Child Session"
"V1 OBSERVED"
"Own thread"
"Own context"
"Own history"
"model + policy + cwd"
"Workspace"
"shared files"
"max depth 1"
"V2 mailbox"
"NOT TESTED"
""" + COMMON_STYLE,
    "07-persistence-lifecycle.txt": """
Use case: infographic-diagram
Asset type: reader-facing session persistence illustration
Primary request: Explain what becomes durable, how a new process resumes it, and what is not rolled back.

Architecture facts and layout:
- Draw a left-to-right main path: "Turn items" -> "LiveThread" -> "ThreadStore" -> "Rollout JSONL" -> "New process" -> "Resume same thread" -> "Restored history".
- Put a green badge "OBSERVED" above the path from Rollout JSONL through Restored history.
- Draw a small flush arrow from "Turn complete" into "Rollout JSONL".
- Below the main path, draw "Workspace" as a parallel state lane with label "not rolled back". It must not pass through Rollout JSONL.
- Above "Restored history", draw a dashed optional branch "Compaction summary" labeled "CONDITIONAL".
- Add a red warning side branch from "Rollout JSONL" to "Corruption / partial write" with badge "NOT TESTED".
- Use event stream, live session, database adapter, JSONL document, new process, restore arrow, history stack, folder, summary, and warning icons.

Text (verbatim, case-sensitive):
"Turn items"
"LiveThread"
"ThreadStore"
"Rollout JSONL"
"New process"
"Resume same thread"
"Restored history"
"OBSERVED"
"Turn complete"
"Workspace"
"not rolled back"
"Compaction summary"
"CONDITIONAL"
"Corruption / partial write"
"NOT TESTED"
""" + COMMON_STYLE,
    "08-design-space.txt": """
Use case: infographic-diagram
Asset type: reader-facing architecture decision map
Primary request: Compare four recurring Codex harness design questions as aligned rows from constraint to recovered mechanism to analyst-synthesized tradeoff.

Architecture facts and layout:
- Create exactly three vertical columns labeled "Constraint", "Recovered mechanism", and "Analyst synthesis".
- Create exactly four aligned rows.
- Row 1: "Resume across processes" -> "LiveThread + Rollout" -> "Flush and corruption boundary".
- Row 2: "Incremental context" -> "History + World state diff" -> "Lower repetition, more state sync".
- Row 3: "Conditional capabilities" -> "Registry + Exposure" -> "Provider and mode matrix".
- Row 4: "Controlled side effects" -> "Exec Policy + Sandbox" -> "Cross-platform verification".
- Use solid arrows from Constraint to Recovered mechanism. Use dotted amber arrows from Recovered mechanism to Analyst synthesis.
- Put a small badge "INFERENCE" at the top of the third column.
- Use resume, context layers, toolbox/filter, shield/sandbox, tradeoff scale, and verification icons.

Text (verbatim, case-sensitive):
"Constraint"
"Recovered mechanism"
"Analyst synthesis"
"Resume across processes"
"LiveThread + Rollout"
"Flush and corruption boundary"
"Incremental context"
"History + World state diff"
"Lower repetition, more state sync"
"Conditional capabilities"
"Registry + Exposure"
"Provider and mode matrix"
"Controlled side effects"
"Exec Policy + Sandbox"
"Cross-platform verification"
"INFERENCE"

Do not imply that the third-column tradeoffs are documented author intent.
""" + COMMON_STYLE,
}


FIGURE_JOBS = [
    ("01-system-overview-v3.txt", "codex-system-overview.png", "1536x1024"),
    ("02-observed-turn.txt", "codex-observed-turn.png", "1024x1536"),
    ("03-context-lifecycle.txt", "codex-context-lifecycle.png", "1536x1024"),
    ("04-tool-extension-surface.txt", "codex-tool-extension-surface.png", "1536x1024"),
    ("05-permission-pipeline.txt", "codex-permission-pipeline.png", "1536x1024"),
    ("06-subagent-topology.txt", "codex-subagent-topology.png", "1536x1024"),
    ("07-persistence-lifecycle.txt", "codex-persistence-lifecycle.png", "1536x1024"),
    ("08-design-space.txt", "codex-design-space.png", "2048x1152"),
]


def n(node_id: str, label: str, hir_ids: list[str], claims: list[str], evidence: list[str], x: int, y: int, tone: str = "core") -> dict:
    return {"id": node_id, "kind": "hir", "hir_ids": hir_ids, "claim_ids": claims, "evidence_ids": evidence, "label": label, "subtitle": "", "tone": tone, "x": x, "y": y, "width": 180, "height": 76}


def e(edge_id: str, source: str, target: str, evidence: list[str], points: list[list[int]], status: str = "static") -> dict:
    return {"id": edge_id, "source": source, "target": target, "points": points, "label": "", "status": status, "claim_ids": [], "evidence_ids": evidence}


STORIES = {
    "schema_version": "1.0",
    "figures": [
        {"id": "codex-system-overview", "title": "Codex System Overview", "description": "Canonical runtime path and secondary boundaries.", "width": 1400, "height": 760, "nodes": [
            n("surface", "Surfaces", ["N-CLI", "N-AppServer", "N-MCPServer"], ["C-001"], ["S-001"], 40, 300, "interface"),
            n("session", "Thread / Session", ["N-ThreadManager", "N-LiveThread"], ["C-011"], ["S-018"], 250, 300, "state"),
            n("loop", "Turn loop", ["N-RegularTask", "N-TurnLoop"], ["C-002"], ["S-002", "S-003", "X-002"], 460, 300),
            n("model", "Responses API", ["N-ModelSession", "N-Responses"], ["C-006"], ["S-008", "S-024"], 670, 300, "model"),
            n("tools", "Tool runtime", ["N-SpecPlan", "N-ToolRouter", "N-ToolRuntime"], ["C-007", "C-008"], ["S-009", "S-010", "S-025"], 880, 300, "capability"),
            n("workspace", "Workspace", ["N-Workspace"], ["C-009"], ["X-007"], 1090, 300, "execution"),
            n("policy", "Exec Policy + Sandbox", ["N-ExecPolicy", "N-Approval", "N-Sandbox"], ["C-009", "C-010"], ["S-012", "S-014"], 900, 100, "policy"),
            n("rollout", "Rollout JSONL", ["N-Rollout"], ["C-011"], ["S-019", "X-006"], 250, 520, "state"),
            n("child", "Child Session", ["N-Subagent"], ["C-012"], ["S-016", "X-005"], 460, 100, "muted"),
        ], "edges": [
            e("s1", "surface", "session", ["S-001"], [[220,338],[250,338]]), e("s2", "session", "loop", ["S-002"], [[430,338],[460,338]]), e("s3", "loop", "model", ["X-002"], [[640,338],[670,338]], "experimental"), e("s4", "model", "tools", ["X-002"], [[850,338],[880,338]], "experimental"), e("s5", "tools", "workspace", ["S-014"], [[1060,338],[1090,338]]), e("s6", "policy", "tools", ["S-012"], [[990,176],[970,300]]), e("s7", "session", "rollout", ["X-006"], [[340,376],[340,520]], "experimental"), e("s8", "session", "child", ["X-005"], [[340,300],[550,176]], "experimental")
        ]},
        {"id": "codex-observed-turn", "title": "Observed Read Tool Turn", "description": "Two deterministic Responses requests around one read tool call.", "width": 900, "height": 1200, "nodes": [n("loop2", "Turn loop", ["N-TurnLoop"], ["C-002"], ["X-002"], 350, 80), n("ctx2", "Context", ["N-Context"], ["C-019"], ["X-002"], 100, 300, "state"), n("model2", "Responses", ["N-Responses"], ["C-019"], ["X-002"], 350, 300, "model"), n("tool2", "exec_command", ["N-ToolRuntime"], ["C-019"], ["X-002"], 600, 300, "capability"), n("history2", "Updated history", ["N-Context"], ["C-019"], ["X-002"], 100, 650, "state"), n("final2", "Final answer", ["N-Exit"], ["C-019"], ["X-002"], 600, 650, "observability")], "edges": [e("t1","ctx2","model2",["X-002"],[[280,338],[350,338]],"experimental"),e("t2","model2","tool2",["X-002"],[[530,338],[600,338]],"experimental"),e("t3","tool2","history2",["X-002"],[[690,376],[690,520],[190,520],[190,650]],"experimental"),e("t4","history2","model2",["X-002"],[[280,688],[440,688],[440,376]],"experimental"),e("t5","model2","final2",["X-002"],[[530,338],[760,338],[760,688],[780,688]],"experimental")]},
        {"id": "codex-context-lifecycle", "title": "Context Lifecycle", "description": "Context sources, transformations and conditional compaction.", "width": 1400, "height": 760, "nodes": [n("hist3","History",["N-Context"],["C-003"],["S-005"],60,200,"state"),n("world3","World state",["N-WorldState"],["C-004"],["S-006"],60,380,"state"),n("spec3","Tool specs",["N-SpecPlan"],["C-007"],["S-009"],60,560,"capability"),n("ctx3","Context Manager",["N-Context"],["C-003"],["S-005"],420,350,"core"),n("model3","Responses",["N-Responses"],["C-006"],["S-024"],800,350,"model"),n("compact3","Compactor",["N-Compactor"],["C-005"],["S-007"],420,80,"muted"),n("memory3","Long-term memory",["N-Memory"],["C-014"],["S-020"],800,80,"muted")],"edges":[e("c1","hist3","ctx3",["S-005"],[[240,238],[420,388]]),e("c2","world3","ctx3",["S-006"],[[240,418],[420,388]]),e("c3","spec3","ctx3",["S-009"],[[240,598],[420,388]]),e("c4","ctx3","model3",["S-004"],[[600,388],[800,388]]),e("c5","compact3","ctx3",["S-007"],[[510,156],[510,350]]),e("c6","memory3","ctx3",["S-020"],[[800,118],[600,350]])]},
        {"id": "codex-tool-surface", "title": "Tool And Extension Surface", "description": "Registration, exposure, routing and feedback.", "width": 1400, "height": 720, "nodes": [n("mcp4","MCP / Dynamic",["N-MCP"],["C-007"],["S-026"],50,150,"muted"),n("reg4","Registry",["N-SpecPlan"],["C-007"],["S-009"],300,300,"capability"),n("model4","Responses",["N-Responses"],["C-007"],["S-004"],550,300,"model"),n("router4","Router",["N-ToolRouter"],["C-008"],["S-010"],800,300,"core"),n("hook4","Hooks",["N-Hooks"],["C-008"],["S-011"],800,100,"policy"),n("runtime4","Runtime",["N-ToolRuntime"],["C-008","C-023"],["S-025"],1050,300,"execution"),n("ctx4","Context",["N-Context"],["C-019"],["X-002"],550,550,"state")],"edges":[e("u1","mcp4","reg4",["S-026"],[[230,188],[390,300]]),e("u2","reg4","model4",["S-009"],[[480,338],[550,338]]),e("u3","model4","router4",["S-010"],[[730,338],[800,338]]),e("u4","hook4","runtime4",["S-011"],[[980,138],[1140,300]]),e("u5","router4","runtime4",["S-025"],[[980,338],[1050,338]]),e("u6","runtime4","ctx4",["X-002"],[[1140,376],[1140,588],[730,588]],"experimental")]},
        {"id": "codex-permission-pipeline", "title": "Permission Pipeline", "description": "Policy decision and platform sandbox before side effects.", "width": 1400, "height": 720, "nodes": [n("call5","Tool call",["N-ToolRuntime"],["C-009"],["X-004"],50,300,"capability"),n("policy5","Exec Policy",["N-ExecPolicy"],["C-009"],["S-012","X-004"],300,300,"policy"),n("approval5","Approval",["N-Approval"],["C-009"],["S-013"],550,300,"policy"),n("sandbox5","Sandbox",["N-Sandbox"],["C-010"],["S-014"],800,300,"policy"),n("process5","Process",["N-ExecBackend"],["C-010"],["S-014"],1050,300,"execution"),n("deny5","Denied",["N-ToolRuntime"],["C-020"],["X-004","X-007"],550,550,"risk")],"edges":[e("p1","call5","policy5",["S-012"],[[230,338],[300,338]]),e("p2","policy5","approval5",["S-013"],[[480,338],[550,338]]),e("p3","approval5","sandbox5",["S-014"],[[730,338],[800,338]]),e("p4","sandbox5","process5",["S-014"],[[980,338],[1050,338]]),e("p5","policy5","deny5",["X-004"],[[390,376],[640,550]],"experimental")]},
        {"id": "codex-subagent-topology", "title": "Subagent Topology", "description": "Independent child state, inherited policy, shared workspace.", "width": 1400, "height": 760, "nodes": [n("root6","Root Session",["N-ThreadManager"],["C-012"],["X-005"],100,260,"core"),n("control6","AgentControl",["N-AgentControl"],["C-012"],["S-015"],450,80,"policy"),n("child6","Child Session",["N-Subagent"],["C-012"],["S-016","X-005"],700,260,"core"),n("ctx6","Child context",["N-Context"],["C-022"],["X-005"],1000,180,"state"),n("workspace6","Shared workspace",["N-Workspace"],["C-012"],["S-015"],450,560,"execution"),n("v26","V2 mailbox",["N-AgentControl"],["C-013"],["S-015"],1000,500,"muted")],"edges":[e("a1","control6","root6",["S-015"],[[540,156],[190,260]]),e("a2","root6","child6",["X-005"],[[280,298],[700,298]],"experimental"),e("a3","child6","ctx6",["X-005"],[[880,298],[1000,218]],"experimental"),e("a4","root6","workspace6",["S-015"],[[190,336],[540,560]]),e("a5","child6","workspace6",["S-016"],[[790,336],[540,560]]),e("a6","control6","v26",["S-015"],[[630,118],[1090,500]])]},
        {"id": "codex-persistence-lifecycle", "title": "Persistence Lifecycle", "description": "Append, flush and cross-process resume.", "width": 1400, "height": 720, "nodes": [n("turn7","Turn items",["N-TurnLoop"],["C-011"],["S-003"],50,300,"core"),n("live7","LiveThread",["N-LiveThread"],["C-011"],["S-018"],300,300,"state"),n("rollout7","Rollout JSONL",["N-Rollout"],["C-011"],["S-019","X-006"],550,300,"state"),n("process7","New process",["N-CLI"],["C-021"],["X-006"],800,300,"interface"),n("restore7","Restored history",["N-Context"],["C-021"],["X-006"],1050,300,"state"),n("workspace7","Workspace",["N-Workspace"],["C-021"],["X-007"],550,550,"execution")],"edges":[e("r1","turn7","live7",["S-018"],[[230,338],[300,338]]),e("r2","live7","rollout7",["S-019"],[[480,338],[550,338]]),e("r3","rollout7","process7",["X-006"],[[730,338],[800,338]],"experimental"),e("r4","process7","restore7",["X-006"],[[980,338],[1050,338]],"experimental")]},
        {"id": "codex-design-space", "title": "Design Space", "description": "Constraints, mechanisms and analyst synthesis.", "width": 1400, "height": 780, "nodes": [n("d1","Durable thread",["N-LiveThread","N-Rollout"],["C-011"],["S-018","S-019"],100,100,"state"),n("d2","Incremental context",["N-Context","N-WorldState"],["C-004"],["S-005","S-006"],100,280,"core"),n("d3","Conditional tools",["N-SpecPlan"],["C-007"],["S-009"],100,460,"capability"),n("d4","Layered safety",["N-ExecPolicy","N-Sandbox"],["C-010"],["S-012","S-014"],100,640,"policy")],"edges":[]},
    ],
}


def main() -> None:
    PROMPTS.mkdir(parents=True, exist_ok=True)
    for name, prompt in PROMPT_TEXT.items():
        (PROMPTS / name).write_text(prompt.strip() + "\n", encoding="utf-8")
    with (GENERATED / "jobs.jsonl").open("w", encoding="utf-8") as handle:
        for prompt_file, output, size in FIGURE_JOBS:
            handle.write(json.dumps({"prompt": (PROMPTS / prompt_file).read_text(encoding="utf-8"), "out": output, "size": size, "quality": "high"}) + "\n")
    (ROOT / "diagrams" / "story-specs.json").write_text(json.dumps(STORIES, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
