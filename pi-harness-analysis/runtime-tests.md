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
