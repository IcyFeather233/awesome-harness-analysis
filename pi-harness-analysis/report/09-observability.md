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

| 表面 | 面向谁 | 关联键/顺序 | 包含内容 | 缺口与敏感性 |
|---|---|---|---|---|
| In-process agent events | `AgentSession`、extensions、UI adapter | 单次 runtime 的 event sequence、message/tool 对象 | run/turn/message/tool/queue/compaction/retry/settled lifecycle | 默认没有全局 trace/span parent；payload 可含 prompt/tool data |
| JSON mode stdout | 自动化消费者、分析脚本 | header + 发出顺序 | 同一 session events 的结构化序列 | 原始输出含 assistant thinking、args/results；需要 redaction |
| RPC stream | 外部 host/UI | command response id + 并行 agent events | session control、events、extension UI request/response | command 与 event 因果关系需 host 自行维护 |
| JSONL session | resume/branch/fork | entry `id/parentId`、timestamp、file order | durable message/config/compaction/tree state | 不是低开销 telemetry；不包含完整内部 timing/span |
| OTel/Sentry adapter notes | 未来外部 adapter | 设计目标是 stable vendor-neutral event mapping | 文档化方向，不是默认 exporter | 本版本不能声明 collector delivery 或 trace propagation |
| 本分析 normalized trace | 复核者 | scenario id + sequence | role/type/length/model/usage/stop/tool lifecycle | 是分析产物，不是 Pi 产品 API；主动删除文本、thinking、args/results |

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
