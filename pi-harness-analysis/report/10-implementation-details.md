# AgentSession 的状态与运行收尾

`AgentSession` 把输入准备、extension、模型配置和会话存储接到 `Agent` 上。`Agent` 驱动低层循环并维护消息；产品层在循环结束后判断是否还有重试、压缩或排队输入需要处理。[S: S-002, S-019]

## 状态分别由谁持有

| 所有者 | 关键状态 | 何时使用 |
|---|---|---|
| AgentSession | `_isAgentRunActive`、`_lastAssistantMessage`、重试与 overflow 恢复标记 | 判断产品运行是否仍在继续，以及最后响应应走哪条恢复路径 |
| Agent | live messages、model、tools、thinking level、输入队列、取消信号 | 构造模型请求、执行工具、推进低层循环 |
| SessionManager | entries、`byId`、`leafId`、session 文件与 flushed 状态 | 追加历史、选择分支、重建上下文和写入文件 |
| ResourceLoader / ModelRegistry | 当前资源、工具来源、模型配置与请求鉴权 | 准备输入和每次请求需要的配置 |

同一条消息可以同时有内存对象和持久 entry。`Agent` 在 `message_end` 时先更新消息状态，`AgentSession` 再处理 extension、监听通知和 session append；这条顺序使工具处理能使用已完成的 assistant 消息。[S: S-019]

## 配置怎样进入下一轮

`setActiveToolsByName()` 根据 registry 更新 active tools，并重建基础 system prompt。`AgentSession` 安装的 `prepareNextTurn` 在 turn 边界读取当前 system prompt、tools、model 和 thinking level，返回下一次请求使用的 context/config。

因此要查“工具变了以后模型什么时候看到”，需要同时追踪 registry 更新和下一轮快照刷新。动态工具测试验证了注册表、active set 和 prompt 的更新；完整的请求中途配置差分仍是单独的检查项。[S: S-023; X: X-005]

## 低层结束后为什么还会继续

`_runAgentPrompt()` 先把产品运行标记设为 active，再调用 `agent.prompt()`。之后循环调用 `_handlePostAgentRun()`；后者返回 true 时，再调用 `agent.continue()`。[S: S-002]

`_handlePostAgentRun()` 取出最后一条 assistant 响应，按源码顺序处理：

1. 检查普通可重试错误，并在重试次数允许时准备退避和 continuation。
2. 对已经尝试重试但仍失败的响应发出相应结束通知，重置重试计数。
3. 检查压缩条件；错误 overflow 的恢复与已完成响应的压缩具有不同的续跑规则。
4. 检查低层结束事件处理期间新进入的队列，有输入时继续运行。

详细实现位于 [agent-session.ts](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L1023)。压缩条件见[上下文与压缩](04-context-memory-compaction.md)，消息排序见[核心循环](03-core-loop.md)。

## 自动重试由代码规则触发

`AgentSession` 的普通自动重试由错误分类和配置规则决定。低层运行结束后，`_handlePostAgentRun()` 读取最后的 assistant message，调用 `_isRetryableError()`；这里的 `stopReason`、`errorMessage` 可以是适配层封装的请求失败状态，不意味着模型已经判断应该重试。[S: S-002, S-010, S-031]

```text
低层运行结束
  → 读取最后一条 assistant message
  → 上下文溢出交给压缩分支
  → 检查 stopReason=error 且有 errorMessage
  → 排除配额/账单限制，匹配可重试错误文本
  → 检查 retry.enabled 和 maxRetries
  → 等待可取消的退避时间
  → Agent.continue() 重新请求模型
```

错误分类函数使用正则表达式匹配错误文本，不会再请求一个 LLM 判断是否值得重试。配额限制的排除规则先于临时错误匹配，因此错误中即使含有 `429`，也不一定重试。[S: S-031]

| 错误信息或状态 | 规则的处理 |
|---|---|
| overloaded、rate limit、部分 5xx 等临时服务错误 | 可进入普通自动重试，再受开关和次数约束 |
| connection lost、fetch failed、timeout 等传输错误 | 可进入同一重试路径 |
| insufficient_quota、billing、部分订阅额度限制 | 从普通自动重试中排除 |
| context overflow | 由 `_checkCompaction()` 处理，沿压缩恢复规则决定后续动作 |
| 普通回答没有完成任务或内容有误 | 不触发这个错误分类器的重试；它不评价答案质量 |

默认配置开启重试，`maxRetries=3`、`baseDelayMs=2000`。连续失败时，等待时间按 `baseDelayMs × 2^(attempt−1)` 计算，即 2、4、8 秒。收到非 error 的 assistant 消息时，产品层重置重试计数；这不是整条长任务一生只能重试三次的总预算。[S: S-010, S-019, S-032]

例如 Pi 请求 LLM 服务时返回 `503 Service Unavailable`，规则判定可重试，首次等待 2 秒。准备重试时，末尾失败响应从 live context 移除，但保留在 session 历史中，再由 `Agent.continue()` 重新发起请求。等待也可被取消。[S: S-010]

