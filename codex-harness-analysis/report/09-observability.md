# 可观测性与评估

Codex 有两套互补表面：用户/host 可消费的 thread、turn、item、tool events；以及 OTel logs/traces/metrics。

任务层创建 turn span，带 conversation/turn/model/token 等字段；tool runtime 发 `codex.tool_call` log，含 trace id、conversation id、turn id、tool/call id 与 duration。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tasks/mod.rs#L384) [S: `S-021`]

OTel 配置默认不记录 user prompts，exporter 可单独关闭，shutdown 必须显式完成。[文档](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/otel/README.md#L1) [D: `D-006`]

app-server 再把内部 events 映射为外部 notifications；exec `--json` 输出本轮观察到的 thread.started、turn.started、agent_message、collab_tool_call、turn.completed/failed。它适合产品集成，却不等同于完整 causal trace：例如 read tool 场景的 exec JSON 没有展示每个内部 handler event，本报告用 provider-side sanitized request log 补足了 tool feedback 证据。

本轮明确关闭 OTel exporter，因而没有声明 span-parent 拓扑、collector delivery 或 telemetry flush 的动态正确性。后续最有价值的实验是启动本地 collector，把同一 deterministic tool turn 对齐到 app-server events、OTel spans 和 rollout items 三个时间轴。
