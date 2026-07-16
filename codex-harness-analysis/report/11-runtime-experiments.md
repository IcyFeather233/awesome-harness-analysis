# 运行实验

## 实验矩阵

| 场景 | 模式 | 区分性断言 | 结果 | 副作用 |
|---|---|---|---|---|
| R-001 | 真实 SiFlow | stock Codex 最小 Responses 能否直接运行 | 400: Unexpected message role | 无 tool call |
| R-002 | 真实 SiFlow + V1 | endpoint 是否接受 namespace tool | 400: schema rejects namespace | 无 tool call |
| X-001 | deterministic SSE | 无 tool 时是否正常停止 | `SCRIPTED_OK`, turn.completed | 无 |
| X-002 | deterministic SSE | tool output 是否进入第二 request | input types 新增 call/output，返回 `HXA-1445` | 只读 FACTS.txt |
| X-003 | deterministic SSE | 未知 tool 是否可恢复 | unsupported error 回流，turn completed | 无 |
| X-004 | deterministic SSE | never 是否前置拒绝 escalation | policy error 回流，turn completed | marker 未创建 |
| X-005 | deterministic SSE + V1 | child 是否独立 request/depth-limited | child thread + 独立 digest/tool surface | 无 |
| X-006 | deterministic SSE + persistence | resume 是否恢复同 thread/history | id 相同，input 3→5 | 仅临时 rollout |

## 为什么真实模型没有伪装成成功

SiFlow 的 `/responses` 基础 SSE probe 能返回 reasoning/message/completed，说明 endpoint 不是完全不支持 Responses。但 Codex 发出的真实请求包含更具体的 dialect：developer role，以及 V1 的 namespace tool schema。当前 endpoint 均拒绝，因此本报告不声称完成“真实模型 agent tool turn”。[R: `R-002`, `R-003`]

如果引入 role/namespace translation proxy，就可以继续测真实 Qwen 行为，但那会改变系统边界；报告必须把 proxy 作为新节点和实验条件，而不能把其结果归因于 stock Codex 0.144.5。

## 为什么 deterministic fixture 有效

fixture 不解释 prompt，也不随机选择工具。它以 call id 和 input item type 作为门槛，强制 harness 进入指定分支；请求日志只保留 role/type/tool name 和文本哈希。这适合验证 loop、router、policy、subagent、resume 等机制，但不评价模型质量。

完整定义见 [scenario catalog](../scenarios/catalog.json)，服务器代码见 [scripted_responses_server.py](../experiments/scripted_responses_server.py)。
