# 观测、Tracing 与评估边界

> **证据边界。** 本报告分析 source-only commit `16a676f`。其 1,884 个 TS/TSX 文件、关键 symbol 与 feature gates 和论文所述 Claude Code v2.1.88 corpus 强指纹一致，但缺少 package version、上游 tree hash、build manifest，不能视为已证明的 exact 官方 artifact。快照仍有 657 个无法解析的相对 import；除 SiFlow 协议探针外，主循环、安全、session 与 subagent 结论均为 static-only。官方材料只支持产品立场，五价值/十三原则是 analyst synthesis。[X: X-001–X-003] [D: D-001–D-008] [C: C-001, C-024–C-026] 首次遇到缩写或内部名词时，可查 [全局术语表](16-glossary.md)。


![Claude Code observability and recovery layers](../diagrams/generated/assets/08-observability-recovery.png)

*读者图问题：模型、工具、重试和退出如何被观测与恢复？ 这是 gpt-image-2 读者插图；当前实现边均为 static-only，结构化证据与排除项见 [图片元数据](../diagrams/generated/metadata.json)。*

## 先区分 event、metric、span、trace 和 profiler

- **Event** 是某件事发生的一条离散记录，例如 tool 被调用或某 feature 启用；它适合计数和属性分析，但不天然表达父子关系。
- **Metric** 是聚合数值，例如次数、延迟分布或 token 总量。当前源码中的 analytics event 可以被 sink 聚合成 metric，但 event 本身不是 metric。
- **Span** 表示一个有开始/结束时间的操作，例如一次 LLM request 或 tool execution，并可带 status、token 和 parent span。
- **Trace** 是由 parent-child spans 组成的一次端到端执行树。只有 correlation 正确，才能知道某个 tool span 属于哪次 interaction/model request。
- **Profiler** 关注进程内部阶段耗时和资源快照，通常用于本地诊断；它不一定发送到 telemetry backend。
- **Redaction** 是在记录前删除或替换 prompt、路径、代码等敏感内容。它降低泄漏风险，但只有 runtime 配置与实际 payload 检查才能证明生效。

## 四类观测面

| 图中标签 | 机制 | 默认/条件 | 能回答什么 |
|---|---|---|---|
| Events | analytics `logEvent` queue、typed metadata 和 attachable sinks/exporters。 | 依赖 sink 初始化、sampling/config 和 metadata redaction 约束。 | 回答哪些 feature/tool/error 发生过、带了什么低敏属性；不能表达一次 query 的完整父子时序。 |
| OTel spans | interaction、LLM request、tool execution、hook 等有开始/结束时间的 spans。 | 受 enhanced/beta telemetry gate、exporter 和 privacy 设置控制。 | 回答 parent-child timing、token、status、success/error；前提是 correlation 正确且 payload 被正确 redacted。 |
| Query Profiler | local performance marks、阶段耗时和 memory snapshot。 | 由 `CLAUDE_CODE_PROFILE_QUERY` 等本地开关触发。 | 回答 context/model/tool 前后阶段耗时和资源变化；更适合本地诊断，不等于生产 telemetry。 |
| Perfetto Trace | Chrome trace event 格式、agent registry 和可视化 timeline。 | 受 feature/user/env gates 控制，默认不能假设开启。 | 回答 agent hierarchy、TTFT/TTLT、tool spans 和并发关系；没有 trace 时不能推断频率或 latency 分布。 |

[sessionTracing](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/utils/telemetry/sessionTracing.ts#L176) 用 **AsyncLocalStorage**（Node.js 在异步 callback/promise 链中传播请求上下文的机制）保存 interaction/tool context，并为并发 LLM request 要求显式传回对应 span，避免 response 绑错。默认 prompt 内容会 redacted，只有显式 env 才记录。[S: S-039]

表中的 **sink** 是 event/span 的最终接收器或 exporter；**sampling** 表示只记录满足比例/规则的事件；**TTFT** 是 time to first token，衡量请求到首 token；**TTLT** 是 time to last token，衡量请求到最后 token。它们回答的性能问题不同。

[analytics API](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/services/analytics/index.ts#L1) 在 sink attach 前排队事件，并用类型标记要求字符串 metadata 显式确认不含代码/路径；这是一种源码层防误传机制，不等同于完整隐私证明。[S: S-038]

Perfetto 记录 agent parent relationship，但源码注释标明条件门控；图中 OPTIONAL 不是装饰，而是防止读者以为每次用户运行都会产出 trace。[S: S-040]

## Retry 与 shutdown 为什么分成两条 lane

Model retry 处理一次调用边界上的 auth/rate/capacity/stream 问题；graceful shutdown 处理 process lifecycle。前者可以回到同一 query，后者目标是尽快保存关键状态并退出。把它们画成一个 Recovery box 会丢失时间预算和所有权差异。[S: S-018, S-041]

## 本分析观测到什么

只观测到 snapshot scanner 和 provider protocol probe，没有 target interaction/LLM/tool spans。因此本报告不能给出 latency、token、cost、tool frequency、delegation coverage 或 production behavior distribution。将来启用 OTel 时应保持 prompt redaction，另用 sanitized request digest 比较 context，而不是保存私有 prompt。[技术证据图](../diagrams/layered-architecture.svg)
