# Session、持久化与恢复

![Codex persistence lifecycle](../diagrams/generated/codex-persistence-lifecycle.png)

> 图 7（gpt-image-2 读者插图）：主轴是 session items → LiveThread → rollout JSONL → resume → restored history；workspace 是并行现实状态，不会因 resume 自动回滚。Evidence: `D-004`, `S-018`, `S-019`, `S-022`, `X-006`。

## Live 与 durable state

`ThreadStore` 是 storage-neutral interface，覆盖 create/resume/append/persist/flush/shutdown/load/list/archive/delete；`LiveThread` 是活动持久化边界，resume 时加载 history，append 时先做 persistence filtering 和 metadata patch。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/thread-store/src/live_thread.rs#L91) [D: `D-004`] [S: `S-018`]

local store 的 rollout 文件采用 `rollout-<timestamp>-<thread-id>.jsonl`。后台 writer 在 I/O error 时保留 pending suffix，turn complete 前 task 会 flush，并把失败作为 warning/retry surface。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/rollout/src/recorder.rs#L1511) [S: `S-019`, `S-022`]

## 跨进程验证

首个非 ephemeral exec 创建 thread `019f6985-7c75-7610-b31a-9749f4221892`，并产生相同 id 的 rollout JSONL。第二个进程执行 `exec resume <id>`，输出的 `thread.started` id 不变；fixture 日志显示 provider input 从 3 items 增到 5 items，新增首轮 assistant 与第二轮 user message。[X: `X-006`]

这证明了正常尾部写入后的 resume，不证明中间 JSONL 损坏、flush 半失败、schema 迁移或 workspace drift 的恢复策略。特别是 workspace 是共享外部状态，resume conversation 不等于文件系统 rollback。
