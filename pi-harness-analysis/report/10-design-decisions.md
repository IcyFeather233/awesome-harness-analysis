# 10 设计决策与权衡

本节把“实现了什么”和“作者为什么这样做”分开。文档明确的产品立场使用 D evidence；源码可见机制使用 S evidence；右侧收益和代价是根据边界与实验形成的分析综合，不自动等价于作者动机。

![Pi design space](../diagrams/generated/pi-design-space.png)

> 图 8（gpt-image-2 读者插图）：四行分别从 documented stance 映射到 recovered mechanism，再以橙色点线连接 analyst-synthesized tradeoff；右列不表示作者声明。图像 provenance 与语义审查见[生成图 metadata](../diagrams/generated/metadata.json)；设计映射来自[story spec](../diagrams/story-specs.json)和下列 Evidence IDs。Evidence: D-001, D-002, D-003, D-004, D-007, D-008, S-001, S-003, S-007, S-008, S-011, S-017, R-004, X-002。

## 决策记录

| 决策 | 当前机制 | Documented intent | 收益 | 代价/风险 | Evidence |
|---|---|---|---|---|---|
| 薄 low-level loop | `runAgentLoop` + callbacks | agent-core 通用 runtime | 易嵌入、可用 faux provider 测试 | 产品编排落到上层，出现两代 orchestration | `S-001`, `D-003` |
| 工具默认并行 | batch 并发，sequential tool 可降级整批 | 文档/源码明确 | 降低多工具 latency | completion order 与 transcript order 不同，hooks 要理解双顺序 | `S-001`, `X-001` |
| 扩展优先而非内置工作流 | extensions/skills/packages | README 明确“aggressively extensible” | core 小、用户可定制 | 安全、subagent、MCP 行为不统一 | `D-004`, `S-003` |
| 无内置 sandbox/permission popup | 进程权限 + 外部隔离 | security 文档明确 intentional | 可直接使用本地 toolchain，不制造虚假边界 | unattended/untrusted 任务必须由部署层治理 | `D-002`, `D-007` |
| Project trust 只守启动资源 | path-based persisted decision | security 文档明确 | 防止 repo 静默注入 extension/settings | AGENTS/context prompt injection 仍存在，工具不受限 | `D-002`, `S-006` |
| Session 用 append-only tree | JSONL id/parentId/leaf | 源码与 session 文档 | branch/fork/compaction 可保留历史 | workspace 不随 branch 回滚；损坏恢复更复杂 | `S-008`, `R-004` |
| Compaction 是一等 entry | summary + first kept + token metadata | 实现明确；作者意图未单独说明 | 可重建 context、保留审计历史 | summary 有信息损失，需要额外模型调用 | `S-009`, `X-003` |
| 新 Harness 用 snapshot/save point | in-flight immutable, next safe point refresh | lifecycle 文档明确 | 配置热更新不污染当前 request，持久顺序确定 | phase/reentrancy/settled 仍在硬化 | `D-003`, `S-011`, `X-002` |
| Provider owns auth + stream | `Models` runtime collection | 源码 contract | 多 provider 与 custom endpoint 共用 loop | compatible server 的细节仍可能泄漏（如 thinking） | `S-012`, `R-005` |
| Event-first observability | structured lifecycle events | design notes 明确不绑定 vendor | JSON/RPC 易消费 | 缺 trace/span correlation 与默认 redaction/exporter | `D-005`, `D-009` |

## 跨决策张力

### 通用核心与产品一致性

薄 loop 让 agent-core 易嵌入，但 compaction、retry、session ordering 和 settled semantics 必须由上层拥有。新 AgentHarness 的出现说明可复用性问题已经从“能否调用 loop”转成“不同 orchestration 是否行为等价”。最有区分度的下一步不是更多单元测试，而是 AgentSession 与 AgentHarness 的 differential scenario suite。[C: C-010, C-016]

### 扩展自由与统一治理

registry/hooks 能把 subagent、MCP、permission UI 和自定义工具留给用户，但同样意味着不存在一个不可绕过的 application-level policy plane。若部署目标从本地交互式工具转向 unattended service，合理替代不是再加一个示例 hook，而是 whole-process isolation 或可证明覆盖所有 side-effect backend 的统一 capability boundary。[C: C-005, C-017]

### 可审计 session 与不可回滚 workspace

JSONL tree 完整保存 branch、compaction 和 resume 历史，却不为文件系统提供相同事务语义。用户可以回到旧 conversation leaf，但 workspace 仍是新状态。这不是 session bug，而是两个 durable subsystem 没有共同 checkpoint protocol 的结构性结果。[C: C-008, C-012]

没有文档化的作者动机不在表中伪装成事实。例如“为什么 JSONL 而非数据库”未找到直接说明，报告只陈述可观察 tradeoff。
