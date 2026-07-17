# 04 上下文、记忆与压缩

![Context lifecycle](../diagrams/generated/pi-context-lifecycle-v2.png)

> 图 3（gpt-image-2 读者插图）：startup/lazy、carry-forward 和 runtime 三类来源先汇入同一入口，再依次经过 `transformContext -> convertToLlm -> Per-request context -> Model request`；compaction 是虚线条件回路。第一版因错误画出 tool result 直达 model 而被拒绝，本图为修正并复审后的 v2。图像的 prompt、output hash 与语义审查见[生成图 metadata](../diagrams/generated/metadata.json)；context 数据流来自[Harness IR](../hir.json)和下列 Evidence IDs。Evidence: `S-001`, `S-002`, `S-004`, `S-005`, `S-008`, `S-009`, `R-001`, `R-002`, `R-004`, `X-003`。

## Context 来源

| 来源 | 首次装载/刷新时机 | 信任与持久性 | 进入模型的精确方式 | 本轮动态覆盖 |
|---|---|---|---|---|
| 默认/自定义 system prompt | startup；model/resource refresh 后重建 | 配置/CLI 来源；不作为 session message entry | `buildSystemPrompt()` 形成每次 request 的 system instructions | 最小 system prompt 路径运行；未做 source diff |
| AGENTS.md / CLAUDE.md | startup/reload，可用 flag 禁用 | context file；**不受 project trust gate** | 包装为 `<project_instructions>` 并入 system prompt | 真实场景显式 `--no-context-files`，仅静态确认 |
| `.pi/SYSTEM.md` / append prompt | trusted project resources 加载或 reload | 未信任项目时不加载 | resource loader 合并到 system prompt | 真实场景禁用，未动态加载 |
| Skills metadata | resource load/reload | global/project skill；project 部分受 trust | 有 read tool 时在 system prompt 列出可用 skill | 真实场景禁用 |
| `/skill:name` full body | 用户显式调用时 lazy expansion | body 在调用 turn 进入 transcript | 展开成 user-side invocation text | 未运行 skill invocation |
| Active session branch | open/resume/branch/fork 后重建 | JSONL v3 durable parent chain | `buildSessionContext()` 选择 active path/messages/summary | R-003/004 验证跨进程恢复 |
| ToolResult | 每个 tool batch 完成后 | 作为 message entry 可被 session 保存 | 先追加 transcript，再经 transform/convert 进入下一 request | R-002 直接观察 `314159` 回填 |
| Extension message/system override | 每个 prompt 开始 | extension 与 host 同权限；是否 durable 取决于 message API | `before_agent_start` 可加 custom message 或替换本轮 system prompt | X-001 hooks；真实 extensions 禁用 |
| Context hook transform | **每次 provider request** | transient，默认不回写原 session tree | `transformContext` 后再 `convertToLlm` | X-001 覆盖 hook contract；未做真实 payload diff |

[C: C-003] 的置信度为 medium，因为本轮没有部署 request proxy 做全部 source 的差分；真实场景只验证了最小路径和 toolResult 回填。

## Durable memory

Pi 没有独立向量 memory 层。核心 durable memory 是 session tree：message、model/thinking change、custom entry、compaction、branch summary 等都在 JSONL 中；active branch 通过 parent chain 与 leaf 计算。workspace 文件是另一条独立持久层，不会自动与 session rollback 保持一致。[S: S-008]

## Compaction

Coding Agent 分两类：

- **Overflow**：错误或 usage 超过当前 model window；删除 live context 中的 error，生成 summary，最多 compact-and-retry 一次。
- **Threshold**：接近窗口时压缩，但不自动重新回答已完成的 assistant turn。

Compaction entry 保存 summary、`firstKeptEntryId`、`tokensBefore` 和 details；随后重建 active context。[S: S-009] [X: X-003]

新 `AgentHarness.compact()` 已有手动结构操作和 compaction helpers，但 auto-compaction decision 尚未实现。[D: D-008]

| 路径 | 触发条件 | 操作顺序 | 是否自动重答 | Durable 结果 | 未验证边界 |
|---|---|---|---|---|---|
| Overflow compaction | provider 报 context overflow，或 usage 超出当前 model window | 从 live context 移除 error -> 生成 summary -> 追加 compaction entry -> 重建 active context -> 最多 retry 一次 | 是，最多一次 compact-and-retry | error 仍可留在 session；summary/firstKept/tokens 写入 JSONL | 真实超长 SiFlow request 未运行 |
| Threshold compaction | token usage 接近阈值，但当前 assistant turn 已正常完成 | 计算 summary -> 追加 compaction entry -> 重建后续 context | 否，不重新回答已完成 turn | compaction 成为 active branch 的一等 entry | summary 信息损失未做质量评估 |
| Manual `AgentHarness.compact()` | host 显式调用 helper | 在 phase/save-point 约束下准备并提交结构变更 | 由 host 决定后续 prompt | helper/session tests 验证 ordering | auto decision、产品迁移和半持久恢复尚未实现 |
