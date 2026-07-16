#!/usr/bin/env python3
"""Write revised prompts for figures rejected during semantic image review."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
GENERATED = ROOT / "diagrams" / "generated"
PROMPTS = GENERATED / "prompts"

STYLE = """
Style and visual hierarchy:
- Clean academic systems infographic with friendly hand-sketched geometry, bold dark-gray outlines, flat pastel fills, large modern sans-serif labels, white background, and generous whitespace.
- One unmistakable reading direction. Coral orchestration, blue model/capability, green state/result, amber policy, red failure, gray conditional/external.
- Similar visual language to a polished modern systems-research figure, but do not copy existing artwork.

Constraints:
- Use only the exact text listed. No title, caption, legend, evidence IDs, source paths, paragraphs, logos, watermark, gradients, shadows, 3D, photorealism, tiny print, nested cards, crossing arrows, or decorative words.
- Labels must remain horizontal and readable at 1000 pixels report width.
"""

PROMPTS_V2 = {
    "03-context-lifecycle-v2.txt": """
Use case: infographic-diagram
Asset type: reader-facing context data-flow illustration
Primary request: Explain context construction and show the complete tool-result feedback loop without any bypass.

Mandatory layout and arrows:
- Put five source icons in a vertical stack on the left: "Base instructions", "History", "World state diff", "User input", "Visible tool specs".
- Every source arrow must point into exactly one large center node "Context Manager". No source may point to any later node.
- Continue one solid main path to the right: "Context Manager" -> "StepContext + Prompt" -> "Responses API".
- Directly below "Responses API", draw a complete solid feedback path in this exact order: "Responses API" -> "Tool runtime" -> "Tool output" -> "History" -> "Context Manager".
- Put the label "tool call" only on the Responses API to Tool runtime arrow. Put "next request" only on the History to Context Manager arrow.
- Below Context Manager, draw one dashed conditional chain: "Token limit" -> "Compaction" -> "History replacement" -> "Context Manager". Add badge "WHEN NEEDED".
- Place "Long-term memory" as a separate dashed optional source into Context Manager with badge "EXPERIMENTAL".
- Arrowheads must make the full loop direction unambiguous. Never end Tool output without connecting it to History. Never draw Tool output directly into Responses API.

Text (verbatim, case-sensitive):
"Base instructions"
"History"
"World state diff"
"User input"
"Visible tool specs"
"Context Manager"
"StepContext + Prompt"
"Responses API"
"Tool runtime"
"Tool output"
"tool call"
"next request"
"Token limit"
"Compaction"
"History replacement"
"WHEN NEEDED"
"Long-term memory"
"EXPERIMENTAL"
""" + STYLE,
    "04-tool-extension-surface-v2.txt": """
Use case: infographic-diagram
Asset type: reader-facing capability pipeline illustration
Primary request: Show registration, exposure, model proposal, routing, hooks, execution, and feedback as separate ordered control points.

Mandatory layout and arrows:
- Across the very top, place exactly five compact source icons: "Built-ins", "MCP", "Extensions", "Dynamic tools", "Multi-agent".
- Their five arrows must converge into one and only one node "Tool registry" below. Use dashed arrows for all except Built-ins. No source may connect to exposure, model, router, hooks, runtime, result, or context.
- From Tool registry, draw one dominant left-to-right main path with exactly this order: "Tool registry" -> "Per-turn exposure" -> "Responses API" -> "Tool Router" -> "Pre-tool hooks" -> "Handler runtime" -> "Tool result" -> "Context".
- Put badge "VISIBLE NOW" on Per-turn exposure.
- Put label "tool call" only on Responses API to Tool Router.
- Put two small lines inside or below Handler runtime: "parallel read" and "exclusive write".
- Do not draw any shortcut from Tool registry to Tool Router, from Responses API to Pre-tool hooks, or from a source to a later stage.
- Use toolbox, plug, puzzle, function, agents, database, filter, model cloud, router, shield, lock, result, and context-stack icons.

Text (verbatim, case-sensitive):
"Built-ins"
"MCP"
"Extensions"
"Dynamic tools"
"Multi-agent"
"Tool registry"
"Per-turn exposure"
"VISIBLE NOW"
"Responses API"
"tool call"
"Tool Router"
"Pre-tool hooks"
"Handler runtime"
"parallel read"
"exclusive write"
"Tool result"
"Context"
""" + STYLE,
    "05-permission-pipeline-v2.txt": """
Use case: infographic-diagram
Asset type: reader-facing permission and sandbox decision illustration
Primary request: Explain allow, ask, and deny as three distinct Exec Policy outcomes. User approval is conditional, not mandatory for every allowed command.

Mandatory layout and arrows:
- Start on the left: "Model tool call" -> "Exec Policy".
- From Exec Policy, draw exactly three clearly separated branches.
- Top green branch: label arrow "allow" and point directly to "Platform Sandbox". This branch must bypass User Approval.
- Middle amber branch: label arrow "ask" and point to "User Approval", then to the same "Platform Sandbox".
- Bottom red branch: "NEVER + escalation" -> "Denied before process" -> "Tool error to model". Add badge "OBSERVED". It must never touch User Approval, Platform Sandbox, Process, or Workspace.
- After the two allowed branches merge at Platform Sandbox, continue one path: "Platform Sandbox" -> "Process" -> "Workspace".
- Put "Rules + mode" above Exec Policy with an input arrow.
- Put "Session cache" above User Approval with a two-way arrow.
- Put "Filesystem profile" and "Network profile" above Platform Sandbox with input arrows.
- Use decision, shield, user approval, OS boundary, process, folder, cache, network, and blocked-command icons.

Text (verbatim, case-sensitive):
"Model tool call"
"Exec Policy"
"allow"
"ask"
"User Approval"
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
""" + STYLE,
}

JOBS = [
    ("03-context-lifecycle-v2.txt", "codex-context-lifecycle.png", "1536x1024"),
    ("04-tool-extension-surface-v2.txt", "codex-tool-extension-surface.png", "2048x1152"),
    ("05-permission-pipeline-v2.txt", "codex-permission-pipeline.png", "1536x1024"),
]


def main() -> None:
    for name, prompt in PROMPTS_V2.items():
        (PROMPTS / name).write_text(prompt.strip() + "\n", encoding="utf-8")
    with (GENERATED / "jobs-revisions.jsonl").open("w", encoding="utf-8") as handle:
        for prompt_name, output, size in JOBS:
            handle.write(json.dumps({"prompt": (PROMPTS / prompt_name).read_text(encoding="utf-8"), "out": output, "size": size, "quality": "high"}) + "\n")


if __name__ == "__main__":
    main()
