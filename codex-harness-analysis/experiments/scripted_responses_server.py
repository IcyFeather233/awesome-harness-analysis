#!/usr/bin/env python3
"""Small deterministic Responses SSE server for Codex architecture experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


def event(kind: str, payload: dict[str, Any]) -> bytes:
    body = {"type": kind, **payload}
    return f"event: {kind}\ndata: {json.dumps(body, separators=(',', ':'))}\n\n".encode()


def completed(response_id: str) -> bytes:
    return event(
        "response.completed",
        {
            "response": {
                "id": response_id,
                "usage": {
                    "input_tokens": 12,
                    "input_tokens_details": None,
                    "output_tokens": 4,
                    "output_tokens_details": None,
                    "total_tokens": 16,
                },
            }
        },
    )


def assistant(response_id: str, text: str) -> bytes:
    return b"".join(
        [
            event("response.created", {"response": {"id": response_id}}),
            event(
                "response.output_item.done",
                {
                    "item": {
                        "type": "message",
                        "role": "assistant",
                        "id": f"msg-{response_id}",
                        "content": [{"type": "output_text", "text": text}],
                    }
                },
            ),
            completed(response_id),
        ]
    )


def function_call(
    response_id: str,
    call_id: str,
    name: str,
    arguments: dict[str, Any],
    namespace: str | None = None,
) -> bytes:
    item: dict[str, Any] = {
        "type": "function_call",
        "call_id": call_id,
        "name": name,
        "arguments": json.dumps(arguments, separators=(",", ":")),
    }
    if namespace:
        item["namespace"] = namespace
    return b"".join(
        [
            event("response.created", {"response": {"id": response_id}}),
            event("response.output_item.done", {"item": item}),
            completed(response_id),
        ]
    )


class ScenarioState:
    def __init__(self, scenario: str, log_path: Path) -> None:
        self.scenario = scenario
        self.log_path = log_path
        self.lock = threading.Lock()
        self.request_number = 0

    def next_request_number(self) -> int:
        with self.lock:
            self.request_number += 1
            return self.request_number

    def log(self, summary: dict[str, Any]) -> None:
        with self.lock:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(summary, sort_keys=True) + "\n")


def tool_summary(tool: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {"type": tool.get("type")}
    for key in ("name", "namespace"):
        if key in tool:
            summary[key] = tool[key]
    if tool.get("type") == "namespace":
        summary["tools"] = [nested.get("name") for nested in tool.get("tools", [])]
    return summary


def contains_output(body: dict[str, Any], call_id: str | None = None) -> bool:
    for item in body.get("input", []):
        item_type = item.get("type")
        if item_type in ("function_call_output", "custom_tool_call_output"):
            if call_id is None or item.get("call_id") == call_id:
                return True
    return False


def input_text_digest(body: dict[str, Any]) -> str:
    text_parts: list[str] = []
    for item in body.get("input", []):
        for content in item.get("content", []) or []:
            text = content.get("text")
            if isinstance(text, str):
                text_parts.append(text)
    return hashlib.sha256("\n".join(text_parts).encode()).hexdigest()


class Handler(BaseHTTPRequestHandler):
    server_version = "HarnessAnalysisFixture/1.0"

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("content-length", "0"))
        body = json.loads(self.rfile.read(length))
        state: ScenarioState = self.server.state  # type: ignore[attr-defined]
        request_number = state.next_request_number()
        input_items = body.get("input", [])
        summary = {
            "timestamp_unix": time.time(),
            "scenario": state.scenario,
            "request_number": request_number,
            "path": self.path,
            "model": body.get("model"),
            "stream": body.get("stream"),
            "input_count": len(input_items),
            "input_types": [item.get("type") for item in input_items],
            "input_roles": [item.get("role") for item in input_items if item.get("role")],
            "contains_tool_output": contains_output(body),
            "tool_specs": [tool_summary(tool) for tool in body.get("tools", [])],
            "input_text_sha256": input_text_digest(body),
        }
        state.log(summary)

        response_id = f"resp-{state.scenario}-{request_number}"
        serialized = json.dumps(body, separators=(",", ":"))
        if state.scenario == "text_stop":
            payload = assistant(response_id, "SCRIPTED_OK")
        elif state.scenario == "read_tool":
            if contains_output(body, "call-read"):
                payload = assistant(response_id, "HXA-1445")
            else:
                payload = function_call(
                    response_id,
                    "call-read",
                    "exec_command",
                    {"cmd": "cat FACTS.txt", "yield_time_ms": 10000},
                )
        elif state.scenario == "unknown_tool":
            if contains_output(body, "call-unknown"):
                payload = assistant(response_id, "UNKNOWN_TOOL_REPORTED")
            else:
                payload = function_call(
                    response_id,
                    "call-unknown",
                    "definitely_not_a_tool",
                    {},
                )
        elif state.scenario == "denied_escalation":
            if contains_output(body, "call-denied"):
                payload = assistant(response_id, "DENIAL_REPORTED")
            else:
                payload = function_call(
                    response_id,
                    "call-denied",
                    "exec_command",
                    {
                        "cmd": "touch forbidden-marker",
                        "sandbox_permissions": "require_escalated",
                        "justification": "controlled denial experiment",
                    },
                )
        elif state.scenario == "subagent_spawn":
            if "CHILD_MARKER" in serialized:
                payload = assistant(response_id, "CHILD_OK")
            elif contains_output(body, "call-spawn"):
                payload = assistant(response_id, "ROOT_OK")
            else:
                payload = function_call(
                    response_id,
                    "call-spawn",
                    "spawn_agent",
                    {"message": "Return exactly CHILD_OK. CHILD_MARKER"},
                    namespace="multi_agent_v1",
                )
        else:
            payload = assistant(response_id, "SCRIPTED_DEFAULT")

        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.send_header("cache-control", "no-cache")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.state = ScenarioState(args.scenario, args.log)  # type: ignore[attr-defined]
    server.serve_forever()


if __name__ == "__main__":
    main()
