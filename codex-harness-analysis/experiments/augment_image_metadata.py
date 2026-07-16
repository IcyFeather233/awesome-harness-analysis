#!/usr/bin/env python3
"""Add semantic-review notes and rejected variants to image metadata."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "diagrams" / "generated" / "metadata.json"


def main() -> None:
    metadata = json.loads(PATH.read_text(encoding="utf-8"))
    for figure in metadata["figures"]:
        if figure["figure_id"] == "codex-context-lifecycle":
            figure["review_notes"] = [
                "The two History icons are views of the same ContextManager history, repeated to keep the tool-output feedback loop free of crossing arrows."
            ]
        if figure["figure_id"] == "codex-tool-extension-surface":
            figure["review_notes"] = ["The model rendered the edge label as tool call only and added 1-7 stage numbers; the ordered architecture and edge direction are unchanged."]
    metadata["rejected"] = [
        {"file": "rejected/codex-system-overview-v1.png", "prompt_file": "prompts/01-system-overview.txt", "semantic_review": "rejected", "reason": "Tool output arrow pointed from Context into Tool runtime instead of feeding Context and the next turn."},
        {"file": "rejected/codex-system-overview-v2.png", "prompt_file": "prompts/01-system-overview-v2.txt", "semantic_review": "rejected", "reason": "A direct Tool runtime to Workspace edge competed with the policy branch and implied a bypass."},
        {"file": "rejected/codex-context-lifecycle-v1.png", "prompt_file": "prompts/03-context-lifecycle.txt", "semantic_review": "rejected", "reason": "Tool output stopped below Responses API instead of returning to History."},
        {"file": "rejected/codex-tool-extension-surface-v1.png", "prompt_file": "prompts/04-tool-extension-surface.txt", "semantic_review": "rejected", "reason": "Conditional sources connected to later pipeline stages and registry bypassed the model before routing."},
        {"file": "rejected/codex-permission-pipeline-v1.png", "prompt_file": "prompts/05-permission-pipeline.txt", "semantic_review": "rejected", "reason": "User approval was drawn as mandatory for every allowed command instead of only the ask branch."},
    ]
    PATH.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
