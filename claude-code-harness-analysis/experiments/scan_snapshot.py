#!/usr/bin/env python3
"""Audit whether the mirrored Claude Code snapshot is self-contained."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path("/volume/med/work/users/mzchen/work/claude-code")
OUT = Path(__file__).resolve().parent / "snapshot-integrity.json"
SOURCE_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".json")
IMPORT_RE = re.compile(
    r"(?:from\s+|import\s*\(|require\s*\()\s*['\"]([^'\"]+)['\"]"
)


def resolve_relative(source: Path, specifier: str) -> Path | None:
    raw = source.parent / specifier
    candidates: list[Path] = [raw]
    if raw.suffix == ".js":
        stem = raw.with_suffix("")
        candidates.extend(stem.with_suffix(suffix) for suffix in (".ts", ".tsx", ".js", ".jsx"))
    elif not raw.suffix:
        candidates.extend(raw.with_suffix(suffix) for suffix in SOURCE_SUFFIXES)
    candidates.extend(raw / f"index{suffix}" for suffix in SOURCE_SUFFIXES)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def main() -> int:
    source_files = sorted(
        path
        for path in (ROOT / "src").rglob("*")
        if path.is_file() and path.suffix in {".ts", ".tsx", ".js", ".jsx"}
    )
    missing: list[dict[str, object]] = []
    import_count = 0
    for source in source_files:
        text = source.read_text(encoding="utf-8", errors="replace")
        for match in IMPORT_RE.finditer(text):
            specifier = match.group(1)
            if not specifier.startswith("."):
                continue
            import_count += 1
            if resolve_relative(source, specifier) is not None:
                continue
            line = text.count("\n", 0, match.start()) + 1
            missing.append(
                {
                    "source": str(source.relative_to(ROOT)),
                    "line": line,
                    "specifier": specifier,
                }
            )

    manifests = [
        name
        for name in (
            "package.json",
            "bun.lock",
            "bun.lockb",
            "pnpm-lock.yaml",
            "yarn.lock",
            "package-lock.json",
            "tsconfig.json",
        )
        if (ROOT / name).exists()
    ]
    result = {
        "schema_version": "1.0",
        "repository_root": str(ROOT),
        "source_file_count": len(source_files),
        "relative_import_count": import_count,
        "missing_relative_import_count": len(missing),
        "missing_relative_imports": missing,
        "present_build_manifests": manifests,
        "entrypoint_files_present": {
            path: (ROOT / path).exists()
            for path in (
                "src/entrypoints/cli.tsx",
                "src/main.tsx",
                "src/QueryEngine.ts",
                "src/query.ts",
            )
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in (
        "source_file_count",
        "relative_import_count",
        "missing_relative_import_count",
        "present_build_manifests",
    )}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
