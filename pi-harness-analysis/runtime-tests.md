# Runtime Test Record

Pinned target: `v0.80.7` / `818d67457cdd6b60bce6b121d16b23141c252dd8`.

## Setup

- Official Node `v22.19.0` portable archive was SHA-256 verified and extracted under `/tmp`.
- `npm ci --ignore-scripts` installed 351 packages; audit reported 0 vulnerabilities.
- Warning: optional `@earendil-works/gondolin@0.12.0` declares Node `>=23.6.0`; Gondolin was not run.
- Isolated HOME and synthetic workspace were used. No API key was stored.

## Model Discovery

Command shape:

```bash
HOME=/tmp/pi-analysis-runtime/home ./pi-test.sh   --list-models siflow --no-extensions --no-skills   --no-prompt-templates --no-context-files
```

Result:

```text
provider  model           context  max-out  thinking  images
siflow    qwen3.6-35ba3b  262.1K   16.4K    no        no
```

## Real Model Scenarios

Common arguments: `--provider siflow --model qwen3.6-35ba3b --mode json --no-extensions --no-skills --no-prompt-templates --no-context-files --no-approve`.

| Scenario | Additional controls | Exit | Event summary | Final |
|---|---|---:|---|---|
| R-001 | `--no-session --no-tools` | 0 | 1 turn, 0 tool, settled | `PI_TEXT_OK` |
| R-002 | `--no-session --tools read` | 0 | 2 turns, read start/end, settled | `314159` |
| R-003 | persistent `analysis-resume-001`, no tools | 0 | JSONL created | `ACK` |
| R-004 | reopen same session in new process | 0 | prior messages restored | `PI_RESUME_2718` |

## Controlled Tests

```text
agent-core loop + Agent:              2 files, 39 passed, 954ms
new AgentHarness/session/compaction:  3 files, 61 passed, 1.26s
Coding Agent compaction/retry/session:3 files, 31 passed, 2.76s
```

Exact test files are recorded in `evidence/observations.jsonl` (`X-001` through `X-003`).

## Trace Handling

Raw traces contain only synthetic prompts/files but may include model thinking. Normalized traces intentionally omit prompt text, assistant text/thinking, tool arguments and tool results. The report and HIR cite normalized traces.


## 2026-10-20 mechanism recheck

This is a new local mock/faux run on the same pinned commit. The real-provider
records above remain historical; no external model was called in this recheck.

Node 22.19.0 was downloaded from nodejs.org and its archive SHA-256 checked
against the official SHASUMS256. See traces/checks/node-runtime-provenance.json.
The runner exports pinned sources into a temporary directory, links existing
dependencies, disables Vitest caching, and passes a restricted environment with
no model credentials. It does not provide OS-level network isolation.

Detailed commands and per-test results:

- traces/checks/20261020/summary.json (X-004 through X-007)
- traces/checks/20261020-followup/summary.json (X-008 and X-009)
- traces/checks/20261020-cli/summary.json (X-010)

The saved results contain 179 passed, 1 failed and 21 skipped entries. The
initial CLI test in X-006 failed before the target behavior due to module
loading. X-010 supplied the development tsx/tsconfig loader and passed that
assertion; X-006 is preserved unchanged. X-005 skipped five real-model e2e
tests without credentials; X-009 selected five file-validation tests and left
sixteen tests outside its name filter.

Runner: reproduce/run_mechanism_checks.py. Use --group to select a group and a
new empty --output directory to preserve prior attempts.
