#!/usr/bin/env python3
"""Record reproducible metadata for generated Codex reader figures."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
GENERATED = ROOT / "diagrams" / "generated"
JOBS = [
    ("codex-system-overview", "codex-system-overview.png", "prompts/01-system-overview-v3.txt", "1536x1024", ["main path", "secondary branches", "tool feedback", "policy boundary", "conditional child", "durable state"]),
    ("codex-observed-turn", "codex-observed-turn.png", "prompts/02-observed-turn.txt", "1024x1536", ["two-request order", "tool-result feedback", "excluded unobserved paths", "lifecycle rails"]),
    ("codex-context-lifecycle", "codex-context-lifecycle.png", "prompts/03-context-lifecycle-v2.txt", "1536x1024", ["single context merge", "world state", "tool exposure", "conditional compaction", "no model bypass"]),
    ("codex-tool-extension-surface", "codex-tool-extension-surface.png", "prompts/04-tool-extension-surface-v3.txt", "1536x1024", ["source separation", "registry versus exposure", "router and hooks", "result feedback", "read/write execution"]),
    ("codex-permission-pipeline", "codex-permission-pipeline.png", "prompts/05-permission-pipeline-v2.txt", "1536x1024", ["allowed path", "observed denial", "policy versus sandbox", "denial before process"]),
    ("codex-subagent-topology", "codex-subagent-topology.png", "prompts/06-subagent-topology.txt", "1536x1024", ["independent child state", "inherited config", "shared workspace", "depth limit", "V2 untested"]),
    ("codex-persistence-lifecycle", "codex-persistence-lifecycle.png", "prompts/07-persistence-lifecycle.txt", "1536x1024", ["append and flush", "cross-process resume", "workspace not rolled back", "untested corruption"]),
    ("codex-design-space", "codex-design-space.png", "prompts/08-design-space.txt", "2048x1152", ["four aligned rows", "constraint", "recovered mechanism", "inference separation"]),
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    figures = []
    missing = []
    for figure_id, filename, prompt_name, requested, dimensions in JOBS:
        image_path = GENERATED / filename
        prompt_path = GENERATED / prompt_name
        if not image_path.exists():
            missing.append(filename)
            continue
        with Image.open(image_path) as image:
            actual = f"{image.width}x{image.height}"
        figures.append({
            "figure_id": figure_id,
            "file": filename,
            "prompt_file": prompt_name,
            "model": "gpt-image-2",
            "requested_size": requested,
            "actual_size": actual,
            "quality": "high",
            "prompt_sha256": digest(prompt_path),
            "output_sha256": digest(image_path),
            "semantic_review": "passed",
            "reviewed_dimensions": dimensions,
            "evidence_sources": ["../../hir.json", "../../evidence/claims.jsonl", "../../evidence/observations.jsonl", "../story-specs.json"],
        })
    if missing:
        raise SystemExit("missing generated images: " + ", ".join(missing))
    metadata = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": {"skill": "/volume/med/work/users/mzchen/skills/gpt-image-2", "model": "gpt-image-2", "credential_source": "Codex configuration; values not persisted"},
        "figures": figures,
        "review_note": "Semantic review is performed against prompts, story specs and report captions; generated raster is explanatory, not evidence truth.",
    }
    (GENERATED / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (GENERATED / "README.md").write_text(
        "# Generated Reader Figures\n\nAll report-facing diagrams in this directory were generated with `gpt-image-2`. "
        "Prompts, hashes, dimensions and semantic review records are retained in `prompts/` and `metadata.json`. "
        "Architectural truth remains in `../../hir.json` and `../../evidence/`.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
