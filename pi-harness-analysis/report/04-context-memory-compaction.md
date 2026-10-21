# 上下文、消息转换与压缩

Pi 同时维护持久会话记录、当前分支的应用消息和本次模型请求的消息视图。它们之间通过选路、hook 和类型转换连接。理解这几个阶段，才能判断一条信息何时进入模型、何时留在文件中。[S: S-008, S-022]

## 持久历史、当前分支与本次请求

Pi 需要管理会话记录、恢复状态和显示过程；模型每次请求只接收经过选择与转换的内容。同一条信息在这些层次中的表示和用途可能不同。

| 层次 | 包含什么 | 回答的问题 |
|---|---|---|
| 持久历史 | 已保存的消息、不同分支、模型切换、压缩记录和扩展数据等 entry | 之前记录了什么？ |
| 当前分支 | 从当前 leaf 沿 parentId 选出的一条路径；运行时还会追加新的内存记录 | 现在沿哪段对话继续？ |
| 本次请求视图 | 按压缩边界选出的消息，经过扩展处理和类型转换，再与 system prompt、tools 组装 | 这一次模型实际收到什么？ |

例如，你先尝试方案 A，随后回到共同历史，改试方案 B。下面是教学示意：

```text
共同历史：分析登录问题
    ├─ 方案 A
    │   ├─ 阅读相关文件
    │   └─ 得到一大段失败日志
    │
    └─ 方案 B
        └─ 继续分析 ← 当前 leaf
```

完整历史可以保留两条分支。沿 B 继续时，重建路径通常选择“共同历史 + B 分支”，不会因为 A 的日志仍在文件中，就自动把它们全部加入本次请求。如果切换时生成分支摘要，一部分信息可以通过摘要带回。[S: S-008]

同一分支还可能经过压缩。例如，较早消息已经被总结，近期片段被保留：

```text
保存的记录：早期消息 + 近期消息 + compaction entry
请求用消息：压缩摘要 + 保留的近期消息 + 之后的新消息
```

旧消息可以继续保存在会话文件中，当前请求用摘要代表其中一部分。`buildSessionContext()` 负责结合分支和压缩边界构建应用消息，后面才进行消息变换与类型转换。[S: S-008, S-022]

这是数据视图之间的关系。恢复会话、切换分支或压缩时会重建相应上下文；正常 loop 在内存中追加消息，每次模型请求再转换当前消息列表。它不要求每次请求都从磁盘重读完整 session。文件首次创建和追加时机见[会话持久化](08-sessions-persistence-recovery.md)。

## 为什么先看上下文控制面

