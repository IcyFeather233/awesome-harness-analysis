# 设计空间与 Running Example

![Codex design space](../diagrams/generated/codex-design-space.png)

> 图 8（gpt-image-2 读者插图）：四行把可观察约束、恢复出的机制和分析者综合的 tradeoff 分开；右列不是作者声明。Evidence: `D-002`, `D-004`, `D-007`, `S-005`, `S-009`, `S-012`, `S-014`, `S-018`, `S-025`, `X-002`, `X-004`, `X-006`。

<!-- EXPLANATION:design-space-figure -->
## 怎么读图 8

每一行都从左向右读：`Constraint` 是 harness 必须面对的问题，`Recovered mechanism` 是在 v0.144.5 源码中找到的当前实现，`Analyst synthesis` 是由实现推导出的工程代价。最后一列带 `INFERENCE`，是为了明确它不是 OpenAI 作者声明。

例如第一行不是说“rollout 一定会损坏”，而是说：既然跨进程 resume 依赖 `LiveThread + Rollout`，那么 flush 失败、尾部截断和 corruption 就成为必须测试的边界。第四行同理：`Exec Policy + Sandbox` 提供分层治理，但跨平台实现不同，所以不能用一次 Linux deny 实验推出所有平台都等价。[S: `S-012`–`S-014`, `S-018`, `S-019`] [X: `X-004`, `X-006`]

## 六个反复出现的设计问题

| 问题 | v0.144.5 的当前机制 | 可替代方案 | 部署约束、权衡与边界 | 证据与置信度 |
|---|---|---|---|---|
| 谁拥有耐久状态？ | `ThreadStore` 定义后端中立接口，`LiveThread` 负责活动 thread 的 append/flush，local backend 用 rollout JSONL 保存 canonical history。 | 只保存在 UI 进程内存，或为每轮建立数据库/文件系统事务 checkpoint。 | 跨进程 resume/fork 清晰，但 flush、尾部损坏和 workspace drift 成为 correctness 边界；本轮只验证正常尾部写入。 | `S-018`, `S-019`, `X-006`；高 |
| 每轮模型看见什么？ | `ContextManager` 保留 history，`WorldState` 维护 typed snapshot/diff，`StepContext` 冻结本次请求的 model、cwd、policy 与 tool exposure。 | 每轮从一个 canonical store 重建完整 prompt snapshot。 | 减少重复注入并保护并发请求配置，但 baseline、cache prefix 与动态状态同步更难推理；完整 source differential 未跑。 | `S-004`–`S-006`, `I-001`；中 |
| 能力何时可见？ | ToolSpecPlan 把 registered handler 与本轮 model-visible specs 分开，并按 provider、feature、agent depth、MCP/extension 状态选择 exposure。 | 所有已注册工具始终发送给模型。 | 动态适配能力强，但静态 registry、模型可见、实际 requested、获准执行是四个不同事实。 | `S-009`, `X-005`；高 |
| 副作用如何治理？ | 真正的进程 exec 先计算 rule/approval requirement，再经 permission profile 选择 platform sandbox；apply_patch 走专用 patch governance。 | 只做用户审批、只做 OS sandbox，或所有 action 统一 capability broker。 | 分层治理能区分“允许”与“可触达范围”，但平台/mode/tool handler 矩阵复杂；一次 Linux deny 不能覆盖 MCP、dynamic tool 或 patch 路径。 | `D-002`, `S-012`–`S-014`, `S-028`, `I-002`；中 |
| 多 agent 如何隔离？ | Child 拥有独立 thread/channel/context/history，继承 effective model/policy/cwd，并共享 AgentControl 与 workspace；V1/V2 分 gate。 | 单 context 角色切换，或每 child 独立 worktree/container/remote runtime。 | Root context 增长受控，但共享文件会竞争；本轮只运行 V1，V2 mailbox 与多 child 冲突仍是静态边界。 | `S-015`–`S-017`, `S-027`, `X-005`；中 |
| 失败后从哪恢复？ | Provider stream retry、tool/turn cancellation、rollout flush 和跨进程 thread resume 分别处理不同失败域。 | Fail-fast 整体重启，或统一事务 checkpoint/rollback。 | 局部恢复成本低且 session 可继续，但不存在覆盖 provider、tool、process、durable state 与 workspace 的单一回滚点。 | `S-008`, `S-022`, `X-006`；中 |

## Running example：一次确定性的 read tool turn

本报告用 `X-SCENARIO-002` 作为主线，因为它只要求 harness 机制，不依赖模型随机选择工具：本地 Responses fixture 首次强制返回 `exec_command(cat FACTS.txt)`；只有第二次请求包含同一 `call_id` 的 `function_call_output` 时，fixture 才返回 `HXA-1445`。

观测顺序是：请求 1（3 个 message items）→ function call → 只读执行 → tool output 进入 history → 请求 2（新增 function call/output）→ assistant final → turn complete。这个 trace 支持核心循环和 context feedback，但**不支持** compaction、MCP、write sandbox 或 subagent 等没有发生的路径。[X: `X-002`]

权限拒绝、subagent 与 resume 分别来自 `X-SCENARIO-004/005/006`，在后文作为独立支路附着，避免把多个实验拼成一次不存在的“全功能运行”。
