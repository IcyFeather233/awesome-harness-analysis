#!/usr/bin/env python3
"""Apply semantic-review corrections to selected narrative story specs."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "diagrams" / "story-specs.json"


def node(node_id: str, label: str, hir_ids: list[str], claims: list[str], evidence: list[str], x: int, y: int, tone: str) -> dict:
    return {"id": node_id, "kind": "hir", "hir_ids": hir_ids, "claim_ids": claims, "evidence_ids": evidence, "label": label, "subtitle": "", "tone": tone, "x": x, "y": y, "width": 170, "height": 72}


def edge(edge_id: str, source: str, target: str, evidence: list[str], points: list[list[int]], status: str = "static", label: str = "") -> dict:
    return {"id": edge_id, "source": source, "target": target, "points": points, "label": label, "status": status, "claim_ids": [], "evidence_ids": evidence}


def main() -> None:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    figures = {figure["id"]: figure for figure in data["figures"]}

    overview = figures["codex-system-overview"]
    overview["width"] = 1600
    overview["height"] = 820
    overview["nodes"] = [
        node("surface", "Surfaces", ["N-CLI", "N-AppServer", "N-MCPServer"], ["C-001"], ["S-001"], 20, 300, "interface"),
        node("session", "Thread / Session", ["N-ThreadManager", "N-LiveThread"], ["C-011"], ["S-018"], 220, 300, "state"),
        node("loop", "Turn loop", ["N-RegularTask", "N-TurnLoop"], ["C-002"], ["S-002", "S-003", "X-002"], 420, 300, "core"),
        node("model", "Responses API", ["N-ModelSession", "N-Responses"], ["C-006"], ["S-008", "S-024"], 620, 300, "model"),
        node("tools", "Tool runtime", ["N-SpecPlan", "N-ToolRouter", "N-ToolRuntime"], ["C-007", "C-008"], ["S-009", "S-010", "S-025"], 820, 300, "capability"),
        node("policy", "Exec Policy + Sandbox", ["N-ExecPolicy", "N-Approval", "N-Sandbox"], ["C-009", "C-010"], ["S-012", "S-014"], 1020, 300, "policy"),
        node("workspace", "Workspace", ["N-Workspace"], ["C-009"], ["X-007"], 1220, 300, "execution"),
        node("context", "Context + World state", ["N-Context", "N-WorldState"], ["C-003", "C-004"], ["S-005", "S-006", "X-002"], 620, 520, "state"),
        node("rollout", "Rollout JSONL", ["N-Rollout"], ["C-011"], ["S-019", "X-006"], 220, 520, "state"),
        node("child", "Child Session", ["N-Subagent"], ["C-012"], ["S-016", "X-005"], 220, 80, "muted"),
        node("telemetry", "Events + OTel", ["N-Telemetry"], ["C-016"], ["S-021"], 820, 700, "observability"),
    ]
    overview["edges"] = [
        edge("o1", "surface", "session", ["S-001"], [[190,336], [220,336]]),
        edge("o2", "session", "loop", ["S-002"], [[390,336], [420,336]]),
        edge("o3", "loop", "model", ["X-002"], [[590,336], [620,336]], "experimental"),
        edge("o4", "model", "tools", ["X-002"], [[790,336], [820,336]], "experimental"),
        edge("o5", "tools", "policy", ["S-012"], [[990,336], [1020,336]]),
        edge("o6", "policy", "workspace", ["S-014"], [[1190,336], [1220,336]]),
        edge("o7", "tools", "context", ["X-002"], [[905,372], [905,556], [790,556]], "experimental", "tool output"),
        edge("o8", "context", "loop", ["X-002"], [[620,556], [505,372]], "experimental"),
        edge("o9", "context", "model", ["S-004"], [[705,520], [705,372]]),
        edge("o10", "session", "rollout", ["X-006"], [[305,372], [305,520]], "experimental"),
        edge("o11", "session", "child", ["X-005"], [[305,300], [305,152]], "experimental"),
        edge("o12", "child", "workspace", ["S-015"], [[390,116], [1305,116], [1305,300]]),
        edge("o13", "loop", "telemetry", ["S-021"], [[505,372], [905,700]]),
    ]

    context = figures["codex-context-lifecycle"]
    context["nodes"].append(node("runtime3", "Tool runtime", ["N-ToolRuntime"], ["C-019"], ["X-002"], 1040, 520, "execution"))
    context["edges"].extend([
        edge("c7", "model3", "runtime3", ["X-002"], [[980,388], [1125,520]], "experimental", "tool call"),
        edge("c8", "runtime3", "hist3", ["X-002"], [[1040,556], [150,556], [150,276]], "experimental", "tool output"),
    ])

    tools = figures["codex-tool-surface"]
    tools["edges"] = [
        edge("u1", "mcp4", "reg4", ["S-026"], [[230,188], [390,300]]),
        edge("u2", "reg4", "model4", ["S-009"], [[480,338], [550,338]]),
        edge("u3", "model4", "router4", ["S-010", "X-002"], [[730,338], [800,338]], "experimental", "tool call"),
        edge("u4", "router4", "hook4", ["S-011"], [[890,300], [890,176]]),
        edge("u5", "hook4", "runtime4", ["S-011"], [[980,138], [1140,300]]),
        edge("u6", "runtime4", "ctx4", ["X-002"], [[1140,376], [1140,588], [730,588]], "experimental", "tool result"),
    ]

    permission = figures["codex-permission-pipeline"]
    for existing in permission["nodes"]:
        if existing["id"] == "approval5":
            existing["label"] = "User Approval"
    permission["edges"] = [
        edge("p1", "call5", "policy5", ["S-012"], [[230,338], [300,338]]),
        edge("p2", "policy5", "sandbox5", ["S-012", "S-014"], [[480,320], [800,320]], label="allow"),
        edge("p3", "policy5", "approval5", ["S-012", "S-013"], [[480,350], [550,350]], label="ask"),
        edge("p4", "approval5", "sandbox5", ["S-013", "S-014"], [[730,350], [800,350]]),
        edge("p5", "sandbox5", "process5", ["S-014"], [[980,338], [1050,338]]),
        edge("p6", "policy5", "deny5", ["X-004"], [[390,376], [640,550]], "experimental", "deny"),
    ]

    PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