[Mario 的设计回顾](https://mariozechner.at/posts/2025-11-30-pi-coding-agent/)把可检查、可控制的模型上下文列为开发 Pi 的动机。[D: D-011]

这个角度适合用来阅读 `AgentSession`：先找信息在哪个阶段进入，再看谁能改写它。`before_agent_start`、`context`、active tools 和会话分支分别作用于不同位置；“系统提示短”只描述其中一部分，不能代表安装扩展后的整次请求有多大。[S: S-002, S-004, S-008, S-023]

## 信息从哪里进入

system prompt 由 `buildSystemPrompt()` 组合默认或自定义提示、工具说明、project instructions、skills 索引和 cwd。skills 索引在有 read 工具时加入；`/skill:name` 在输入处理时读取正文并展开成用户侧文本。AGENTS/CLAUDE 项目指令与受 project trust 控制的 `.pi` 启动资源有不同的加载边界，见[信任与执行](06-permissions-sandbox-workspace.md)。[S: S-002, S-004, S-005, S-006]

当前分支由 `SessionManager.buildSessionContext()` 生成。工具结果进入后续消息，extension 的 `before_agent_start` 可追加 custom messages 或覆盖本次 system prompt；`context` hook 则在每次 provider 请求前处理消息视图。[S: S-001, S-003, S-008]

## 应用消息怎样变成 provider messages

![持久历史怎样变成本次模型请求，system prompt 和 tools 在哪里加入？](../diagrams/generated/pi-context-views-v3.png)

会话记录先选出当前分支，有压缩记录时组合最新摘要与保留消息，再经过消息变换和类型转换；system prompt 与 active tools 在请求组装处单独加入。图示源码中的视图转换，不表示压缩触发频率。证据：S-001、S-004、S-008、S-022。[提示词、生成参数与复核记录](../diagrams/generated/metadata.json)。

低层循环依次调用 `transformContext → convertToLlm`。前者允许 extension 调整请求用的消息；后者通过普通 TypeScript 分支转换类型、整理字段和过滤消息，不调用 LLM。转换结果是 pi-ai 的 `Message[]`，provider 适配器之后才将其变成具体 API 的请求格式。system prompt 和 active tools 在消息转换后单独加入请求 context。[S: S-001, S-022]

| 应用消息 | `convertToLlm` 的处理 |
|---|---|
| user / assistant / toolResult | 保留 pi-ai 标准消息，之后由 provider 适配器继续转换 |
| custom | 将内容包装成 user message |
| bashExecution | 把命令、输出和状态组织成 user 文本；excludeFromContext 为 true 时过滤 |
| compactionSummary | 给已有摘要加上说明与 summary 标签，再包装为 user message |
| branchSummary | 给分支摘要加上相应说明，再包装为 user message |

以下例子省略时间戳等字段，用于说明转换过程，不是新增运行轨迹。

### 扩展消息：界面隐藏与模型可见是两个属性

扩展可以注入这样一条应用消息：

```json
{
  "role": "custom",
  "customType": "project-rule",
  "content": "不要修改公共 API。",
  "display": false,
  "details": {"source": "project-settings"}
}
```

转换后，消息正文成为：

```json
{
  "role": "user",
  "content": [{"type": "text", "text": "不要修改公共 API。"}]
}
```

`display: false` 控制 TUI 显示，不能据此判断模型看不到内容。`customType`、`display` 和 `details` 没有被自动展开到这条 user 消息中。转换后的 `role: "user"` 表示模型消息格式中的位置，内容也可能来自扩展，而不一定由人刚刚输入。[S: S-022]

还要分清持久记录的 `type` 和应用消息的 `role`：

| 持久记录 | 重建与发送路径 |
|---|---|
| `type: "custom"` 的 CustomEntry | 保存扩展状态，例如计数器；默认不参与模型上下文 |
| `type: "custom_message"` 的 CustomMessageEntry | 先重建为 `role: "custom"` 的应用消息，再由 convertToLlm 转为 user message |

扩展因此可以保存内部状态，也可以显式注入给模型看的内容，两种记录有不同的入口。[S: S-008, S-022]

### Bash 执行记录：用户命令与模型工具调用分别表示

用户直接输入 `!npm test` 时，可以产生这种内部记录：

```json
{
  "role": "bashExecution",
  "command": "npm test",
  "output": "1 test failed",
  "exitCode": 1,
  "cancelled": false,
  "truncated": false
}
```

转换函数将命令、输出和退出状态整理成 user 文本。例如，下面用 JSON 转义表示换行，代码围栏也是正文的一部分：

```json
{
  "role": "user",
  "content": [{
    "type": "text",
    "text": "Ran `npm test`\n```\n1 test failed\n```\n\nCommand exited with code 1"
  }]
}
```

若记录带 `excludeFromContext: true`，例如 `!!` 命令对应的排除语义，`convertToLlm` 会过滤这条消息。记录仍可供应用管理，但不通过这条转换路径进入请求。

模型主动请求 bash 工具时，返回的是与 tool call 关联的 `toolResult`；上面的 `bashExecution` 描述用户直接执行命令的记录。不能把所有 Bash 输出都当作转换后的 user message。[S: S-022]

### 压缩摘要：包装已有文本，而不是再次总结

应用消息可以用专门的类型保存摘要：

```json
{
  "role": "compactionSummary",
  "summary": "正在修复登录问题，已排除数据库连接故障。",
  "tokensBefore": 80000
}
```

`convertToLlm` 把 summary 包装成一条 user message，其文本类似：

```text
The conversation history before this point was compacted into the following summary:

<summary>
正在修复登录问题，已排除数据库连接故障。
</summary>
```

`tokensBefore` 用于程序记录压缩前状态，不会自动成为摘要正文。摘要文字在更早的压缩步骤中生成；这里仅添加说明和标签。`branchSummary` 也采用相似的文本包装方式。[S: S-022]

源码：[消息定义与转换](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/messages.ts#L33)、[会话记录到应用消息](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/session-manager.ts#L375)、[请求组装](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/agent/src/agent-loop.ts#L282)。[C: C-025]

## 排查模型为什么没看到一条信息

沿数据经过的位置依次检查：

1. 信息是否已经进入会话记录，还是只在界面或扩展内部？
2. 记录是否属于当前 leaf 选出的分支？
3. 原始消息是否已被压缩摘要代表？
4. `transformContext` 是否过滤、替换或追加了消息？
5. `convertToLlm` 保留了哪些字段，是否过滤了整条消息？
6. provider 适配器最终怎样组织实际请求？

确认“文件里有这条记录”只回答了第一个阶段的一部分。请求视图还经过分支选择、摘要与消息转换；需要对照这些阶段或捕获的请求，判断模型实际收到的内容。[S: S-001, S-008, S-022, S-026]

## 压缩前先判断响应与历史边界

`AgentSession._checkCompaction()` 在低层运行结束后和发送新 prompt 前调用。它先检查开关和 abort 条件，再检查模型是否相同、assistant 响应是否早于最新 compaction boundary。旧模型的 overflow 和压缩边界之前的 usage 不能直接用于触发当前上下文的同一条恢复分支。[S: S-021]

接下来分两类处理：

- Overflow：当前模型报告上下文越界或 usage 超过窗口。若响应已经以 `stop` 完成，则压缩但不重答。需要恢复的错误响应最多进行一次 compact-and-retry，避免同一次恢复无限循环。
- Threshold：上下文接近配置阈值时压缩。已完成回答不会因此重新生成；如果压缩期间有输入入队，产品层仍可继续消费这些输入。

发生错误或 usage 为零时，代码会从最后有效的 usage 估算上下文，并检查估算来源是否已经被此前压缩淘汰。本次 `X-008` 执行了 15 项 faux/controller 用例；`X-005` 另覆盖压缩后队列续跑。[C: C-024]

## 已经有阈值检查，为什么还会溢出

Threshold 根据已有用量或估算，在接近窗口上限时预先腾空间；Overflow 则处理已经收到的越界信号。提前检查仍有时间和信息上的边界。

当前默认路径主要在发送新 prompt 前、一次低层运行结束后检查压缩。发送新 prompt 前的检查发生在构造并加入这次新用户消息之前；一次低层运行内部可以连续处理多个工具批次，默认的逐轮刷新 hook 也没有在每次工具结果返回后执行相同的压缩检查。因此，上一次检查之后，新的输入或工具输出仍可能让下一次请求突然变大。[S: S-021]

例如，假设窗口是 100,000 token，预留 16,384，触发阈值就是 83,616。检查时用量为 75,000，尚未触发；后续加入约 30,000 token 的材料，下一次请求就可能越过窗口。这个数值例子只说明检查间隙的增长，不是测得的 Pi 运行轨迹。用量估算与 provider 实际计数的差异，也会让预防性判断存在误差。

源码中的 overflow 分支还包含“响应已经成功 stop，但报告的输入用量超过本地配置窗口”的情况。这时只压缩、不重答；需要恢复的溢出响应才使用一次 compact-and-retry 的限额。因此，两条分支分别处理提前腾空间和收到越界信号后的状态，不能把所有 overflow 都理解成 API 已经拒绝请求。[S: S-021]

## 两个压缩预算各控制什么

当前设置中 `reserveTokens` 默认 16384，`keepRecentTokens` 默认 20000。前者进入 `contextTokens > contextWindow - reserveTokens` 的触发判定；后者用于向后估算需要保留的近期片段。改变预留预算不等于改变同样数量的保留消息。[C: C-029; S: S-028, S-029]

`findCutPoint()` 使用逐条消息的 `estimateTokens()` 累计保留片段的估算体积。触发检查使用的 `estimateContextTokens()` 则会优先利用最近有效 assistant usage，并估算后续新增消息；两处估算服务于不同阶段。切分还受合法消息边界约束，保留量不是 provider tokenizer 的精确测量。[S: S-021, S-029]

这两类预算在部分解读中被混称为 reserve。对照配置 getter 和切点函数，可以把“什么时候压缩”与“保留哪段历史”分开验证，详见[外部来源核对](17-external-perspectives.md)。

## 哪些消息保留原文，哪些送去总结

默认路径先由代码选出近期连续片段，再由 LLM 提炼较早消息的内容。以下示例沿用“排查启动问题”的任务，数字与切点用于解释源码，不代表新增实验。[S: S-029, S-035]

假设当前分支积累了约 80,000 token 的对话。`findCutPoint()` 从最新 entry 往前走，把其中上下文可见消息的估算体积逐项相加，达到 `keepRecentTokens` 后选择合法切点。默认预算是 20,000，因此可以先把结果理解成：

```text
较早的连续消息，约 60,000 token │ 最近的连续消息，约 20,000 token
          交给模型生成摘要     │          保留原文
```

这里按 token 体积选择，而不是固定保留多少条消息。`estimateTokens()` 对文本主要采用字符数除以 4 的启发式估算，图片等内容另有估算处理；再加上边界调整，实际保留量不保证恰好等于预算。较早的重要要求也可能落进摘要区域，其后续可见性依赖摘要是否准确保留它。[S: S-029]

### 工具调用与结果不能从中间拆开

假设某段消息是：

```text
assistant：调用 read("config.ts")
toolResult：文件内容……
assistant：根据配置，接下来检查启动脚本……
```

代码不允许把 `toolResult` 当作保留片段的第一条消息。找到预算位置后，它会选择该位置或更靠后的合法切点：若从包含工具调用的 assistant 消息开始保留，后续结果也保留；若切到后面的 assistant 消息，前面那组调用和结果一起进入待压缩部分。这样不会只留下一个失去对应调用的工具结果。[S: S-029]

### 一次任务太长时，给保留的后半段补上来由

合法切点可以是 assistant 消息，所以一次用户要求产生的长执行过程，也可能被分成两段：

```text
更早的对话
用户：帮我修复启动问题
assistant：读取配置、修改启动脚本
toolResult：修改完成
                           ← 从这里开始保留原文
assistant：执行测试
toolResult：端口冲突
assistant：继续排查……
```

这时 `prepareCompaction()` 找到该段交互的起始输入，将“更早的对话”和“本次任务被切掉的前半段”分别准备。常规压缩路径为前者生成历史摘要，再为后者生成专门的前缀摘要，交代原始要求、早期进展，以及理解后半段需要的信息。两份摘要合并到同一条 compaction 记录中，后面接保留的原文。[S: S-035]

```text
历史摘要 + 本次任务前半段摘要 + 本次任务后半段原始消息
```

源码称这种情况为 `split turn`。压缩模块在这里按 user、Bash 执行记录或其他用户侧消息寻找交互起点；它与低层循环中“一次模型响应及其工具处理”的 turn 不是同一个计数单位。一次用户任务可以跨过多个低层 turn。

### 模型负责把旧内容写成什么摘要

普通历史摘要的提示词要求覆盖目标、用户约束与偏好、已完成和进行中的工作、阻碍、关键决定、下一步及必要上下文，并要求保留准确的路径、函数名和错误信息。长任务的前缀摘要则侧重原始要求与后半段需要的背景。代码还会从工具调用中提取读过、修改过的文件路径并附到摘要中。[S: S-035]

已有压缩记录时，准备阶段取出上次摘要与之前保留的起点；历史摘要更新路径会把旧摘要和本次需要总结的消息一起交给模型。后续压缩通常是在已有摘要上继续整理，不需要每次重读所有已被摘要代表的原始消息。摘要是有损的信息整理，提示词要求保留某项内容，并不等于它一定完整保留了该项内容。

以上描述默认摘要生成路径。扩展可以在 `session_before_compact` 中取消或提供压缩结果，具体配置需要沿扩展路径另查。[S: S-021]

源码：[切点与消息体积](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/compaction/compaction.ts#L240)、[摘要提示词](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/compaction/compaction.ts#L441)、[压缩准备与分段摘要](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/compaction/compaction.ts#L633)。

## 摘要怎样替换当前消息

`_runAutoCompaction()` 从当前 branch 准备压缩。`session_before_compact` 可以取消或提供摘要；常规路径则调用模型生成 summary。成功后按以下顺序处理：

1. 追加带 `summary`、`firstKeptEntryId`、`tokensBefore` 的 compaction entry。
2. 从当前会话树重建 context。
3. 用重建结果替换 `agent.state.messages`。
4. 发出压缩完成通知，并按恢复标记或剩余队列决定是否继续。[S: S-021]

重建结果包含最新摘要、从 `firstKeptEntryId` 开始保留的旧消息，以及压缩 entry 之后的新消息。旧记录仍在 session 文件中；当前请求使用的是选出的有效视图。错误响应也可能保留在历史中，但在重试前从 live context 移除。[S: S-008, S-010]

## 压缩后的消息列表长什么样

压缩成功后，Pi 把最新摘要放在消息列表前面，接上从 `firstKeptEntryId` 开始保留的消息，再接压缩记录之后加入的消息。近期消息分别保留角色、内容和调用关联关系。摘要内部可以合并历史总结与长任务前半段总结，但整段会话仍是一个消息数组。[S: S-008, S-022, S-035]

例如，较早的排查过程已经总结；近期原文保留了读启动脚本的调用、结果和回答；之后你又要求检查 Docker 配置。省略时间戳和 usage 等字段，内部列表可以表示为：

```js
[
  {
    role: "compactionSummary",
    summary: "正在排查启动端口，之前已检查项目配置……"
  },
  {
    role: "assistant",
    content: [{
      type: "toolCall", id: "call_1", name: "read",
      arguments: { path: "scripts/start.sh" }
    }]
  },
  {
    role: "toolResult", toolCallId: "call_1", toolName: "read",
    content: [{ type: "text", text: "启动脚本内容……" }]
  },
  {
    role: "assistant",
    content: [{ type: "text", text: "启动脚本会读取 PORT 环境变量。" }]
  },
  {
    role: "user",
    content: [{ type: "text", text: "生产环境 PORT=8080，请检查 Docker 配置。" }]
  }
]
```

发送前，`convertToLlm` 将第一条摘要包装成带说明和 `<summary>` 标签的 user 消息；普通 assistant、toolResult 和 user 继续保留对应类型。system prompt 与工具定义在统一请求 context 中单独加入：[S: S-001, S-022]

```text
systemPrompt：当前系统提示
messages：摘要 user → 保留的 assistant / toolResult 等消息 → 后续新消息
tools：当前启用的工具定义
```

立即压缩完成时，尚未消费的队列输入还不在这份列表中，之后才会加入。到了 provider 适配器，system prompt 又可能成为 API messages 中的 system/developer 消息；模型服务还会把角色和工具定义编码为具体模型的输入。完整过程见[请求编码与两种模型示例](18-model-input-encoding.md)。

## 压缩期间提交的新输入怎样接上来

假设 Pi 已完成一轮排查，正在做阈值压缩：把消息 1～80 总结成摘要，保留消息 81～100。此时你在终端提交：“生产环境设置了 PORT=8080，接下来检查 Docker 配置。”这些消息编号只用来说明先后关系。

摘要调用使用开始时准备好的历史材料。终端编辑框继续接收输入，普通文本先存入 `compactionQueuedMessages`，并显示等待压缩完成的提示。新要求不会被临时加入已经进行中的摘要调用，也不会在摘要生成的同时启动相应的任务处理。[S: S-036]

```text
开始压缩：准备旧历史，调用模型生成摘要
用户补充：新要求暂存在输入队列
摘要完成：保存 compaction entry，重建为“摘要 + 保留消息”
继续处理：提交队列输入，模型看到“摘要 + 保留消息 + 新要求”
```

`compaction_end` 通知终端调用 `flushCompactionQueue()`。具体怎样续跑，取决于是否还有待恢复的运行：[S: S-036]

- 没有待恢复重试时，第一条排队的普通输入通过 `session.prompt()` 提交；其余输入按记录的 steering / follow-up 类型进入相应队列。上一轮已经完成的回答不会因此重答。
- 有待恢复重试时，输入按原类型通过 `session.steer()` 或 `session.followUp()` 入队，由恢复后的循环在相应边界消费。follow-up 仍需等待当前工作与 steering 处理完。

终端的压缩暂存队列和 Agent 本身的 steering / follow-up 队列是两处状态。其他入口或扩展已经放入 Agent 队列的消息，则由 `AgentSession` 的续跑检查衔接：自动压缩成功后，没有恢复重试要求时，`_runAutoCompaction()` 返回 `agent.hasQueuedMessages()` 的结果，由外层运行流程决定是否调用 `Agent.continue()`。这个压缩方法本身并不直接调用 continue。[S: S-021, X: X-005]

本例描述压缩成功后的普通输入路径。已注册的扩展命令在终端有单独入口，不能据此推断所有命令都必须等待压缩。终端发送排队消息失败时会恢复暂存队列并显示错误。[S: S-036]

源码：[压缩期间提交](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/modes/interactive/interactive-mode.ts#L2783)、[压缩结束通知](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/modes/interactive/interactive-mode.ts#L3059)、[队列转交](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/modes/interactive/interactive-mode.ts#L3990)。
