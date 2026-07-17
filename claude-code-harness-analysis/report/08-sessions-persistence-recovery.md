# Session、持久化与恢复

> **证据边界。** 本报告分析 source-only commit `16a676f`。其 1,884 个 TS/TSX 文件、关键 symbol 与 feature gates 和论文所述 Claude Code v2.1.88 corpus 强指纹一致，但缺少 package version、上游 tree hash、build manifest，不能视为已证明的 exact 官方 artifact。快照仍有 657 个无法解析的相对 import；除 SiFlow 协议探针外，主循环、安全、session 与 subagent 结论均为 static-only。官方材料只支持产品立场，五价值/十三原则是 analyst synthesis。[X: X-001–X-003] [D: D-001–D-008] [C: C-001, C-024–C-026]


![Claude Code persistence lifecycle](../diagrams/generated/assets/07-persistence-lifecycle.png)

*读者图问题：哪些状态 durable，resume/fork 实际恢复什么？ 这是 gpt-image-2 读者插图；当前实现边均为 static-only，结构化证据与排除项见 [图片元数据](../diagrams/generated/metadata.json)。*

## Live 与 durable state

| 状态 | 所有者 | 是否 durable | 恢复含义 |
|---|---|---|---|
| Live Session | 进程/AppState | 否 | 重启后重建 |
| Message chain | transcript JSONL | 是 | 通过 parentUuid 重建会话视图 |
| Child transcript | subagents/agent-*.jsonl | 是 | 用 agent metadata 选择/恢复 child |
| Compaction boundary | transcript entry | 是 | 指定被摘要/保留 segment 的新边界 |
| Team inbox | ~/.claude/teams | 是 | unread message 可跨进程被 attachment 消费 |
| Workspace files | 当前 cwd/git worktree | 外部持久状态 | 不随 session resume 自动回滚 |
| Worktree path metadata | session/agent metadata | 条件 durable | 路径仍存在时可恢复 cwd |

[sessionStorage](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/utils/sessionStorage.ts#L500) 使用项目路径派生目录和 sessionId JSONL，主消息与 sidechain 分开；parentUuid 形成逻辑链。写入有 queue/flush，compact/snip 后会重连 dangling parent 或重写可恢复 segment。[S: S-029]

## Resume 与 fork 的精确差别

- **Resume**：默认继续原 sessionId，加载 transcript/metadata，恢复 agent/mode、file history attribution、todo、worktree path 等可用信息。
- **Fork**：保留启动时的新 sessionId，同时复制可恢复 history 与部分 replacement metadata；它是会话身份分叉，不是 git branch 或文件快照。
- **Rewind files**：CLI 另有显式 file-history rewind，说明普通 resume/fork 本身不等于 filesystem rollback；它也不是任意 workspace/process 的通用 checkpoint。[S: S-030–S-031]
- **Permission freshness**：resume/fork 不从 transcript 反序列化旧 session 的临时 allow/deny/ask grants；新进程从当前 settings 与 CLI 参数重建 permission context。[S: S-044] [C: C-029]

所以 durable transcript 保存“发生过什么”，不自动保存“现在仍被授权做什么”。若恢复后再次请求同一 Bash action，正确的验证实验是观察是否重新 ask，而不是只检查 mode label。

## Compaction 与 persistence

Compact summary 不只是内存中替换 messages：boundary、preserved segment 和重注入 metadata 会影响之后 JSONL chain 如何加载。大文件读取还会做 byte-level prefilter、dead-branch pruning 和 parent chain reconstruction；这使恢复具有明确算法，而不是简单读取所有 JSON 行。[S: S-015, S-029]

## Crash/exit recovery

Graceful shutdown 把 cleanup/persistence 放在 SessionEnd hooks 和 analytics 之前，并用 2 秒 cleanup race、hook budget、analytics 500ms cap 与最终 failsafe 限制退出时间。[S: S-041]

静态代码尚不能回答 corrupted JSONL 是 fail closed、局部修复还是丢弃到什么粒度，也不能证明 abrupt SIGKILL 时最后一批 buffered writes 的边界。需要 resume/fork/corruption/signal 四组实验。[技术证据图](../diagrams/persistence-lifecycle.svg)
