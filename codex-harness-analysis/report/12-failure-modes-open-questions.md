# 失败模式与开放问题

## 已验证失败

- `Unexpected message role`: supplied SiFlow endpoint 与 stock Codex request role 不兼容。[R: `R-002`]
- `namespace` schema rejected: V1 multi-agent 的 provider capability 要求高于普通 function tools。[R: `R-003`]
- unsupported tool: router 记录 error，但把结果回流并允许 turn 完成。[X: `X-003`]
- forbidden escalation: `never` policy 在进程执行前拒绝。[X: `X-004`, `X-007`]

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
