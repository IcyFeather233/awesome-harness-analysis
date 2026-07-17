# 05 模型、工具与扩展

![Tool and extension surface](../diagrams/generated/pi-extension-surface.png)

> 图 4（gpt-image-2 读者插图）：三列分别回答模型看到什么、能调用什么、action 如何运行；默认 host path 与可选 gate/container 明确分离。图像的 prompt、output hash 与语义审查见[生成图 metadata](../diagrams/generated/metadata.json)；三类控制点来自[Harness IR](../hir.json)和下列 Evidence IDs。Evidence: `D-002`, `D-004`, `D-007`, `S-001`, `S-002`, `S-003`, `S-007`, `S-015`, `S-017`, `R-002`。

## Model boundary

`pi-ai` 的运行时单位是 Provider：id/name/base URL、auth、model catalog、`stream` 和 `streamSimple`。`ModelsImpl` 在每次请求前解析 provider auth，合并 base URL/header/env，再把 model/context 分派给拥有该 model 的 provider。[S: S-012]

本轮用隔离 `models.json` 注册 `siflow/qwen3.6-35ba3b`：`--list-models` 成功，随后真实 text/read 场景都通过相同 provider abstraction。[R: R-005, R-001, R-002]

## Tool registry

`AgentSession._refreshToolRegistry()` 合并：

- built-in tool definitions；
- extension `registerTool()`；
- SDK custom tools；
- CLI/settings allowlist 与 denylist。

extension/custom tool 同名时按 load/order 进入最终 map；resource loader 会产生 conflict diagnostic，但机制仍允许扩展覆盖/替换能力。[S: S-003]

## Hook 注入点

| 注入点 | 发生时机 | 能改变什么 | 失败/阻断语义 | 权限边界 |
|---|---|---|---|---|
| `input` | 用户输入进入产品层时 | 标记 handled，或变换输入 | handled 可短路普通 prompt；错误由 extension runtime 报告 | host 进程内 |
| `before_agent_start` | 每次 prompt 调 low-level loop 前 | 加 custom messages，或替换本轮 system prompt | 可改变该 run 的初始 context | host 进程内 |
| `context` | 每次 provider request 前 | 变换将要发送的 messages | 影响 request，不必改写 durable session | host 进程内 |
| `tool_call` | 参数 validation 后、`execute` 前 | block 调用并返回理由 | 可阻止该 tool handler；不是不可绕过的全局 gate | host 进程内、可选 |
| `tool_result` | handler 返回后 | 改 content、details、`isError` | 模型下一 request 看到变换后的结果 | host 进程内 |
| provider hooks | request/payload/response 边界 | 观察或修改 provider 交互 | 可能改变兼容性、日志和 redaction | host 进程内 |
| session/tree hooks | switch/fork/compact/tree 操作前后 | 观察、阻止或附加生命周期行为 | 部分 post-commit failure 不能回滚已提交状态 | host 进程内 |

这些 hooks 是控制面，不是被隔离的 plugin VM；extension TypeScript 与主进程同权限。`tool_call` block 只覆盖经过该 registry/hook pipeline 的调用，extension 自己直接访问 filesystem/process/network 不受它约束。[D: D-002]

## 不内置的协议

核心明确不内置 MCP。要么把 CLI + README 暴露成 skill，要么 extension 自行注册 MCP tool。因而 HIR 中没有把 MCPServer 画成现存核心组件。[D: D-004]
