# Subagent 与 Delegation

![Codex subagent topology](../diagrams/generated/codex-subagent-topology.png)

> 图 6（gpt-image-2 读者插图）：V1/V2 是两条条件路径；本轮只运行 V1。Child 拥有独立 context/history/thread，继承 policy/cwd，workspace 共享；默认 `max_depth=1` 使 child 不再暴露 spawn namespace。Evidence: `S-015`–`S-017`, `X-005`。

## 静态拓扑

一个 root tree 共享 `AgentControl`、registry/limiter/rollout budget；`CodexDelegate` 创建独立 child Codex，拥有自己的 channels、session、context 与 history，同时继承 effective config、provider、approval、sandbox、cwd、MCP、skills 和 tools。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/codex_delegate.rs#L70) [S: `S-016`]

历史继承不是单一布尔值：full-history fork 保留 user/developer/final assistant 和 metadata；truncated fork 强制 child 重建上下文。[S: `S-017`]

默认配置中 V1 `multi_agent` 开启，V2 关闭；默认最大 child threads 为 6，V2 并发 session 为 4，深度为 1。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/config/mod.rs#L203) [S: `S-015`] 这些数字是版本/配置条件，不应画成 harness 的普遍常数。

## 动态观察

`X-SCENARIO-005` 的 root request 暴露一个 `multi_agent_v1` namespace，随后 `spawn_agent` event 返回新的 child thread id。日志出现三个 provider requests：root 首次、root tool-output follow-up、child 首次。child request 有不同 input digest，且不再带 namespace，符合默认 depth limit。[X: `X-005`]

尚未验证：父进程等待/聚合 child final、child crash、cancel propagation、多个 child 同文件写冲突、V2 mailbox/preemption。图中这些未运行机制均不能用实线。
