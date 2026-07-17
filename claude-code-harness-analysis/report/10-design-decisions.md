# 设计决策与权衡

> **证据边界。** 本报告分析 source-only commit `16a676f`。其 1,884 个 TS/TSX 文件、关键 symbol 与 feature gates 和论文所述 Claude Code v2.1.88 corpus 强指纹一致，但缺少 package version、上游 tree hash、build manifest，不能视为已证明的 exact 官方 artifact。快照仍有 657 个无法解析的相对 import；除 SiFlow 协议探针外，主循环、安全、session 与 subagent 结论均为 static-only。官方材料只支持产品立场，五价值/十三原则是 analyst synthesis。[X: X-001–X-003] [D: D-001–D-008] [C: C-001, C-024–C-026]


这里严格使用 `D → design question → S → I`：官方材料只支持产品目标，源码说明 mechanism，收益/代价仍是 analyst inference。不能把“官方强调 safety”直接写成“作者因此选择了某个函数结构”。

| 决策 | First-party stance（D） | 当前机制（S） | Analyst tradeoff / 反例测试（I/X） | 证据 |
|---|---|---|---|---|
| 多 surface 共用 query() | 官方描述 iterative agentic loop 与 verifiable outcomes | REPL/QueryEngine 适配后进入同一 generator | 核心语义复用；需双入口 scripted diff 验证 UI/headless 差异 | D-002; C-003–C-004 |
| Context 按生命周期合流 | context 是有限资源，应 progressive disclosure/compact | prompt、CLAUDE.md、history、attachments；五阶段 shaper | provenance 强但有顺序/摘要漂移；逐项 ablation | D-005–D-006; C-006–C-007 |
| Registry 与 exposure 分离 | capability 应按任务逐步呈现 | pool/filter/schema/dispatch 四层 | 动态 MCP/deferred tools；同名/disabled matrix | D-005; C-010, C-028 |
| Permission 与 sandbox 分离 | human control + bounded autonomy | policy decision 后条件 sandbox wrapper | 两层可组合但易把 allow 误读为 isolated；side-effect matrix | D-001, D-003–D-004; C-012–C-014 |
| Child context 分离、workspace 默认共享 | subagent/team 使用 independent context | runAgent + optional worktree | 节省主 context；共享文件会冲突；并发 same-file experiment | D-005, D-007; C-017–C-020 |
| JSONL append + parent chain | memory 应可检查、可编辑、可延续 | session/sidechain JSONL，resume 不恢复 session grants | 易审计/分叉；corruption 与 trust freshness 需注入测试 | D-001, D-006; C-015–C-016, C-029 |
| 多层 telemetry | 没有足够 first-party 架构意图 | events、OTel、profiler、Perfetto | 粒度可选；correlation/privacy 配置复杂 | C-021 |
| Cleanup 优先的有界 shutdown | 没有足够 first-party 架构意图 | persistence → hooks → analytics → failsafe | 降低关键状态丢失；hung cleanup test | C-022 |

## 架构上最值得迁移的三点

第一，工具“存在、可见、被调用、被允许、被隔离、成功执行”应建模为六个状态，不应压成一个 capability edge。第二，subagent 隔离需要 context/process/workspace/policy/transcript/cancellation 六维矩阵。第三，resume 必须把 conversational state 与 external workspace state 分开描述。

## 不应迁移的假确定性

不能把 source-visible feature 当 production feature，不能把 analyst-normalized principle 冒充 Anthropic 官方 taxonomy，也不能把 provider probe 当 end-to-end harness validation。[C: C-023–C-027]
