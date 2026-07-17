# 运行实验

## 实验矩阵

| 场景 | 模式与关键配置 | 区分性断言与实际结果 | OS 可见副作用 | 保留工件 | 不能推出什么 |
|---|---|---|---|---|---|
| R-001 | 官方 binary + 真实 SiFlow，最小 Responses。 | Stock request 是否直接可运行；HTTP 400 `Unexpected message role`，在模型输出前失败。 | 无 tool call、无 workspace 写入。 | `traces/raw/real-siflow-minimal.jsonl`。 | 只证明该日期/endpoint 方言不兼容，不证明 Responses 协议整体不可用。 |
| R-002 | 官方 binary + SiFlow + V1 namespace tool。 | Endpoint 是否接受 Codex namespace schema；HTTP 400 schema reject。 | 无 tool call。 | Normalized namespace trace。 | 不能推出关闭 V1 后的所有 tool schema 都失败。 |
| X-001 | Local deterministic SSE，无工具。 | 无 tool 时应正常停止；得到 `SCRIPTED_OK` 与 turn.completed。 | 仅临时 home/workspace。 | Normalized trace + raw request log。 | 不覆盖 tool、policy、compaction 或 persistence。 |
| X-002 | Deterministic SSE，read-only/never，fixture 强制 `exec_command(cat FACTS.txt)`。 | 第二 request 必须包含同 call id 的 output；观察到 function call/output 并返回 `HXA-1445`。 | 只读 `FACTS.txt`。 | `traces/raw/read-tool-requests.jsonl`（未另建 normalized 文件）。 | 不能评价模型自主选 tool 的质量，也不覆盖 write/sandbox。 |
| X-003 | Deterministic SSE，请求不存在工具。 | Unsupported error 是否回流模型；观察到 model-facing output 与 turn completion。 | 无。 | Normalized unknown-tool trace。 | 不证明所有 handler exception 都可恢复。 |
| X-004 | Deterministic SSE，`approval_policy=never`，请求 escalation。 | Policy 是否先于 process 拒绝；观察到 error 回流并完成。 | Marker 未创建，目录清单与文件 hash 不变。 | Denial normalized trace + `X-007` side-effect trace。 | 只覆盖该普通 exec escalation；不覆盖 patch/MCP/dynamic tool。 |
| X-005 | Deterministic SSE + Multi-agent V1，默认 depth=1。 | Child 是否独立 request 且 depth-limited；观察到 child thread、不同 digest、child 无 namespace。 | 共享临时 workspace，无写入。 | `traces/raw/subagent-spawn-requests.jsonl`。 | 不覆盖 join/cancel/crash、并发文件竞争或 V2 mailbox。 |
| X-006 | Deterministic SSE + local rollout，两个进程。 | Resume 是否保持 thread/history；id 相同，provider input 3→5。 | 只写临时 rollout。 | `traces/raw/resume-requests.jsonl` 与临时 rollout 记录。 | 只验证正常尾部；不覆盖 partial write、corruption、fork 或 workspace drift。 |

<!-- EXPLANATION:experiment-modes -->
## 表中模式与结果怎么解释

`R-*` 是官方 Codex binary 连接真实 SiFlow endpoint 的兼容性观察；失败仍是有效结果，因为它说明 stock request 在模型输出前被哪一层拒绝。`X-*` 是 deterministic Responses fixture：fixture 不理解任务，只按预先写好的 call id/item type 强制 Codex 走指定分支，因此适合验证 harness control flow。

`passed` 表示预先声明的区分性断言成立，不表示整个功能面都正确。例如 X-004 证明 `never` 在该 escalation 请求上先于 process 拒绝，并用文件哈希检查了无副作用；它没有证明所有 shell/MCP/dynamic tool 都经过同一 gate。详细配置和 trace 路径在 [scenario catalog](../scenarios/catalog.json)。

## 为什么真实模型没有伪装成成功

SiFlow 的 `/responses` 基础 SSE probe 能返回 reasoning/message/completed，说明 endpoint 不是完全不支持 Responses。但 Codex 发出的真实请求包含更具体的 dialect：developer role，以及 V1 的 namespace tool schema。当前 endpoint 均拒绝，因此本报告不声称完成“真实模型 agent tool turn”。[R: `R-002`, `R-003`]

如果引入 role/namespace translation proxy，就可以继续测真实 Qwen 行为，但那会改变系统边界；报告必须把 proxy 作为新节点和实验条件，而不能把其结果归因于 stock Codex 0.144.5。

## 为什么 deterministic fixture 有效

fixture 不解释 prompt，也不随机选择工具。它以 call id 和 input item type 作为门槛，强制 harness 进入指定分支；请求日志只保留 role/type/tool name 和文本哈希。这适合验证 loop、router、policy、subagent、resume 等机制，但不评价模型质量。

完整定义见 [scenario catalog](../scenarios/catalog.json)，服务器代码见 [scripted_responses_server.py](../experiments/scripted_responses_server.py)。
