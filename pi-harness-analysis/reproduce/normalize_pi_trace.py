#!/usr/bin/env python3
"""Normalize Pi JSON mode traces without retaining prompts or model content."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EVENT_MAP = {
    "agent_start": "run.started",
    "turn_start": "turn.started",
    "tool_execution_start": "tool.started",
    "tool_execution_update": "tool.updated",
    "tool_execution_end": "tool.completed",
    "turn_end": "turn.completed",
    "agent_end": "run.completed",
    "agent_settled": "run.settled",
}


def normalize(event: dict, scenario_id: str, sequence: int) -> dict | None:
    event_type = event.get("type")
    base = {"sequence": sequence, "scenario_id": scenario_id}

    if event_type == "session":
        return {
            **base,
            "type": "session.created_or_restored",
            "session_id": event.get("id"),
            "session_version": event.get("version"),
        }

    if event_type in EVENT_MAP:
        result = {**base, "type": EVENT_MAP[event_type]}
        if event_type.startswith("tool_execution_"):
            result.update(
                {
                    "tool_call_id": event.get("toolCallId"),
                    "tool_name": event.get("toolName"),
                    "is_error": event.get("isError"),
                }
            )
        if event_type == "turn_end":
            result["tool_result_count"] = len(event.get("toolResults", []))
        return result

    if event_type not in {"message_start", "message_end"}:
        return None

    message = event.get("message", {})
    role = message.get("role")
    content = message.get("content", [])
    if isinstance(content, str):
        text_chars = len(content)
        content_types = ["text"]
    else:
        text_chars = sum(len(item.get("text", "")) for item in content if item.get("type") == "text")
        content_types = [item.get("type") for item in content]

    result = {
        **base,
        "type": f"message.{event_type.removeprefix('message_')}",
        "role": role,
        "content_types": content_types,
        "text_char_count": text_chars,
    }
    if role == "assistant" and event_type == "message_end":
        usage = message.get("usage", {})
        result.update(
            {
                "provider": message.get("provider"),
                "model": message.get("model"),
                "stop_reason": message.get("stopReason"),
                "usage": {
                    "input": usage.get("input"),
                    "output": usage.get("output"),
                    "cache_read": usage.get("cacheRead"),
                    "cache_write": usage.get("cacheWrite"),
                    "total_tokens": usage.get("totalTokens"),
                },
            }
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--scenario-id", required=True)
    args = parser.parse_args()

    normalized = []
    with args.input.open(encoding="utf-8") as source:
        for sequence, line in enumerate(source, start=1):
            item = normalize(json.loads(line), args.scenario_id, sequence)
            if item is not None:
                normalized.append(item)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as destination:
        for item in normalized:
            destination.write(json.dumps(item, ensure_ascii=True, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
