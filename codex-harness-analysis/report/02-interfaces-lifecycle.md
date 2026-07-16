# 接口与生命周期

Codex 的接口层比“CLI 包一层 core”更丰富，但共享同一个 thread/session 概念。

`codex-rs/cli/src/main.rs` 的 `Subcommand` 将 `exec`、`mcp-server`、`app-server` 等模式显式分派；无 subcommand 时进入 TUI。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/cli/src/main.rs#L124) [S: `S-001`]

app-server 不是另一个 agent runtime。它把 thread start/resume/fork、turn start/interrupt 与通知映射成双向 JSON-RPC；processor 与 outbound writer 分离，避免慢客户端直接卡住处理 loop。[文档](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/app-server/README.md#L1) [源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/app-server/src/lib.rs#L150) [D: `D-003`] [S: `S-023`]

常规生命周期可压缩为：surface 创建/恢复 thread → session 接受 op → `RegularTask` 发出 `TurnStarted` → `run_turn` → flush rollout → `TurnComplete/TurnAborted` → session 仍可接受后续 turn。`RegularTask` 只在队列里存在新用户输入时继续启动 turn；tool follow-up 则发生在同一 `run_turn` 内。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tasks/regular.rs#L37) [S: `S-002`]

这一区分很关键：**turn、session、process 的终止条件不同**。一次 model/tool error 可以结束 turn，却不必销毁 thread；app-server 客户端断开也不能被简单等同于 durable thread 删除。

动态验证覆盖了 `exec` 的 start 与 resume，但没有启动 TUI、app-server websocket 或 MCP server。因此“共享 core”是高置信静态结论，接口特有背压/序列化行为仍是局部覆盖。
