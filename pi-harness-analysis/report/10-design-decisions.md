# 10 设计决策与权衡

本节把“实现了什么”和“作者为什么这样做”分开。文档明确的产品立场使用 D evidence；源码可见机制使用 S evidence；右侧收益和代价是根据边界与实验形成的分析综合，不自动等价于作者动机。

![Pi design space](../diagrams/generated/pi-design-space.png)

> 图 8（gpt-image-2 读者插图）：四行分别从 documented stance 映射到 recovered mechanism，再以橙色点线连接 analyst-synthesized tradeoff；右列不表示作者声明。图像 provenance 与语义审查见[生成图 metadata](../diagrams/generated/metadata.json)；设计映射来自[story spec](../diagrams/story-specs.json)和下列 Evidence IDs。Evidence: D-001, D-002, D-003, D-004, D-007, D-008, S-001, S-003, S-007, S-008, S-011, S-017, R-004, X-002。

## 决策记录

| 决策 | 当前机制 | 适用条件 | Documented intent | 收益 | 代价/风险 | Evidence / 置信度 | 最小反证 |
|---|---|---|---|---|---|---|---|
| 薄 low-level loop | `runAgentLoop` + callbacks | 所有使用 agent-core contract 的 host | agent-core 通用 runtime | 易嵌入、可用 faux provider 精确测试 | 产品 retry/session/settled 落到上层，形成两代 orchestration | `S-001`, `D-003`；高 | 找到产品主路径绕过它的独立 model/tool loop |
| 工具默认并行 | batch 并发；任一 sequential tool 使整批串行 | 同一 assistant message 的 toolUse batch | 文档/源码明确 | 降低互不依赖工具的 latency | completion event 与 transcript 顺序不同，错误分类会改变整批吞吐 | `S-001`, `X-001`；高 | 并发测试中 toolResults 按完成顺序而非原 call 顺序进入 context |
| 扩展优先而非内置工作流 | extensions/skills/packages + hooks | Coding Agent resource loader 启用相应资源时 | README 明确 aggressively extensible | core 小、用户可定制 MCP/subagent/policy | 行为和治理不统一；extension 与 host 同权限 | `D-004`, `S-003`；高 | 默认 registry 强制提供统一 MCP/subagent/policy contract |
| 无内置 sandbox/permission popup | 进程权限 + 外部隔离 | 默认 built-ins 与 extension runtime | security 文档明确 intentional | 直接使用本地 toolchain，不制造虚假边界 | unattended/untrusted 任务必须由部署层治理 | `D-002`, `D-007`；高 | 默认配置存在覆盖所有副作用 backend 的不可绕过 gate |
| Project trust 只守启动资源 | path-based persisted decision | project-local settings/extensions/skills/SYSTEM | security 文档明确 | 防止 repo 静默加载可执行扩展/配置 | AGENTS context 仍可注入 prompt；运行期 tools 不受限 | `D-002`, `S-006`；高 | 未信任项目时 read/bash 被 runtime policy 自动阻止 |
| Session 用 append-only tree | JSONL `id/parentId/leaf` | persistent session，非 `--no-session` | session 文档和实现 | branch/fork/compaction 保留历史 | workspace 不随 branch 回滚；中段损坏可造成错误 branch | `S-008`, `R-004`；高 | resume 不依赖 tree/leaf，或 fork 自动恢复旧文件状态 |
| Compaction 是一等 entry | summary + first kept + token metadata | Coding Agent overflow/threshold path | 机制明确；作者选择理由未单独记录 | 可重建 active context并保留压缩事件 | summary 有信息损失，增加模型调用和失败面 | `S-009`, `X-003`；高 | compact 后没有 durable entry 或 context 不经 summary 重建 |
| 新 Harness 用 snapshot/save point | in-flight immutable；next safe point refresh | 迁移中的 generic `AgentHarness`，非当前 Coding Agent 默认 | lifecycle 文档明确 | 热更新不污染当前 request，持久顺序明确 | phase/reentrancy/settled/auto recovery 仍在硬化 | `D-003`, `S-011`, `X-002`；中 | 当前 request 中途读到 next-state 配置，或 pending write 越过 save point |
| Provider owns auth + stream | `Models` runtime collection | 注册 provider/model 与 custom endpoint | 源码 contract | 多 provider 共用 loop | “compatible” endpoint 的 body/stream 方言仍泄漏，如 thinking flag | `S-012`, `R-005`；高 | provider 选择/auth 在 loop 内按 provider id 硬编码 |
| Event-first observability | structured lifecycle events | JSON/RPC/in-process consumers | design notes 明确不绑定 vendor | UI/host 易消费，可由 adapter 映射 | 缺默认 trace/span correlation、redaction 和 exporter | `D-005`, `D-009`；中 | 本版本默认发出完整 OTel spans 并传播 parent context |

## 跨决策张力

### 通用核心与产品一致性

薄 loop 让 agent-core 易嵌入，但 compaction、retry、session ordering 和 settled semantics 必须由上层拥有。新 AgentHarness 的出现说明可复用性问题已经从“能否调用 loop”转成“不同 orchestration 是否行为等价”。最有区分度的下一步不是更多单元测试，而是 AgentSession 与 AgentHarness 的 differential scenario suite。[C: C-010, C-016]

### 扩展自由与统一治理

registry/hooks 能把 subagent、MCP、permission UI 和自定义工具留给用户，但同样意味着不存在一个不可绕过的 application-level policy plane。若部署目标从本地交互式工具转向 unattended service，合理替代不是再加一个示例 hook，而是 whole-process isolation 或可证明覆盖所有 side-effect backend 的统一 capability boundary。[C: C-005, C-017]

### 可审计 session 与不可回滚 workspace

JSONL tree 完整保存 branch、compaction 和 resume 历史，却不为文件系统提供相同事务语义。用户可以回到旧 conversation leaf，但 workspace 仍是新状态。这不是 session bug，而是两个 durable subsystem 没有共同 checkpoint protocol 的结构性结果。[C: C-008, C-012]

没有文档化的作者动机不在表中伪装成事实。例如“为什么 JSONL 而非数据库”未找到直接说明，报告只陈述可观察 tradeoff。
