# 失败模式与开放问题

## 已验证失败

- `Unexpected message role`: supplied SiFlow endpoint 与 stock Codex request role 不兼容。[R: `R-002`]
- `namespace` schema rejected: V1 multi-agent 的 provider capability 要求高于普通 function tools。[R: `R-003`]
- unsupported tool: router 记录 error，但把结果回流并允许 turn 完成。[X: `X-003`]
- forbidden escalation: `never` policy 在进程执行前拒绝。[X: `X-004`, `X-007`]

<!-- EXPLANATION:failure-terms -->
## 这里的“失败”分三类

- **Provider dialect failure**：HTTP endpoint 存在，但不接受 Codex 使用的 message role 或 tool schema；这不是 agent loop 自身失败。
- **Handled tool failure**：unknown tool 或 policy deny 被包装为 model-facing output，当前 turn 仍可能恢复并完成。
- **Durability/recovery failure**：timeout、process crash、partial rollout、corruption 或 workspace drift，可能影响跨 turn/process 恢复；本轮大多尚未故障注入。

因此下面的开放问题既包括产品风险，也包括分析覆盖缺口。`V2 mailbox preemption` 指 parent 在 reasoning/commentary 期间收到 child mail 时提前结束当前 sampling、转入吸收消息的 follow-up；它不等于强制终止整个 parent session。[S: `S-027`]

## 高价值未知项

1. pre-turn、mid-turn、remote/local compaction 是否在同一超长 scenario 下保持语义等价？
2. MCP、dynamic/hosted tools 是否全部经过与 exec 相同的 approval/sandbox 边界？答案很可能按 handler 不同，必须逐类验证。
3. V2 mailbox preemption、child crash 与 root cancel 的事件/rollout 顺序是什么？
4. rollout 尾部截断、中间 corruption、store flush failure 后 resume 是拒绝、修复还是部分恢复？
5. workspace 在 resume/fork 和多个 child 并发写入时如何检测 drift/conflict？
6. OTel、app-server events、rollout items 是否可用同一 turn/call id 无歧义对齐？

## 下一轮优先实验

优先级最高的是一个本地 translation proxy：只把 developer role 与 namespace tools 降解成 endpoint 可接受格式，并完整记录变换。它能把“真实模型不可运行”从 blocker 变成可比较条件，同时诚实保留 stock 与 adapted 两种架构。

其次是 fault injection：oversized tool output 触发 compaction；写入后拒绝/超时验证 side-effect reporting；截断 rollout 验证 resume；两个 child 竞争同一 fixture 文件验证 workspace ownership。

| 优先级 | 实验 | 要区分的机制 | 通过标准 | 仍不能推出 |
|---|---|---|---|---|
| P0 | stock/adapted provider 对照 | endpoint 方言不兼容，还是 Codex loop 本身失败 | adapter 只改 role/schema；两侧请求 hash、变换日志和 tool feedback 均可审计 | adapted 成功不代表 stock Codex 兼容 |
| P0 | shell / unified exec / direct `apply_patch` 对照 | 普通 exec policy 与专用 patch governance 的边界 | 三个入口分别记录 approval key、sandbox runtime 与是否创建 process | 单平台结果不能代表所有 sandbox backend |
| P1 | compaction 阈值与顺序 | pre-turn、mid-turn、remote/local replacement 是否等价 | token snapshot、replacement、rollout 与 resume 顺序可重放 | 一次长上下文不能覆盖所有模型窗口变化 |
| P1 | rollout corruption/flush failure | durable history 在部分写入后的恢复模型 | 对尾部截断、中段损坏、flush error 给出拒绝/修复/部分恢复分类 | conversation 恢复不表示 workspace 回滚 |
| P1 | V2 child crash/cancel/mailbox | parent sampling、mailbox 和 terminal events 的因果顺序 | turn/call/agent id 可在 events、rollout 与 provider log 中对齐 | V1 的结果不能外推到 V2 |
| P2 | 多 child workspace 冲突 | context 隔离下的共享文件竞争 | 两 child 写同一 fixture 时观察到明确冲突、序列化或最后写入语义 | 单文件结果不覆盖 git 或目录级冲突 |
