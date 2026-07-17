# 覆盖率与复现

> **证据边界。** 本报告分析 source-only commit `16a676f`。其 1,884 个 TS/TSX 文件、关键 symbol 与 feature gates 和论文所述 Claude Code v2.1.88 corpus 强指纹一致，但缺少 package version、上游 tree hash、build manifest，不能视为已证明的 exact 官方 artifact。快照仍有 657 个无法解析的相对 import；除 SiFlow 协议探针外，主循环、安全、session 与 subagent 结论均为 static-only。官方材料只支持产品立场，五价值/十三原则是 analyst synthesis。[X: X-001–X-003] [D: D-001–D-008] [C: C-001, C-024–C-026] 首次遇到缩写或内部名词时，可查 [全局术语表](16-glossary.md)。


## Coverage 在这里表示什么

- **Source coverage**：哪些目录、入口和关键 symbol 被实际阅读；它不是“扫描到关键词”的文件数。
- **Runtime coverage**：哪些路径在指定配置下真的执行并产生 trace/side effect evidence。
- **Configuration coverage**：测试过哪些 mode、feature、provider、platform 和 permission policy。同一代码路径在不同配置下可能有不同语义。
- **Partial**：已覆盖该模块的主要 source path，但缺少完整 build graph、次要入口或 runtime scenario；它不是“精确完成了 50%”。
- **Excluded surface**：明确不在本轮结论范围内的模式。排除项不是不存在，而是读者不能用本报告替它作保证。

## 14 模块覆盖

| Module | 状态 | 已覆盖的 source 面 | Runtime / 未覆盖边界 |
|---|---|---|---|
| interfaces | partial source coverage | `cli.tsx`、`main.tsx`、REPL、QueryEngine，覆盖 bootstrap、interactive/headless 入口和部分子命令分发。 | 无 target run；server/bridge/MCP 子命令的实际 reachability 未验证。 |
| core_loop | partial source coverage | `query.ts`、query config/deps，覆盖 loop state、model request、tool follow-up、transition 和 recovery counters。 | 无 scripted/real query trace；不能证明事件顺序在 runtime 中完整出现。 |
| context_assembly | partial source coverage | context、prompts、CLAUDE.md、attachments，覆盖 provenance、startup/lazy/per-turn/carry-forward 来源。 | 无真实 request envelope；无法量化每类 context 的 token cost。 |
| compaction | partial source coverage | autoCompact、compact、microCompact、query shaper order，覆盖 source-verified stage order。 | 无 overflow/fault injection；summary loss、threshold 和 survivor 质量未测。 |
| model_abstraction | static + protocol probe | client、claude request builder、withRetry、providers，并执行 SiFlow protocol probe。 | Probe 绕过 Claude Code；完整 headers、thinking/cache、retry/fallback 未端到端验证。 |
| tools_extensions | partial source coverage | Tool types、registry、toolExecution、hooks、MCP、plugin schema、orchestration。 | 无 fixture 安装/调用；同名 tool、disabled tool、hook side effects 未实测。 |
| permissions_safety | partial source coverage | permission types/engine、mode schema、useCanUseTool、child derivation、resume freshness。 | 无 permission deny side-effect matrix；canonical path 外副作用仍为 open claim。 |
| sandbox_execution | partial source coverage | BashTool、shouldUseSandbox、sandbox adapter、Shell wrapper。 | 无实际 spawn、filesystem/network trace；sandbox availability 和 policy interaction 未跑。 |
| workspace | partial source coverage | cwd handling、worktree creation/cleanup、AgentTool workspace choices。 | 无并发 same-file 或 worktree retention experiment。 |
| sessions_persistence | partial source coverage | sessionStorage、sessionRestore、JSONL、parentUuid、fork/resume metadata。 | 无 corruption、SIGKILL、flush-boundary 实验。 |
| subagents | partial source coverage | AgentTool、runAgent、spawnInProcess、async task、worktree、teammate/mailbox。 | 无 child runtime matrix；pid/cwd/tool/mode/abort/result channel 未观测。 |
| orchestration | partial source coverage | query orchestration、tool scheduling、coordinatorMode 与 worker delegation。 | 无 branch-forcing scripted model；concurrent tool ordering 未实测。 |
| observability | partial source coverage | analytics、sessionTracing、OTel gates、Query Profiler、Perfetto。 | 无 target spans；不能报告 latency、cost、frequency 或 correlation accuracy。 |
| recovery | partial source coverage | withRetry、gracefulShutdown、compaction recovery、abort/interruption result。 | 无 induced provider failure、hung hook、slow flush 或 signal experiment。 |

partial 表示已做重点 source coverage，但缺少 build configuration 与 runtime scenario，不表示“只读了一半文件”。机器可读范围见 [coverage.json](../evidence/coverage.json)。

## 复现顺序

1. python3 experiments/scan_snapshot.py
2. python3 experiments/compile_analysis.py
3. python3 experiments/compile_story_specs.py
4. python3 experiments/write_reports.py
5. 运行 skill 的 render_diagrams.py 与 render_story_diagrams.py
6. 运行 validate_analysis.py . --strict
7. 运行 audit_outputs.py . --strict

## Artifact map

- [manifest.json](../manifest.json)：冻结对象、执行边界
- [inventory.json](../inventory.json)：启发式导航
- [hir.json](../hir.json)：34 nodes / 54 edges
- [claims.jsonl](../evidence/claims.jsonl)：29 claims
- [observations.jsonl](../evidence/observations.jsonl)：62 条 D/S/X/I evidence
- [conflicts.jsonl](../evidence/conflicts.jsonl)：快照与 runtime 冲突
- [scenarios](../scenarios/catalog.json)：3 executed（含 paper fingerprint）、5 blocked
- [story specs](../diagrams/story-specs.json)：十一张读者图规格，含 question/exact-text/glossary/exclusions contract
- [image prompts](../diagrams/generated/prompts/prompts.jsonl)：首批 gpt-image-2 正文图提示词；论文对照新增图见 [paper-gap prompts](../diagrams/generated/prompts/09-11-paper-gap-prompts.jsonl)
- [generated assets](../diagrams/generated/assets/)：当前八张 gpt-image-2 PNG 正文图；另三张已有 story spec/prompt，因本轮自定义 API 凭据发送审批未通过而待生成
- [image metadata](../diagrams/generated/metadata.json)：模型、端点类别、哈希与人工语义审查

该仓库无法单独重建官方 bundle、确定 feature set 或运行 Claude Code。它能强指纹映射到论文 v2.1.88 corpus，但关闭 exact identity 与 runtime 缺口仍需要同快照 package/build metadata、tree hash 或编译 artifact。
