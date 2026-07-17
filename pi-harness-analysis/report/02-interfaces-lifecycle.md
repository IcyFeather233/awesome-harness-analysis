# 02 入口与生命周期

## 入口收敛

`main()` 解析 CLI、session、trust、资源和模型，然后创建 `AgentSessionRuntime`。最终只有 UI 适配不同：RPC 进入 `runRpcMode()`，TUI 进入 `InteractiveMode`，print/JSON 进入 `runPrintMode()`；它们共享同一个 `AgentSession`。[S: S-012, S-013]

```text
CLI args / stdin
  -> main()
  -> SessionManager + cwd-bound services
  -> AgentSessionRuntime
  -> AgentSession
  -> interactive | print/json | rpc adapter
```

关键源码：`packages/coding-agent/src/main.ts:650-857`、`packages/coding-agent/src/core/agent-session-runtime.ts:67-353`。

## 生命周期

1. 选择/创建/恢复 `SessionManager`。
2. 以 effective cwd 创建 settings、auth、model registry、resource loader。
3. 解析 project trust 后装载最终 extension/resource 集合。
4. 创建 `AgentSession`，绑定目标 mode 的 extension UI/context。
5. prompt 后进入共享 loop；JSON/RPC 只是转发结构化 event。
6. session switch/new/fork/import 会先发 `session_shutdown`，再重建 cwd-bound runtime，而不是只替换 message array。[S: S-014]

## 模式差异

- Interactive 有 trust prompt 和完整 TUI。
- Print 输出最终 assistant text；JSON 输出每个 session event。
- RPC 用 LF-delimited JSON 收命令、回 response，并并行输出 agent events 与 extension UI request。
- 非交互模式没有 project trust UI；default `ask` 在无既有决策时等价于不信任项目资源。[S: S-006]

本轮真实运行覆盖 JSON mode；TUI 与 RPC 源码已检查但未端到端启动。

## 对象与结束边界

| 对象/层 | 谁创建或拥有 | 生命周期 | Durable 内容 | 结束时发生什么 |
|---|---|---|---|---|
| CLI mode adapter | `main()` 按 interactive/print/JSON/RPC 选择 | 单进程 UI/transport 生命周期 | 自身不持久化 conversation | 断开 adapter 不等于删除 session 文件 |
| `AgentSessionRuntime` | main 的 cwd-bound runtime factory | 当前 cwd/session 组合 | settings/auth/resource decisions 由各自 store 持久 | session switch/new/fork/import 时先 shutdown，再重建服务 |
| `AgentSession` | 当前 Coding Agent 产品路径 | 可处理多次 prompt，直到 switch/shutdown | message/compaction 等通过 `SessionManager` 追加 JSONL | `agent_end` 后仍可能 retry/compact/queue；`agent_settled` 才是产品空闲 |
| Low-level `Agent` / `runAgentLoop` | `AgentSession` 每次 prompt 驱动 | 一次 agent run，可含多次 turn | transcript 由上层 session 选择是否保存 | 无工具、steering、follow-up 后发 `agent_end` |
| Session tree | `SessionManager` | 跨 prompt、进程、branch/fork | JSONL v3 header + parent-linked entries | resume 重建 active branch，不重建旧 workspace |