```text
同一次用户请求
├─ 第一次低层运行：LLM API 请求报可重试错误
│  → turn_end → agent_end
├─ AgentSession：检查规则，等待，再调用 continue
├─ 第二次低层运行：模型调用工具并给出回答
│  → agent_end
└─ 没有其他后续工作 → agent_settled
```

这是基于源码的重试示意，不是对历史 read 轨迹补造一次失败。用户没有重新提交请求，但同一次产品运行可以出现多次 `agent_end`，最后才 `agent_settled`。

## Bash 联网失败和模型 API 失败分别怎么处理

在未取消整体运行、也没有 extension 覆盖行为的默认 bash 工具路径中，命令自身的网络错误先成为工具结果。`AgentSession` 的自动重试分类器检查的则是最后一条 assistant 消息的错误状态。[S: S-010, S-031, S-034]

假设用户要求“下载这个文件，再分析内容”，模型提出：

```bash
curl --fail --max-time 5 https://example.com/data.json
```

若 curl 下载超时，以非零退出码结束，bash handler 会抛出包含输出和退出状态的异常。低层工具执行器捕获它，构造 `isError: true` 的 `toolResult`，把结果加入后续模型请求。接下来由模型决定换一种方式、报告失败，或提出一个新的等待后重试命令，例如：

```bash
sleep 10 && curl --fail --max-time 5 https://example.com/data.json
```

这里的等待和再次下载是模型提出的新工具调用，既不保证一定发生，也不使用产品层默认的 2/4/8 秒退避。上面的命令是教学示例，未在本轮实际运行。[S: S-018, S-034]

| 失败或重试发生在哪里 | Pi 看到的状态 | 谁决定后续动作 |
|---|---|---|
| curl、npm 等命令内部自行重试 | bash 调用仍在运行，最终结果尚未返回 | 命令自己的配置和实现 |
| bash 中的命令结束并返回网络错误 | 错误 toolResult 被交给模型 | LLM 决定下一次工具调用或回答 |
| Pi 请求 LLM 服务失败 | assistant 消息带 stopReason: "error" 和 errorMessage | AgentSession 按错误规则、次数与退避配置重试模型请求 |

所以，工具输出即使出现 `503` 或 `network error`，也不会仅凭这段文字触发产品层自动重试。分类器的输入必须先是相应的 assistant 错误消息。[S: S-031]

两层失败也可能连续发生：

```text
curl 下载失败
  → Pi 得到错误 toolResult
  → Pi 请求模型，让它决定下一步
  → 这次 LLM API 请求又失败
  → AgentSession 按规则重试 LLM API 请求
  → 模型恢复响应，决定是否再调用 bash
```

`Agent.continue()` 重试的是从现有上下文继续请求模型，不会直接重放上一批已执行的 shell 命令，也不回滚文件或从头执行整个用户任务。模型若随后再次要求执行同一命令，那是一次新的模型决策。

定位：[bash 非零退出处理](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/tools/bash.ts#L398)、[工具异常包装](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/src/agent-loop.ts#L669)、[产品层运行后检查](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L1038)。

## 自动重发与模型重新尝试工具的区别

| 情况 | 谁决定下一步 | 处在哪条路径 |
|---|---|---|
| 模型请求因网络或临时服务错误失败后重发 | Harness 的错误匹配、次数和退避规则 | AgentSession 产品层自动重试 |
| 测试命令失败，模型读到 toolResult 后改代码再运行 | LLM 根据上下文生成新的工具调用 | 正常模型—工具循环 |
| 上下文越界后生成摘要并继续 | 产品层选择压缩与续跑分支；模型承担摘要生成 | 压缩恢复路径 |

Provider SDK/适配器内部还可能有自己的请求重试配置。它与这里低层运行结束后的产品层重试是两层控制，不能简单把 `maxRetries=3` 当作全部 HTTP 尝试的上限。[S: S-024, S-032]

源码定位：[错误文本分类](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/ai/src/utils/retry.ts#L96)、[产品层重试准备](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/agent-session.ts#L2587)、[默认设置](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/settings-manager.ts#L813)。

## 最后怎样收尾

`_runAgentPrompt()` 的 finally 清除本次 system prompt override、处理 pending Bash messages，再调用 `_emitAgentSettled()`。后者更新产品运行标记，通知 extension 和订阅者，并处理 idle 等待者。[S: S-002, S-019]

由此可以区分低层 `agent_end` 和产品层 `agent_settled`：前者到来后，重试、压缩或队列仍可能延长这次产品运行。自动化调用方需要按所需边界等待，并另外检查最终响应和任务产物。[X: X-005, X-008]

## 从外部解读回到状态所有权

把扩展理解成“可以改工作流”，落实到代码后仍要回答：数据由谁持有、何时重建、哪些内容进入模型。当前路径中，Agent 管消息与队列，SessionManager 管历史记录，AgentSession 组织两者与 extensions 的生命周期。新增的工具输出分流与 reload 核查分别见 C-027、C-028；外部文章的用途解释和版本边界见[来源对照](17-external-perspectives.md)。
