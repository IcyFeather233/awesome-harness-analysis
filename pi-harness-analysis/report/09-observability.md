# 事件与可观测性

Pi 的事件同时服务界面、extension 和产品状态处理。JSON 模式将 session header 与这些事件写到 stdout，RPC 除命令响应外也转发事件。当前核心提供生命周期事件，默认没有完整的 OpenTelemetry trace/span 关联模型。[D: D-005, D-009; R: R-001, R-002]

## 事件表示哪个阶段

| 事件 | 可确认的阶段 | 需要另外检查的内容 |
|---|---|---|
| message_start / update | 消息开始或流式内容变化 | 尚不是最终消息，也不等于落盘 |
| message_end | 最终消息进入状态/监听处理路径 | 当前监听位置、是否持久化、文件是否首次创建 |
| tool_execution_start | 开始处理一次工具调用 | handler 可能被校验、block 或截断保护跳过 |
| tool_execution_end | 该调用的结果处理完成 | 结果可能是执行错误或准备阶段拒绝 |
| turn_end | 一轮 assistant 及工具批次结束 | 后续可能有下一轮模型请求 |
| agent_end | 一次低层循环结束 | 产品层可能重试、压缩或消费队列 |
| agent_settled | 产品层本次运行收尾完成 | 最终结果是否成功仍要看任务或错误 |

这张表依据 `Agent.processEvents()`、`AgentSession._handleAgentEvent()` 和工具批次实现。外部监听者与内部持久化有明确先后，事件名本身不足以推断磁盘或 OS 副作用。[S: S-018, S-019]

## 执行事件与持久历史

工具批次的结束事件可以按完成顺序到达，而持久消息按模型调用顺序形成。Session JSONL 记录可恢复的会话内容和配置，不保存每一次内部回调耗时。要分析延迟，需要额外关联请求、工具和时间信息。

历史 read 轨迹归一化后呈现 `run.started → turn.started → assistant(toolUse) → tool.started/completed → toolResult → turn.completed → 下一 turn → run.completed → run.settled`。其中 `tool.started` 是分析脚本对 Pi 事件的映射，含义仍受上述阶段边界约束。[R: R-002]

## 轨迹保留什么

原始 JSON 输出可含用户输入、模型文本/thinking、工具参数和结果。当前 normalized trace 去掉这些内容，保留事件序号、角色、类型、长度、usage 和工具关联信息。本次 Vitest JSON 则保留断言名称、状态、耗时及失败信息，可从[实验章节](11-runtime-experiments.md)定位。

OTel/Sentry adapter 在这个固定版本的相关文档中属于设计方向。本报告按 scenario 和事件序号关联记录，未验证 exporter 或 collector 端链路。[C: C-014]

## 运行完成和任务答对需要分别观测

[Scott 的 my-pi 实践](https://scottspence.com/posts/building-my-pi-claude-code-alternative-with-pi)区分运行故障与完成后的错误回答。[Kahtaf 的领域 Agent 记录](https://kahtaf.com/blog/lessons-from-building-a-domain-agent/)则按路由、工具、证据和回答层定位问题。[I: I-003]

当前 Pi 的 event stream 能帮助还原请求和工具经过了哪些阶段，任务产物是否符合要求仍需要单独的验收。`agent_settled` 也会在错误或取消收尾后出现。本报告的 controller 测试因此只支持所断言的机制，不当作真实任务成功率；外部项目加入的 telemetry、脱敏和评测组件也不记为默认 Pi 能力。[S: S-019]
