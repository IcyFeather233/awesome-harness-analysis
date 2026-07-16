#!/usr/bin/env python3
"""Add source-grounded MultiAgent V2 mailbox semantics to the analysis bundle."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
COMMIT = "87db9bc18ba5bc82c1cb4e4381b44f693ee35623"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


def augment_structured_evidence() -> None:
    claims_path = ROOT / "evidence" / "claims.jsonl"
    claims = read_jsonl(claims_path)
    for claim in claims:
        if claim["id"] != "C-013":
            continue
        claim["statement"] = (
            "V1 与 V2 multi-agent 是分离 feature gate；v0.144.5 默认 V1 开启、V2 关闭，"
            "默认并发/深度限制阻止无界递归。V2 还使用 session-scoped mailbox 把 child completion "
            "和其他 inter-agent communication 投递给 parent，并按 turn phase 决定当前轮或下一轮消费。"
        )
        claim["evidence_ids"] = list(dict.fromkeys([*claim["evidence_ids"], "S-027"]))
        claim["falsification_test"] = (
            "分别启用 V1/V2，检查工具 namespace、child depth 与并发上限；再让 V2 child 在 parent "
            "可见 final 前后完成，比较 mailbox 是进入当前 follow-up 还是留到下一 turn。本轮只运行 V1，"
            "mailbox 语义为静态源码结论。"
        )
    write_jsonl(claims_path, claims)

    observations_path = ROOT / "evidence" / "observations.jsonl"
    observations = [record for record in read_jsonl(observations_path) if record["id"] != "S-027"]
    observations.append(
        {
            "id": "S-027",
            "record_type": "evidence",
            "kind": "S",
            "summary": (
                "MultiAgent V2 的 session-scoped mailbox 保存 InterAgentCommunication。turn 起初允许 mail "
                "进入当前轮；可见 final 后通常延后到下一轮；reasoning/commentary 期间检测到 pending mail "
                "可提前结束当前 sampling，使下一次请求吸收该消息。child terminal event 也会转发给直接 parent。"
            ),
            "source": {
                "locator": "codex-rs/core/src/state/turn.rs:MailboxDeliveryPhase",
                "path": "codex-rs/core/src/state/turn.rs",
                "start_line": 35,
                "end_line": 55,
                "symbol": "MailboxDeliveryPhase",
                "url": (
                    "https://github.com/openai/codex/blob/"
                    f"{COMMIT}/codex-rs/core/src/state/turn.rs#L35"
                ),
                "scenario_id": None,
                "trace_id": None,
                "command": None,
            },
            "supports_claims": ["C-013"],
            "contradicts_claims": [],
            "conditions": {"feature": "multi_agent_v2", "runtime_tested": False},
            "confidence": "high",
            "notes": (
                "Queue/drain logic is in core/src/session/input_queue.rs:34-251; sampling preemption is in "
                "core/src/session/turn.rs:2099-2141; child terminal forwarding is in "
                "core/src/session/mod.rs:1812-1885."
            ),
        }
    )
    write_jsonl(observations_path, observations)

    hir_path = ROOT / "hir.json"
    hir = json.loads(hir_path.read_text(encoding="utf-8"))
    hir["edges"] = [edge for edge in hir["edges"] if edge["id"] != "E-Child-Mailbox"]
    hir["edges"].append(
        {
            "id": "E-Child-Mailbox",
            "source": "N-Subagent",
            "target": "N-AgentControl",
            "type": "returns",
            "label": "V2 completion/mailbox",
            "conditions": {"feature": "multi_agent_v2"},
            "evidence_ids": ["S-027"],
            "confidence": "high",
            "status": "static_only",
            "source_refs": [
                {
                    "path": "codex-rs/core/src/state/turn.rs",
                    "start_line": 35,
                    "end_line": 55,
                    "symbol": "MailboxDeliveryPhase",
                }
            ],
        }
    )
    hir_path.write_text(json.dumps(hir, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    coverage_path = ROOT / "evidence" / "coverage.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    for module_id in ("subagents", "orchestration"):
        module = coverage["modules"][module_id]
        module["files"] = list(
            dict.fromkeys(
                [
                    *module["files"],
                    "codex-rs/core/src/state/turn.rs",
                    "codex-rs/core/src/session/input_queue.rs",
                ]
            )
        )
    coverage_path.write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    story_path = ROOT / "diagrams" / "story-specs.json"
    if story_path.exists():
        story = json.loads(story_path.read_text(encoding="utf-8"))
        for figure in story["figures"]:
            if figure["id"] != "codex-subagent-topology":
                continue
            for node in figure["nodes"]:
                if node["id"] == "v26":
                    node["evidence_ids"] = list(dict.fromkeys([*node["evidence_ids"], "S-027"]))
            for edge in figure["edges"]:
                if edge["id"] == "a6":
                    edge["evidence_ids"] = list(dict.fromkeys([*edge["evidence_ids"], "S-027"]))
        story_path.write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    augment_structured_evidence()
