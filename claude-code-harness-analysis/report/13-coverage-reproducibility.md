# 覆盖率与复现

> **证据边界。** 本报告分析 source-only commit `16a676f`。其 1,884 个 TS/TSX 文件、关键 symbol 与 feature gates 和论文所述 Claude Code v2.1.88 corpus 强指纹一致，但缺少 package version、上游 tree hash、build manifest，不能视为已证明的 exact 官方 artifact。快照仍有 657 个无法解析的相对 import；除 SiFlow 协议探针外，主循环、安全、session 与 subagent 结论均为 static-only。官方材料只支持产品立场，五价值/十三原则是 analyst synthesis。[X: X-001–X-003] [D: D-001–D-008] [C: C-001, C-024–C-026]


## 14 模块覆盖

| Module | 状态 | 重点文件 | Runtime |
|---|---|---|---|
| interfaces | partial | cli.tsx、main.tsx、REPL、QueryEngine | 无 |
| core_loop | partial | query.ts、query/config、query/deps | 无 |
| context_assembly | partial | context、prompts、claudemd、attachments | 无 |
| compaction | partial | autoCompact、compact、microCompact | 无 |
| model_abstraction | partial | client、claude、withRetry、providers | 仅 provider probe |
| tools_extensions | partial | Tool、tools、toolExecution、orchestration | 无 |
| permissions_safety | partial | permissions types/engine、useCanUseTool | 无 |
| sandbox_execution | partial | BashTool、shouldUseSandbox、sandbox-adapter、Shell | 无 |
| workspace | partial | cwd、worktree、AgentTool | 无 |
| sessions_persistence | partial | sessionStorage、sessionRestore | 无 |
| subagents | partial | AgentTool、runAgent、spawnInProcess | 无 |
| orchestration | partial | query、toolOrchestration、coordinatorMode | 无 |
| observability | partial | analytics、sessionTracing、Perfetto | 无 |
| recovery | partial | withRetry、gracefulShutdown、compact | 无 |

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
