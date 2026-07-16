# 09 可观测性

## 已实现

Agent event vocabulary 包含：

- `agent_start`, `agent_end`, `agent_settled`；
- `turn_start`, `turn_end`；
- `message_start/update/end`；
- `tool_execution_start/update/end`；
- `queue_update`；
- `compaction_start/end`；
- `auto_retry_start/end`。

JSON mode 把 header + events 写到 stdout；RPC 在 command response 之外转发同一事件，并提供 extension UI request/response。[D: D-005] [R: R-001, R-002]

`R-SCENARIO-002` 归一化后可重建：

```text
session
  -> run.started
  -> turn.started
  -> user message
  -> assistant toolUse
  -> tool.started(read)
  -> tool.completed(read)
  -> toolResult
  -> turn.completed
  -> turn.started
  -> assistant stop
  -> run.completed
  -> run.settled
```

## 未实现为默认核心的部分

当前 event 没有统一 `traceId/spanId/parentSpanId`，也没有默认 OTel exporter。`packages/agent/docs/observability.md` 是 design notes：目标是 Pi 自己产 stable vendor-neutral events，外部 adapter 再映射到 OTel/Sentry。[D: D-009]

因此本分析通过 scenario id + sequence 做归一化 correlation，而没有把 JSON events 宣称成完整 distributed trace。[C: C-014]

## 数据敏感性

原始 JSON mode 会包含 prompt、assistant text/thinking、tool args/result。报告使用的 normalized trace 只保留角色、内容类型/长度、provider/model、usage、stop reason、tool name 与 lifecycle。生产接入应默认执行同类 redaction。
