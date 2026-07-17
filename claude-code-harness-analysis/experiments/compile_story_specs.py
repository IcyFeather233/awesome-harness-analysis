#!/usr/bin/env python3
"""Build curated reader-facing figure specifications from the HIR."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
W, H = 1600, 860


def n(node_id, label, hir_ids, claims, evidence, x, y, tone, subtitle="", badge=None, width=180, height=78):
    value = {
        "id": node_id, "kind": "hir", "hir_ids": hir_ids,
        "claim_ids": claims, "evidence_ids": evidence,
        "label": label, "subtitle": subtitle, "tone": tone,
        "x": x, "y": y, "width": width, "height": height,
    }
    if badge:
        value["badge"] = badge
    return value


def c(node_id, label, claims, evidence, x, y, tone, subtitle="", badge=None, width=180, height=78):
    value = {
        "id": node_id, "kind": "concept", "hir_ids": [],
        "claim_ids": claims, "evidence_ids": evidence,
        "label": label, "subtitle": subtitle, "tone": tone,
        "x": x, "y": y, "width": width, "height": height,
    }
    if badge:
        value["badge"] = badge
    return value


def e(edge_id, source, target, evidence, nodes, label="", status="static"):
    a, b = nodes[source], nodes[target]
    ax, ay = a["x"], a["y"]
    aw, ah = a["width"], a["height"]
    bx, by = b["x"], b["y"]
    bw, bh = b["width"], b["height"]
    if bx >= ax + aw:
        points = [[ax + aw, ay + ah // 2], [bx, by + bh // 2]]
    elif by >= ay + ah:
        points = [[ax + aw // 2, ay + ah], [bx + bw // 2, by]]
    elif by + bh <= ay:
        points = [[ax + aw // 2, ay], [bx + bw // 2, by + bh]]
    else:
        lane = max(ay + ah, by + bh) + 50
        points = [[ax + aw // 2, ay + ah], [ax + aw // 2, lane], [bx + bw // 2, lane], [bx + bw // 2, by + bh]]
    value = {
        "id": edge_id, "source": source, "target": target,
        "points": points, "label": label, "status": status,
        "claim_ids": [], "evidence_ids": evidence,
    }
    if label:
        value["label_x"] = (points[0][0] + points[-1][0]) // 2
        value["label_y"] = min(p[1] for p in points) - 12
    return value


FIGURE_CONTRACTS = {
    "claude-system-overview": {"question": "What is the canonical runtime path and which services branch from it?", "glossary": {"CLI / REPL": "Command-line and interactive terminal surfaces", "Transcript JSONL": "Append-oriented session event log", "Anthropic Messages": "Provider request/response boundary"}, "exclusions": ["Compiled feature reachability", "Production frequency"]},
    "claude-turn-flow": {"question": "How does one user query iterate across multiple model requests and tool calls?", "glossary": {"Model Stream": "One streamed API request", "Tool Call?": "Decision based on tool_use blocks", "Retry / Compact": "Separate provider and context-pressure recovery paths"}, "exclusions": ["Exact runtime timing", "Feature-disabled recovery paths"]},
    "claude-context-lifecycle": {"question": "What reaches the model, when, and through which transformations?", "glossary": {"CLAUDE.md": "Hierarchical project/user instruction files", "History JSONL": "Durable transcript used to rebuild the live view", "Runtime Attachments": "Per-turn context deltas"}, "exclusions": ["Production token thresholds", "Semantic quality after compaction"]},
    "claude-tool-surface": {"question": "How do capabilities become visible model schemas and then executable actions?", "glossary": {"MCP Servers": "External Model Context Protocol capability providers", "Visible Schemas": "Tool definitions included in the current model request", "Tool Router": "Validation, hooks, permission and dispatch path"}, "exclusions": ["All conditional tools", "Runtime-enabled plugin inventory"]},
    "claude-permission-pipeline": {"question": "Which checks occur before a tool creates a side effect?", "glossary": {"Permission Rules": "Allow, ask and deny policy plus mode constraints", "Sandbox?": "Optional OS-backed execution isolation", "Model-facing Denial": "A denial returned to the loop as context"}, "exclusions": ["Unproven process-wide bypass reachability", "Platform-specific sandbox implementation"]},
    "claude-subagent-topology": {"question": "Which child mechanisms exist and what do they isolate or share?", "glossary": {"AgentTool": "Model-callable delegation entry", "Sidechain JSONL": "Child-specific durable transcript", "Swarm Teammate": "Team worker with in-process or terminal-pane backend", "Team Mailbox": "File-locked durable inbox"}, "exclusions": ["Observed process IDs", "Runtime permission prompt propagation"]},
    "claude-persistence-lifecycle": {"question": "What becomes durable, and what do resume and fork restore?", "glossary": {"Resume: Same ID": "Continue an existing session identity", "Fork: New ID": "Copy recoverable history into a new session identity", "NO ROLLBACK": "Workspace files are external to conversational restore"}, "exclusions": ["Corrupted JSONL behavior", "Abrupt SIGKILL durability"]},
    "claude-observability-recovery": {"question": "How are model/tool activity, retry and process shutdown observed?", "glossary": {"OTel": "OpenTelemetry spans and exporters", "Perfetto Trace": "Optional timing and agent-hierarchy trace", "Failsafe Timer": "Bounded final-exit safeguard"}, "exclusions": ["Tracing enabled by default", "Production latency and cost distributions"]},
    "claude-layered-architecture": {"question": "How do surface, core, safety/action, state and backend responsibilities depend on one another?", "glossary": {"Surface": "Entrypoints and rendering", "Core": "Shared query loop and context pressure management", "Safety / Action": "Capabilities, policy and execution mediation", "State": "Context, runtime and durable records", "Backend": "Host, remote and external resources"}, "exclusions": ["Strict acyclic layering", "Compiled feature reachability"]},
    "claude-extension-injection": {"question": "Where does each extension mechanism enter the loop?", "glossary": {"ASSEMBLE": "What the model sees", "MODEL SURFACE": "What actions the model can request", "AUTHORIZE / EXECUTE": "Whether and how an action runs", "Context Cost": "Prompt-window footprint when active"}, "exclusions": ["Installed plugin inventory", "Exact production context cost"]},
    "claude-values-mechanisms": {"question": "How do first-party product stances map through analyst principles to implementation mechanisms?", "glossary": {"Product Stance": "First-party documented objective or constraint", "Analyst Principle": "Normalized interpretation, not official taxonomy", "Mechanism": "Source-grounded implementation choice"}, "exclusions": ["Causal proof of author motivation", "Cross-project universality"]},
}


def figure(fig_id, title, description, node_list, edge_list, groups=None):
    nodes = {item["id"]: item for item in node_list}
    edges = [e(item[0], item[1], item[2], item[3], nodes, *item[4:]) for item in edge_list]
    labels = [" ".join(str(item["label"]).split()) for item in node_list]
    contract = FIGURE_CONTRACTS[fig_id]
    result = {
        "id": fig_id, "title": title, "description": description,
        "question": contract["question"],
        "exact_text": labels,
        "exactly_once": labels,
        "glossary": contract["glossary"],
        "exclusions": contract["exclusions"],
        "width": W, "height": H, "nodes": node_list, "edges": edges,
        "footer": "All architecture edges are static-only at commit 16a676f unless explicitly marked otherwise.",
    }
    if groups:
        result["groups"] = groups
    return result


FIGURES = []

# 1. System overview
nodes = [
    n("surface", "CLI / REPL", ["N-CLI", "N-Interactive", "N-Headless"], ["C-002", "C-003"], ["S-002", "S-003", "S-004", "S-005"], 30, 330, "interface"),
    n("session", "Live Session", ["N-Session"], ["C-003", "C-015"], ["S-004", "S-005", "S-029"], 245, 330, "state"),
    n("loop", "Query Loop", ["N-QueryLoop"], ["C-004"], ["S-006", "S-007", "S-008"], 460, 330, "core"),
    n("model", "Anthropic\nMessages", ["N-ModelAdapter", "N-ModelCall"], ["C-008"], ["S-016", "S-017"], 675, 330, "model"),
    n("tools", "Tool Router", ["N-ToolRegistry", "N-ToolRouter"], ["C-010", "C-011"], ["S-019", "S-020", "S-022"], 890, 330, "capability"),
    n("policy", "Permission Gate", ["N-Permission", "N-Policy"], ["C-012"], ["S-023", "S-024"], 1105, 330, "policy"),
    n("exec", "Sandbox / Shell", ["N-Sandbox", "N-Shell"], ["C-013"], ["S-025", "S-026", "S-027"], 1320, 330, "execution"),
    n("workspace", "Workspace", ["N-Workspace"], ["C-013", "C-016"], ["S-025", "S-030"], 1320, 520, "state"),
    n("context", "Context Builder", ["N-ContextBuilder", "N-SystemPrompt", "N-ClaudeMd", "N-Attachments"], ["C-006"], ["S-010", "S-011", "S-012", "S-013"], 460, 110, "state"),
    n("store", "Transcript JSONL", ["N-SessionStore"], ["C-015"], ["S-029"], 245, 600, "state"),
    n("children", "Subagents", ["N-AgentTool", "N-Subagent", "N-Team"], ["C-017"], ["S-032", "S-033", "S-034"], 675, 600, "muted"),
]
edges = [
    ("a1", "surface", "session", ["S-004", "S-005"]), ("a2", "session", "loop", ["S-006"]),
    ("a3", "loop", "model", ["S-007", "S-017"]), ("a4", "model", "tools", ["S-007", "S-022"]),
    ("a5", "tools", "policy", ["S-022", "S-024"]), ("a6", "policy", "exec", ["S-024", "S-025"]),
    ("a7", "context", "loop", ["S-006", "S-010"]), ("a8", "session", "store", ["S-029"]),
    ("a10", "exec", "workspace", ["S-025", "S-027"]),
    ("a9", "loop", "children", ["S-032", "S-033"]),
]
FIGURES.append(figure("claude-system-overview", "Claude Code: product boundary and canonical path", "The shared query loop connects interfaces, model calls, governed tools, context and durable state.", nodes, edges))

# 2. Turn flow
nodes = [
    n("input", "User Input", ["N-Interactive", "N-Headless"], ["C-003"], ["S-004", "S-005"], 20, 340, "interface"),
    n("context", "Build Context", ["N-ContextBuilder", "N-Compactor"], ["C-006", "C-007"], ["S-010", "S-014"], 220, 340, "state"),
    n("stream", "Model Stream", ["N-ModelCall"], ["C-004", "C-008"], ["S-007", "S-017"], 420, 340, "model"),
    n("route", "Tool Call?", ["N-ToolRouter"], ["C-004"], ["S-007", "S-008"], 620, 340, "core"),
    n("validate", "Validate", ["N-ToolRouter"], ["C-011"], ["S-022"], 820, 340, "capability"),
    n("permission", "Permission", ["N-Permission"], ["C-012"], ["S-024"], 1020, 340, "policy"),
    n("execute", "Execute Tool", ["N-BuiltinTools", "N-Shell"], ["C-011", "C-013"], ["S-022", "S-025"], 1220, 340, "execution"),
    n("append", "Append Result", ["N-Attachments", "N-ContextBuilder"], ["C-005"], ["S-009", "S-022"], 1420, 340, "state", width=150),
    n("stop", "Stop", ["N-Exit"], ["C-004"], ["S-008"], 650, 610, "neutral", width=120),
    n("recover", "Retry / Compact", ["N-Recovery", "N-Compactor"], ["C-007", "C-008"], ["S-014", "S-018"], 420, 100, "risk"),
]
edges = [
    ("b1", "input", "context", ["S-004", "S-005"]), ("b2", "context", "stream", ["S-007", "S-010"]),
    ("b3", "stream", "route", ["S-007"]), ("b4", "route", "validate", ["S-022"], "yes"),
    ("b5", "validate", "permission", ["S-022", "S-024"]), ("b6", "permission", "execute", ["S-024", "S-025"]),
    ("b7", "execute", "append", ["S-009", "S-022"]), ("b8", "append", "context", ["S-008", "S-009"], "continue"),
    ("b9", "route", "stop", ["S-008"], "no"), ("b10", "stream", "recover", ["S-014", "S-018"]),
    ("b11", "recover", "stream", ["S-018"]),
]
FIGURES.append(figure("claude-turn-flow", "One query: model, tool and recovery loop", "A query may contain multiple model calls; a UI turn is therefore not the same as one API request.", nodes, edges))

# 3. Context lifecycle
nodes = [
    n("system", "System Prompt", ["N-SystemPrompt"], ["C-006"], ["S-011"], 30, 80, "interface", badge="STARTUP"),
    n("claudemd", "CLAUDE.md\n+ Rules", ["N-ClaudeMd"], ["C-006"], ["S-012"], 30, 240, "capability", badge="LAZY"),
    n("history", "History JSONL", ["N-SessionStore"], ["C-015"], ["S-029"], 30, 400, "state", badge="DURABLE"),
    n("delta", "Runtime\nAttachments", ["N-Attachments"], ["C-006"], ["S-013"], 30, 560, "capability", badge="PER TURN"),
    n("builder", "Context Builder", ["N-ContextBuilder"], ["C-006"], ["S-010", "S-013"], 360, 310, "core", width=210),
    n("compact", "Compact?", ["N-Compactor"], ["C-007"], ["S-014", "S-015"], 700, 310, "policy"),
    n("request", "Model Request", ["N-ModelCall"], ["C-004", "C-008"], ["S-007", "S-017"], 1030, 310, "model"),
    n("result", "Tool Result", ["N-BuiltinTools", "N-Attachments"], ["C-005"], ["S-009", "S-022"], 1320, 500, "execution"),
]
edges = [
    ("c1", "system", "builder", ["S-011"]), ("c2", "claudemd", "builder", ["S-012"]),
    ("c3", "history", "builder", ["S-029"]), ("c4", "delta", "builder", ["S-013"]),
    ("c5", "builder", "compact", ["S-014"]), ("c6", "compact", "request", ["S-014", "S-015"]),
    ("c7", "request", "result", ["S-007", "S-009"]), ("c8", "result", "history", ["S-009", "S-029"]),
]
FIGURES.append(figure("claude-context-lifecycle", "Context is a lifecycle, not one prompt", "Startup instructions, durable history and per-turn deltas converge before token-pressure transforms.", nodes, edges))

# 4. Tools and extensions
nodes = [
    n("builtin", "Built-in Tools", ["N-BuiltinTools"], ["C-010"], ["S-019"], 20, 90, "capability"),
    n("mcp", "MCP Servers", ["N-MCP"], ["C-010"], ["S-020"], 20, 250, "model"),
    n("plugin", "Plugins", ["N-Plugins"], ["C-010"], ["S-003", "S-020"], 20, 410, "interface"),
    n("skills", "Skills", ["N-Skills"], ["C-006", "C-010"], ["S-013", "S-033"], 20, 570, "state"),
    n("pool", "Tool Pool", ["N-ToolRegistry"], ["C-010"], ["S-019", "S-020"], 330, 250, "core"),
    n("schemas", "Visible Schemas", ["N-ToolRegistry", "N-ModelCall"], ["C-010"], ["S-020", "S-021"], 600, 250, "model"),
    n("router", "Tool Router", ["N-ToolRouter", "N-Hooks"], ["C-011"], ["S-022"], 870, 250, "capability"),
    n("gate", "Permission Gate", ["N-Permission"], ["C-012"], ["S-024"], 1140, 250, "policy"),
    n("result", "Execution ->\nTool Result", ["N-Shell", "N-Attachments"], ["C-005", "C-013"], ["S-009", "S-025"], 1390, 250, "execution", width=170),
]
edges = [
    ("d1", "builtin", "pool", ["S-019"]), ("d2", "mcp", "pool", ["S-020"]),
    ("d3", "plugin", "mcp", ["S-003", "S-020"]), ("d4", "pool", "schemas", ["S-020", "S-021"]),
    ("d5", "schemas", "router", ["S-022"]), ("d6", "router", "gate", ["S-022", "S-024"]),
    ("d7", "gate", "result", ["S-024", "S-025"]), ("d8", "skills", "schemas", ["S-013", "S-033"], "context"),
]
FIGURES.append(figure("claude-tool-surface", "Registration, visibility and execution are different layers", "Plugins may contribute MCP, skills or hooks; only the current visible tool pool becomes model schemas.", nodes, edges))


# 5. Permission pipeline
nodes = [
    n("call", "Model Tool Call", ["N-ModelCall"], ["C-011"], ["S-017", "S-022"], 20, 320, "model"),
    n("validate", "Schema\nValidation", ["N-ToolRouter"], ["C-011"], ["S-022"], 230, 320, "capability"),
    n("rules", "Permission Rules", ["N-Policy", "N-Permission"], ["C-012"], ["S-023", "S-024"], 440, 320, "policy"),
    n("ask", "Ask User", ["N-Permission", "N-Interactive"], ["C-012"], ["S-004", "S-024"], 690, 100, "interface"),
    n("deny", "Model-facing\nDenial", ["N-Exit", "N-Attachments"], ["C-012"], ["S-022", "S-024"], 690, 560, "risk"),
    n("sandbox", "Sandbox?", ["N-Sandbox"], ["C-013"], ["S-026", "S-027"], 730, 320, "policy"),
    n("exec", "Execution", ["N-Shell"], ["C-013"], ["S-025", "S-027"], 1010, 320, "execution"),
    n("effect", "Workspace /\nNetwork Effect", ["N-Workspace"], ["C-013"], ["S-025", "S-027"], 1280, 320, "execution"),
    n("other", "Hooks + Other\nSubsystems", ["N-Hooks", "N-CLIEntry"], ["C-014"], ["S-003", "S-028", "I-001"], 1010, 610, "muted", badge="AUDIT"),
]
edges = [
    ("p1", "call", "validate", ["S-022"]), ("p2", "validate", "rules", ["S-022", "S-024"]),
    ("p3", "rules", "sandbox", ["S-024", "S-026"], "allow"), ("p4", "rules", "ask", ["S-024"], "ask"),
    ("p5", "rules", "deny", ["S-024"], "deny"), ("p6", "ask", "sandbox", ["S-024"], "approved"),
    ("p7", "sandbox", "exec", ["S-026", "S-027"]), ("p8", "exec", "effect", ["S-025", "S-027"]),
    ("p9", "other", "exec", ["S-028", "I-001"], "separate path", "inferred"),
]
FIGURES.append(figure("claude-permission-pipeline", "Permission is a decision pipeline; sandbox is conditional", "The canonical tool path is source-grounded. Other side-effect surfaces remain a separate audit question.", nodes, edges))

# 6. Subagent topology
nodes = [
    n("parent", "Parent Query", ["N-QueryLoop"], ["C-017"], ["S-006", "S-032"], 690, 40, "core"),
    n("agenttool", "AgentTool", ["N-AgentTool"], ["C-017"], ["S-032"], 690, 180, "capability"),
    n("child", "Agent Child", ["N-Subagent"], ["C-018"], ["S-032", "S-033"], 300, 380, "model", subtitle="own context + tools"),
    n("shared", "Shared Workspace", ["N-Workspace"], ["C-019"], ["S-032"], 110, 580, "execution", badge="DEFAULT"),
    n("worktree", "Worktree\nIsolation", ["N-Worktree"], ["C-019"], ["S-032", "S-035"], 500, 580, "state", badge="OPTIONAL"),
    n("sidechain", "Sidechain JSONL", ["N-SessionStore"], ["C-015", "C-018"], ["S-029", "S-033"], 300, 700, "state"),
    n("team", "Swarm Teammate", ["N-Team"], ["C-020"], ["S-034", "S-036"], 1080, 380, "interface", subtitle="in-process or pane"),
    n("mailbox", "Team Mailbox", ["N-Mailbox"], ["C-020"], ["S-037"], 1080, 600, "state", badge="DURABLE"),
    n("result", "Return to Parent", ["N-Attachments"], ["C-017", "C-018"], ["S-013", "S-032"], 690, 700, "neutral"),
]
edges = [
    ("s1", "parent", "agenttool", ["S-032"]), ("s2", "agenttool", "child", ["S-032", "S-033"]),
    ("s3", "agenttool", "team", ["S-034", "S-036"]), ("s4", "child", "shared", ["S-032"], "default"),
    ("s5", "child", "worktree", ["S-032", "S-035"], "optional"), ("s6", "child", "sidechain", ["S-029", "S-033"]),
    ("s7", "team", "mailbox", ["S-037"]),
    ("s9", "child", "result", ["S-032", "S-033"]), ("s10", "team", "result", ["S-034", "S-037"]),
]
FIGURES.append(figure("claude-subagent-topology", "Claude Code has several child mechanisms, not one", "Agent child and swarm teammate differ in context, process backend, workspace and result channel.", nodes, edges))


# 7. Persistence lifecycle
nodes = [
    n("live", "Live Session", ["N-Session"], ["C-015"], ["S-029"], 30, 250, "core"),
    n("append", "Append Messages", ["N-QueryLoop"], ["C-015"], ["S-029"], 270, 250, "capability"),
    n("jsonl", "Transcript JSONL", ["N-SessionStore"], ["C-015"], ["S-029"], 510, 250, "state", badge="DURABLE"),
    n("resume", "Resume: Same ID", ["N-Session"], ["C-016"], ["S-030", "S-031"], 780, 100, "interface"),
    n("fork", "Fork: New ID", ["N-Session"], ["C-016"], ["S-030", "S-031"], 780, 400, "interface"),
    n("rebuild", "Rebuild Context", ["N-ContextBuilder"], ["C-016"], ["S-030"], 1080, 250, "core"),
    n("workspace", "Workspace Files", ["N-Workspace"], ["C-016"], ["S-030", "I-003"], 1080, 600, "execution", badge="NO ROLLBACK"),
    n("compact", "Compaction Boundary", ["N-Compactor"], ["C-007", "C-015"], ["S-015", "S-029"], 510, 40, "policy"),
    n("worktree", "Worktree Path", ["N-Worktree"], ["C-016", "C-019"], ["S-030", "S-035"], 1350, 600, "state", badge="OPTIONAL"),
]
edges = [
    ("r1", "live", "append", ["S-029"]), ("r2", "append", "jsonl", ["S-029"]),
    ("r3", "compact", "jsonl", ["S-015", "S-029"]), ("r4", "jsonl", "resume", ["S-030", "S-031"]),
    ("r5", "jsonl", "fork", ["S-030", "S-031"]), ("r6", "resume", "rebuild", ["S-030"]),
    ("r7", "fork", "rebuild", ["S-030"]), ("r8", "rebuild", "workspace", ["S-030", "I-003"], "external state", "inferred"),
    ("r9", "workspace", "worktree", ["S-030", "S-035"], "optional"),
]
FIGURES.append(figure("claude-persistence-lifecycle", "Resume restores conversation state, not the filesystem", "JSONL history, session identity and optional worktree metadata have different persistence semantics.", nodes, edges))

# 8. Observability and recovery
nodes = [
    n("interaction", "Interaction Span", ["N-Telemetry"], ["C-021"], ["S-039"], 40, 90, "interface"),
    n("llm", "LLM Span", ["N-Telemetry", "N-ModelCall"], ["C-021"], ["S-039"], 320, 90, "model"),
    n("tool", "Tool Span", ["N-Telemetry", "N-ToolRouter"], ["C-021"], ["S-039"], 600, 90, "capability"),
    n("sinks", "Events + OTel", ["N-Telemetry"], ["C-021"], ["S-038", "S-039"], 900, 90, "observability"),
    n("perfetto", "Perfetto Trace", ["N-Telemetry"], ["C-021"], ["S-040"], 1200, 90, "muted", badge="OPTIONAL"),
    n("error", "Model Error", ["N-Recovery"], ["C-008"], ["S-018"], 40, 350, "risk"),
    n("retry", "Retry Policy", ["N-Recovery"], ["C-008"], ["S-018"], 320, 350, "policy"),
    n("outcome", "Retry / Fallback / Error", ["N-Recovery", "N-Exit"], ["C-008"], ["S-018"], 620, 350, "core", width=220),
    n("signal", "SIGINT / SIGTERM", ["N-Exit"], ["C-022"], ["S-041"], 40, 620, "interface"),
    n("shutdown", "Graceful Shutdown", ["N-Recovery"], ["C-022"], ["S-041"], 340, 620, "core"),
    n("cleanup", "Cleanup -> Hooks -> Exit", ["N-SessionStore", "N-Hooks", "N-Telemetry", "N-Exit"], ["C-022"], ["S-041"], 700, 620, "state", width=260),
    n("failsafe", "Failsafe Timer", ["N-Recovery"], ["C-022"], ["S-041"], 1080, 620, "risk"),
]
edges = [
    ("o1", "interaction", "llm", ["S-039"]), ("o2", "llm", "tool", ["S-039"]),
    ("o3", "tool", "sinks", ["S-038", "S-039"]), ("o4", "sinks", "perfetto", ["S-040"], "optional"),
    ("o5", "error", "retry", ["S-018"]), ("o6", "retry", "outcome", ["S-018"]),
    ("o7", "signal", "shutdown", ["S-041"]), ("o8", "shutdown", "cleanup", ["S-041"]),
    ("o9", "cleanup", "failsafe", ["S-041"]),
]
FIGURES.append(figure("claude-observability-recovery", "Observation and recovery are layered", "Tracing is optional; retry and shutdown use separate policies and time budgets.", nodes, edges))


# 9. Layered architecture
nodes = [
    n("surface", "Surface", ["N-CLI", "N-Interactive", "N-Headless"], ["C-002", "C-003"], ["S-002", "S-003", "S-004", "S-005"], 60, 100, "interface", subtitle="CLI, REPL, headless, SDK", width=300),
    n("loop", "Shared Query Loop", ["N-QueryLoop", "N-ModelCall"], ["C-003", "C-004"], ["S-006", "S-007", "S-008"], 400, 100, "core", width=260),
    n("compact", "Compaction Pipeline", ["N-Compactor"], ["C-007"], ["S-014", "S-015"], 700, 100, "core", subtitle="five ordered shapers", width=260),
    n("capability", "Capabilities", ["N-ToolRegistry", "N-BuiltinTools", "N-MCP", "N-Skills", "N-Plugins"], ["C-010", "C-028"], ["S-019", "S-020", "S-046"], 60, 340, "capability", subtitle="tools and extensions", width=260),
    n("governance", "Safety / Action", ["N-Permission", "N-Policy", "N-Hooks", "N-Sandbox"], ["C-012", "C-013", "C-014"], ["S-023", "S-024", "S-026", "S-028"], 360, 340, "policy", subtitle="rules, hooks, sandbox", width=280),
    n("children", "Subagents", ["N-AgentTool", "N-Subagent", "N-Team"], ["C-017", "C-018"], ["S-032", "S-033", "S-034"], 680, 340, "model", subtitle="recursive workers", width=240),
    n("context", "Context Assembly", ["N-ContextBuilder", "N-SystemPrompt", "N-ClaudeMd", "N-Attachments"], ["C-006"], ["S-010", "S-011", "S-012", "S-013"], 60, 570, "state", width=280),
    n("durable", "Durable State", ["N-SessionStore", "N-Mailbox"], ["C-015", "C-020"], ["S-029", "S-037"], 380, 570, "state", subtitle="transcript and inbox", width=260),
    n("backend", "Execution Backend", ["N-Shell", "N-Workspace", "N-Worktree"], ["C-013", "C-019"], ["S-025", "S-027", "S-035"], 1040, 340, "execution", subtitle="host, worktree, remote", width=270),
    n("external", "External Resources", ["N-MCP", "N-Telemetry"], ["C-008", "C-021"], ["S-016", "S-020", "S-039"], 1360, 340, "observability", width=190),
]
edges = [
    ("l1", "surface", "loop", ["S-004", "S-005", "S-006"]),
    ("l2", "loop", "compact", ["S-014"]),
    ("l3", "loop", "capability", ["S-007", "S-019", "S-020"]),
    ("l4", "capability", "governance", ["S-022", "S-024"]),
    ("l5", "governance", "backend", ["S-024", "S-025", "S-027"]),
    ("l6", "capability", "children", ["S-032", "S-033"]),
    ("l7", "context", "loop", ["S-010", "S-013"]),
    ("l8", "loop", "durable", ["S-029"]),
    ("l9", "backend", "external", ["S-016", "S-020", "S-039"]),
]
FIGURES.append(figure("claude-layered-architecture", "Five responsibility layers around one shared loop", "Interfaces and state surround a small reactive core; safety/action mediates capabilities before backend effects.", nodes, edges))

# 10. Extension injection points
nodes = [
    n("assemble", "ASSEMBLE", ["N-ContextBuilder"], ["C-006", "C-028"], ["S-010", "S-013"], 460, 110, "state", subtitle="what the model sees", width=240),
    n("model", "MODEL SURFACE", ["N-ToolRegistry", "N-ModelCall"], ["C-010", "C-028"], ["S-019", "S-020", "S-021"], 460, 350, "model", subtitle="what it can call", width=240),
    n("execute", "AUTHORIZE / EXECUTE", ["N-ToolRouter", "N-Permission", "N-Shell"], ["C-011", "C-012", "C-028"], ["S-022", "S-024", "S-025"], 460, 590, "policy", subtitle="whether and how it runs", width=280),
    n("plugins", "Plugins", ["N-Plugins"], ["C-028"], ["S-046"], 40, 350, "interface", subtitle="packaging", width=200),
    n("skills", "Skills", ["N-Skills"], ["C-028"], ["S-013"], 1020, 110, "capability", badge="LOW CONTEXT", width=220),
    n("mcp", "MCP Servers", ["N-MCP"], ["C-028"], ["S-020"], 1020, 350, "capability", badge="SCHEMA COST", width=220),
    n("hooks", "Hooks", ["N-Hooks"], ["C-028"], ["S-028", "S-043"], 1020, 590, "policy", badge="EVENT DRIVEN", width=220),
]
edges = [
    ("x1", "skills", "assemble", ["S-013"], "instructions"),
    ("x2", "mcp", "model", ["S-020"], "tools"),
    ("x3", "hooks", "execute", ["S-022", "S-028", "S-043"], "pre / post"),
    ("x4", "hooks", "assemble", ["S-028", "S-043"], "context"),
    ("x5", "plugins", "skills", ["S-046"], "packages"),
    ("x6", "plugins", "mcp", ["S-046"], "packages"),
    ("x7", "plugins", "hooks", ["S-043", "S-046"], "packages"),
]
FIGURES.append(figure("claude-extension-injection", "Four extension mechanisms, three runtime injection points", "Plugins package components; skills shape context, MCP expands callable tools, and hooks intercept lifecycle boundaries.", nodes, edges))

# 11. Documented stances to analyst principles to source mechanisms
nodes = [
    c("v1", "Human Authority", ["C-024"], ["D-001", "D-008"], 30, 90, "interface", width=210),
    c("v2", "Safety & Privacy", ["C-024"], ["D-001", "D-003", "D-004"], 30, 230, "policy", width=210),
    c("v3", "Reliable Execution", ["C-024"], ["D-002", "D-005"], 30, 370, "core", width=210),
    c("v4", "Capability Amplification", ["C-024"], ["D-002", "D-005"], 30, 510, "capability", width=210),
    c("v5", "Context Adaptability", ["C-024"], ["D-005", "D-006", "D-007"], 30, 650, "state", width=210),
    c("p1", "Deny-first &\nGraduated Trust", ["C-024", "C-027"], ["D-001", "D-003", "I-003", "I-005"], 500, 90, "policy", badge="ANALYST", width=240),
    c("p2", "Defense in Depth", ["C-024", "C-027"], ["D-003", "D-004", "I-003", "I-005"], 500, 230, "policy", badge="ANALYST", width=240),
    c("p3", "Progressive Context", ["C-024", "C-027"], ["D-005", "I-003", "I-005"], 500, 370, "core", badge="ANALYST", width=240),
    c("p4", "Composable Extensions", ["C-024", "C-027", "C-028"], ["D-005", "D-006", "I-003", "I-005"], 500, 510, "capability", badge="ANALYST", width=240),
    c("p5", "Append-only &\nIsolated Work", ["C-024", "C-027"], ["D-005", "D-007", "I-003", "I-005"], 500, 650, "state", badge="ANALYST", width=240),
    n("m1", "Rules + Re-approval", ["N-Policy", "N-Permission"], ["C-012", "C-029"], ["S-023", "S-024", "S-044"], 1060, 90, "policy", width=260),
    n("m2", "Permission + Sandbox", ["N-Permission", "N-Sandbox", "N-Hooks"], ["C-012", "C-013"], ["S-024", "S-026", "S-043"], 1060, 230, "policy", width=260),
    n("m3", "Five-stage Compaction", ["N-Compactor", "N-ContextBuilder"], ["C-006", "C-007"], ["S-014", "S-015"], 1060, 370, "core", width=260),
    n("m4", "MCP + Plugins +\nSkills + Hooks", ["N-MCP", "N-Plugins", "N-Skills", "N-Hooks"], ["C-028"], ["S-020", "S-043", "S-046"], 1060, 510, "capability", width=260),
    n("m5", "JSONL + Sidechains +\nWorktrees", ["N-SessionStore", "N-Subagent", "N-Worktree"], ["C-015", "C-018", "C-019"], ["S-029", "S-033", "S-035"], 1060, 650, "state", width=260),
]
edges = [
    ("v1p1", "v1", "p1", ["D-001", "D-008", "I-003"], "supports", "inferred"),
    ("p1m1", "p1", "m1", ["S-023", "S-024", "S-044", "I-005"], "implemented as", "inferred"),
    ("v2p2", "v2", "p2", ["D-003", "D-004", "I-003"], "supports", "inferred"),
    ("p2m2", "p2", "m2", ["S-024", "S-026", "S-043", "I-005"], "implemented as", "inferred"),
    ("v3p3", "v3", "p3", ["D-002", "D-005", "I-003"], "supports", "inferred"),
    ("p3m3", "p3", "m3", ["S-014", "S-015", "I-005"], "implemented as", "inferred"),
    ("v4p4", "v4", "p4", ["D-002", "D-005", "I-003"], "supports", "inferred"),
    ("p4m4", "p4", "m4", ["S-020", "S-043", "S-046", "I-005"], "implemented as", "inferred"),
    ("v5p5", "v5", "p5", ["D-005", "D-006", "D-007", "I-003"], "supports", "inferred"),
    ("p5m5", "p5", "m5", ["S-029", "S-033", "S-035", "I-005"], "implemented as", "inferred"),
]
FIGURES.append(figure("claude-values-mechanisms", "Documented product stances, analyst principles, source mechanisms", "The middle column is synthesis, not an official Anthropic taxonomy; source mechanisms remain independently verifiable.", nodes, edges))


def main():
    out = ROOT / "diagrams" / "story-specs.json"
    out.write_text(json.dumps({"schema_version": "1.0", "figures": FIGURES}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(FIGURES)} story figures to {out}")


if __name__ == "__main__":
    main()
