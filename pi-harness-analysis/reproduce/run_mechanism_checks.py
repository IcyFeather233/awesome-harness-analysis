#!/usr/bin/env python3
"""Run pinned Pi mechanism tests in a disposable source copy, without model APIs."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone

COMMIT = "818d67457cdd6b60bce6b121d16b23141c252dd8"
GROUPS = [
    ("X-004", "agent", "vitest.config.ts", [
        "test/agent-loop.test.ts", "test/agent.test.ts",
    ]),
    ("X-005", "coding-agent", "vitest.config.ts", [
        "test/agent-session-compaction.test.ts",
        "test/agent-session-auto-compaction-queue.test.ts",
        "test/agent-session-dynamic-tools.test.ts",
        "test/suite/regressions/1717-2113-agent-session-event-settlement.test.ts",
        "test/suite/regressions/3317-network-connection-lost-retry.test.ts",
    ]),
    ("X-006", "coding-agent", "vitest.config.ts", [
        "test/session-manager/build-context.test.ts",
        "test/session-manager/tree-traversal.test.ts",
        "test/session-file-invalid.test.ts",
    ]),
    ("X-007", "agent", "vitest.harness.config.ts", [
        "test/harness/agent-harness.test.ts",
        "test/harness/session.test.ts",
        "test/harness/compaction.test.ts",
    ]),
    ("X-008", "coding-agent", "vitest.config.ts", [
        "test/suite/agent-session-compaction.test.ts",
        "test/suite/regressions/pre-prompt-compaction-no-continue.test.ts",
    ]),
    ("X-009", "coding-agent", "vitest.config.ts", [
        "test/session-manager/file-operations.test.ts",
    ]),
    ("X-010", "coding-agent", "vitest.config.ts", [
        "test/session-file-invalid.test.ts",
    ]),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--node", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--group", action="append", choices=[group[0] for group in GROUPS],
                        help="Current AgentSession groups by default; repeat to select groups explicitly (X-007 is historical)")
    args = parser.parse_args()
    selected_groups = set(args.group or [group[0] for group in GROUPS if group[0] != "X-007"])
    repo, node, output = args.repo.resolve(), args.node.resolve(), args.output.resolve()
    head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    if head != COMMIT:
        parser.error(f"expected {COMMIT}, found {head}")
    if not (repo / "packages/agent/node_modules/vitest/dist/cli.js").is_file():
        parser.error("existing reviewed dependencies are required; this runner does not install packages")
    if output.exists() and any(output.iterdir()):
        parser.error("output must be empty to preserve previous experiment records")
    output.mkdir(parents=True, exist_ok=True)
    archive = subprocess.check_output(["git", "-C", str(repo), "archive", COMMIT])
    summary = {
        "commit": COMMIT,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "node_version": subprocess.check_output([str(node), "--version"], text=True).strip(),
        "dependency_lock_sha256": hashlib.sha256((repo / "package-lock.json").read_bytes()).hexdigest(),
        "source_copy": "git archive of the pinned commit; original worktree is not edited",
        "dependencies": "existing node_modules linked read-only by convention; cache disabled",
        "model_mode": "mock/faux only; no credentials passed; no external model requests",
        "isolation": "temporary source/cache/test data; no OS-level network sandbox",
        "groups": [],
    }
    with tempfile.TemporaryDirectory(prefix="pi-mechanism-checks-") as temporary:
        work = Path(temporary)
        checkout = work / "source"
        checkout.mkdir()
        with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
            # Archive comes from the pinned local repository, not an external tarball.
            bundle.extractall(checkout, filter="data")
        for original in [repo / "node_modules", *repo.glob("packages/*/node_modules")]:
            dependencies = checkout / original.relative_to(repo)
            dependencies.mkdir(parents=True, exist_ok=True)
            for dependency in original.iterdir():
                if dependency.name.startswith(".vite"):
                    continue
                (dependencies / dependency.name).symlink_to(dependency, target_is_directory=dependency.is_dir())
        scratch = work / "tmp"
        scratch.mkdir()
        agent_dir = work / "agent-config"
        agent_dir.mkdir()
        env = {
            "PATH": f"{node.parent}:/usr/bin:/bin",
            "TMPDIR": str(scratch),
            "XDG_CACHE_HOME": str(work / "cache"),
            "PI_CODING_AGENT_DIR": str(agent_dir),
            "CI": "1",
            "NO_COLOR": "1",
        }
        for evidence_id, package, config, files in GROUPS:
            if evidence_id not in selected_groups:
                continue
            result_path = output / f"{evidence_id}.vitest.json"
            command = [str(node), str(checkout / "packages" / package / "node_modules/vitest/dist/cli.js"),
                       "--run", "--config", config, "--maxWorkers=1", "--no-cache",
                       "--reporter=json", "--outputFile", str(result_path), *files]
            if evidence_id == "X-009":
                command.extend(["--testNamePattern", "SessionManager.setSessionFile"])
            group_env = dict(env)
            if evidence_id == "X-010":
                group_env["NODE_OPTIONS"] = f"--import={(checkout / 'node_modules/tsx/dist/loader.mjs').as_uri()}"
                group_env["TSX_TSCONFIG_PATH"] = str(checkout / "tsconfig.json")
            started = datetime.now(timezone.utc).isoformat()
            try:
                result = subprocess.run(command, cwd=checkout / "packages" / package,
                                        env=group_env, capture_output=True, text=True, timeout=180)
                exit_code = result.returncode
                log = result.stdout + result.stderr
            except subprocess.TimeoutExpired as exc:
                exit_code = 124
                log = f"Timed out after {exc.timeout} seconds.\n"
            (output / f"{evidence_id}.log").write_text(log)
            details = json.loads(result_path.read_text()) if result_path.exists() else {}
            record = {
                "evidence_id": evidence_id, "package": package, "config": config,
                "test_files": files, "started_at": started, "exit_code": exit_code,
                "command": command, "cwd": str(checkout / "packages" / package),
                "loader": "tsx with workspace tsconfig" if evidence_id == "X-010" else "Vitest default",
                "passed": details.get("numPassedTests", 0),
                "failed": details.get("numFailedTests", 0),
                "skipped": details.get("numPendingTests", 0),
                "total": details.get("numTotalTests", 0),
                "result_file": result_path.name if result_path.exists() else None,
            }
            summary["groups"].append(record)
            (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
            print(f"{evidence_id}: exit={exit_code}, passed={record['passed']}/{record['total']}", flush=True)
            if exit_code:
                print(log[-4000:], flush=True)
    summary["completed_at"] = datetime.now(timezone.utc).isoformat()
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return int(any(group["exit_code"] for group in summary["groups"]))


if __name__ == "__main__":
    raise SystemExit(main())
