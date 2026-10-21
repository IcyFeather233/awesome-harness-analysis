# 入口、对象与生命周期

Pi 的 interactive、print/JSON 和 RPC 模式在 `main.ts` 分派，使用共同的 Coding Agent session 构建路径。模式层负责输入输出，`AgentSessionRuntime` 负责当前 session 及与 cwd 关联的服务，`createAgentSession()` 组合 `Agent`、`SessionManager`、设置、资源和模型注册表。[S: S-013, S-014, S-024]

## 对象怎样组合

`AgentSessionRuntime` 面对的是打开、替换、fork 和导入 session 等产品操作。发生 session/cwd 切换时，它负责清理并重建相关服务。`AgentSession` 面对的是一个已建立的 session，负责其 prompt、extensions、工具配置和运行收尾。

`Agent` 持有当前消息、model、tools、thinking level、输入队列和活动运行的取消信号。它把这些数据组成快照传给低层循环，并根据循环发出的事件更新自身状态。`SessionManager` 则持有记录树与文件索引；当前模型看到的消息是从树中选择和转换得到的视图。[S: S-008, S-019]

源码入口：[main.ts](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/main.ts#L650)、[sdk.ts](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/sdk.ts#L301)、[Agent](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/src/agent.ts#L184)。

## 输入不一定立即成为模型请求

`AgentSession.prompt()` 先尝试执行 extension command；被处理后可直接返回。随后 `input` hook 可以处理或变换输入，skill/template 再展开文本。若 session 正在运行，调用方须指定 `steer` 或 `followUp`，输入进入对应队列；普通 prompt 不会同时启动第二套运行。这里按调用参数分流，不分析句子语义来猜队列。默认交互界面在运行中用 Enter 选择 steer、Alt+Enter 选择 followUp，详见[队列选择机制](03-core-loop.md#双队列对应两种交互意图)。[S: S-002, S-033]

空闲路径检查模型和鉴权，检查是否需要发送前压缩，构造 user message，追加 `nextTurn` 消息，再处理 `before_agent_start` 返回的消息及 system prompt。最后进入 `_runAgentPrompt()`。此处的源码顺序解释了同一段用户文字为何可能先被命令或 extension 消费。[S: S-002]

## 三个结束时刻

`turn_end` 结束一轮 assistant 响应及其工具处理。低层循环发出 `agent_end` 时，其事件流已到末尾；`Agent` 仍会等待监听者，再清理运行状态。`AgentSession` 随后检查重试、压缩和剩余队列，必要时再次调用 `Agent.continue()`，最后发出 `agent_settled`。[S: S-001, S-019; X: X-005]

`agent_settled` 表示产品层暂时没有这次运行的后续工作。成功回答、不可恢复错误和取消都可能走到收尾，所以自动化消费者还须检查最后的响应、错误或任务产物。

## 用一个读文件例子区分这些事件

假设用户要求“读取 `config.json`，告诉我端口”。下面按源码规则示意一次正常执行；它是教学例子，历史真实 read 场景另见[请求过程](00-task-walkthrough.md)。

```text
用户提交一次请求
│
├─ turn 1
│  模型回复：调用 read 读取 config.json
│  Pi 执行 read，得到 {"port": 8080}
│  工具结果进入上下文
│  → turn_end
│
├─ turn 2
│  模型看到结果，回复：服务监听 8080 端口
│  没有新的工具调用或排队输入
│  → turn_end
│
├─ agent_end：本次低层循环结束
├─ AgentSession 检查重试、压缩及剩余队列
└─ agent_settled：产品层完成收尾
```

这里是一条用户请求、两个 turn、一次低层运行。一轮 assistant 响应提出多个工具调用时，这些调用也可以属于同一个 turn。[S: S-001]

| 事件 | 回答的问题 |
|---|---|
| turn_end | 这一轮模型响应及工具处理结束了吗？ |
| agent_end | 这一次低层循环结束了吗？ |
| agent_settled | 产品层的这次运行收尾了吗？ |

产品层压缩可能单独调用模型生成摘要；这种辅助调用不直接计作上面低层循环的 turn。若重试次数耗尽，Pi 报错并收尾，也可以发出 `agent_settled`。这些事件说明运行阶段，端口答得对不对仍须检查回答与文件内容。[S: S-002, S-019, S-021]

## 模式层的区别

| 模式 | 输入与输出 |
|---|---|
| Interactive | TUI 输入、交互操作与 extension UI |
| Print | 等待调用完成后输出最终内容 |
| JSON | 在 stdout 输出 session header 与结构化事件 |
| RPC | 消费命令并返回带 id 的响应，同时转发 session 事件 |

历史真实运行覆盖 JSON 路径；其他入口的共享关系由源码确认。当前产品的运行状态与收尾顺序见 [AgentSession 的状态与运行收尾](10-implementation-details.md)。
