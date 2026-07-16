# 接口与生命周期

Codex 的接口层比“CLI 包一层 core”更丰富，但共享同一个 thread/session 概念。

`codex-rs/cli/src/main.rs` 的 `Subcommand` 将 `exec`、`mcp-server`、`app-server` 等模式显式分派；无 subcommand 时进入 TUI。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/cli/src/main.rs#L124) [S: `S-001`]

app-server 不是另一个 agent runtime。它把 thread start/resume/fork、turn start/interrupt 与通知映射成双向 JSON-RPC；processor 与 outbound writer 分离，避免慢客户端直接卡住处理 loop。[文档](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/app-server/README.md#L1) [源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/app-server/src/lib.rs#L150) [D: `D-003`] [S: `S-023`]

常规生命周期可压缩为：surface 创建/恢复 thread → session 接受 op → `RegularTask` 发出 `TurnStarted` → `run_turn` → flush rollout → `TurnComplete/TurnAborted` → session 仍可接受后续 turn。tool follow-up 发生在同一次 `run_turn` 的 sampling loop 内；如果存在排队或 steer 的新用户输入，`RegularTask` 还可以在同一外层 turn 里再执行一次 `run_turn`。是否是新 turn 应以 `TurnStarted/TurnComplete` 及 `turn_id` 为准，不能按模型请求次数判断。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tasks/regular.rs#L37) [S: `S-002`]

这一区分很关键：**turn、session、process 的终止条件不同**。一次 model/tool error 可以结束 turn，却不必销毁 thread；app-server 客户端断开也不能被简单等同于 durable thread 删除。

<!-- EXPLANATION:lifecycle-terms -->
## Thread、Session、Turn 的包含关系

先把它们看成三种不同时间尺度的对象：**thread 是可持久化的对话身份，session 是当前进程中运行该 thread 的实例，turn 是 session 正在处理的一次任务边界**。用运行时所有权表示是：

```text
Codex process
└─ ThreadManager                         0..N 个已加载 thread
   └─ thread_id = T                    可持久化的逻辑身份
      └─ CodexThread handle
         └─ Session S                  当前进程的 live runtime
            └─ active_turn = None | U  同一时刻最多 1 个
               └─ Turn U
                  ├─ model request 1
                  ├─ tool call / tool result
                  └─ model request 2 ... N
```

这是运行时关系，不是持久化文件的目录结构。`ThreadManager` 在内存中维护 `ThreadId -> Arc<CodexThread>` 映射；`CodexThread` 是向 interface 提供 submit/event/shutdown 的 handle，内部包装真正的 `Session`。对同一个 manager，如果某个 thread 已经在运行，resume 会返回现有 handle，而不是再建一个并发 session。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/thread_manager.rs#L182) [源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/thread_manager.rs#L1526)

### 1. Thread：“这是哪段对话”

Thread 是跨 turn、也可以跨进程的逻辑身份。它的核心是 `thread_id`、会话历史和 metadata，而不是某个常驻 Rust 对象。

- `start` 产生新 `thread_id` 和新历史。
- `resume` 使用原 `thread_id` 加载原历史；新进程会为它创建新的 live session。
- `fork` 复制选定的历史快照，但分配**新** `thread_id`，因此不是在原 thread 内新建一个 turn。
- local store 通常用 rollout JSONL 保存 canonical history，用 SQLite 保存可查询 metadata；`LiveThread` 隔离了 core 与具体存储后端。

Thread 记录“Codex 看过和产生过什么”，但它不拥有 workspace 的版本。恢复 thread 会恢复对话 history，不会自动把文件系统回滚到旧状态。[D: `D-004`] [S: `S-018`] [X: `X-006`]

### 2. Session：“谁正在运行这段对话”

Session 是一个 live、in-process 的运行对象。它带着同一个 `thread_id`，但还拥有只在当前运行期有意义的状态：event channel、model/provider 配置、permission profile、MCP/services、input queue、内存 conversation state，以及指向持久化后端的 `LiveThread` handle。

`Session` 源码明确声明“at most 1 running task at a time”，并以 `active_turn: Mutex<Option<ActiveTurn>>` 表示这个约束。它在生命周期中可以顺序处理多个 turn；开始替代任务时，旧任务会通过 cancellation 边界中止。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/session/session.rs#L25) [源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tasks/mod.rs#L325)

因此，一个 thread 在时间上可以对应多个先后出现的 session：进程 A 中的 `S1` 退出后，进程 B resume 同一 thread 会创建 `S2`。`S1` 与 `S2` 的内存地址、channel 和 service 对象不同，但它们共享同一个 `thread_id` 和已持久化历史。

### 3. Turn：“这一次任务什么时候结束”

Turn 是 `TurnStarted` 到 `TurnComplete` 或 `TurnAborted` 之间的调度单位。它有自己的 `turn_id`/`TurnContext` 和 mutable `TurnState`：本轮使用的 model、cwd/environment、approval/permission profile、dynamic tools、取消 token、token usage，以及正在等待的 approval、user input 或 dynamic-tool response。

**Turn 不等于一次模型 API 请求。** 一个 turn 可以是：

```text
TurnStarted(U1)
  -> model request #1
  -> model proposes exec_command
  -> permission + sandbox + tool execution
  -> tool result appended to history
  -> model request #2
  -> final assistant message
  -> flush rollout
TurnComplete(U1)
```

两次 model request、tool call 和 tool result 都属于同一个 `U1`。只有下一次发出新的 `TurnStarted(U2)` 才是新 turn。`TurnComplete/TurnAborted` 后，`active_turn` 被清空并再次 flush terminal event，session 回到 idle，thread 不因此消失。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tasks/mod.rs#L756) [S: `S-002`]

### 4. 一个跨进程的具体例子

| 时间 | 发生的事 | 仍然相同 | 已经变化 |
|---|---|---|---|
| 进程 A 启动 | start thread `T`，建立 session `S1` | `thread_id=T` | 新 session |
| 用户提问 | `S1` 开始 turn `U1`，内含两次 model request 和一次 tool call | `T`, `S1`, `U1` | model request/step 变化 |
| `U1` 完成 | terminal event 和 history flush，`S1` 继续 idle | `T`, `S1` | `active_turn: U1 -> None` |
| 进程 A 退出 | `S1` 消失，rollout 保留 | `T` 和 durable history | live session 消失 |
| 进程 B resume | 加载 `T` 并建立 `S2` | 同一 `thread_id=T` 和旧 history | `S2` 是新 live object |
| 用户再提问 | `S2` 开始新 turn `U2` | `T` | session 和 turn 都与首轮不同 |

本轮的跨进程实验已观察到：第二个进程 resume 后 `thread_id` 不变，provider input 包含首轮 assistant history。这直接验证了“thread 跨进程，session 不跨进程”的主路径。[X: `X-006`]

### 5. 失败会影响到哪一层

| 事件 | 通常结束或改变的边界 | 不能自动推出的结论 |
|---|---|---|
| 单次 provider stream 错误 | 当前 sampling/request，可能在 turn 内有界 retry | 不等于 thread 已删除 |
| tool error | 错误可以作为 tool output 回到当前 turn | 不一定结束 session |
| `TurnAborted` | 当前 turn | session 仍可接受新 turn |
| interface/websocket 断开 | 客户端连接 | 不等于 durable thread 被删除 |
| session/process shutdown | live runtime | flush 成功时 thread 仍可 resume |
| thread archive/delete | durable identity/history 的可见性或存在性 | 不会自动回滚 workspace |

所以最简短的记忆方式是：**Thread 回答“哪段对话”，Session 回答“哪个 live runtime 正在处理它”，Turn 回答“当前这次任务的边界在哪里”。** Interface 只决定这些操作通过 TUI、`exec`、app-server 还是 MCP server 进入 core。[D: `D-003`, `D-004`] [S: `S-002`, `S-018`]

动态验证覆盖了 `exec` 的 start 与 resume，但没有启动 TUI、app-server websocket 或 MCP server。因此“共享 core”是高置信静态结论，接口特有背压/序列化行为仍是局部覆盖。
