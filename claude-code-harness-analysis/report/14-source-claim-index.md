# 源码与 Claim 索引

> **证据边界。** 本报告分析 source-only commit `16a676f`。其 1,884 个 TS/TSX 文件、关键 symbol 与 feature gates 和论文所述 Claude Code v2.1.88 corpus 强指纹一致，但缺少 package version、上游 tree hash、build manifest，不能视为已证明的 exact 官方 artifact。快照仍有 657 个无法解析的相对 import；除 SiFlow 协议探针外，主循环、安全、session 与 subagent 结论均为 static-only。官方材料只支持产品立场，五价值/十三原则是 analyst synthesis。[X: X-001–X-003] [D: D-001–D-008] [C: C-001, C-024–C-026]


## 关键源码

| Evidence | 源码 | 主题 |
|---|---|---|
| S-002/S-003 | [cli.tsx](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/entrypoints/cli.tsx#L33) / [main.tsx](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/main.tsx#L585) | 产品入口、feature path |
| S-004/S-005 | [REPL](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/screens/REPL.tsx#L2661) / [QueryEngine](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/QueryEngine.ts#L260) | surface adapters |
| S-006–S-008 | [query.ts](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/query.ts#L219) | loop、recovery、stop |
| S-010–S-013 | [context](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/context.ts#L1) / [attachments](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/utils/attachments.ts#L1) | context |
| S-014/S-015 | [compact](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/services/compact/compact.ts#L330) | compaction |
| S-016–S-018 | [client](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/services/api/client.ts#L88) / [withRetry](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/services/api/withRetry.ts#L170) | provider/retry |
| S-019–S-022 | [tools](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/tools.ts#L100) / [toolExecution](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/services/tools/toolExecution.ts#L880) | capability |
| S-023–S-027 | [permissions](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/utils/permissions/permissions.ts#L560) / [sandbox](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/utils/sandbox/sandbox-adapter.ts#L1) | governance |
| S-029–S-031 | [storage](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/utils/sessionStorage.ts#L500) / [restore](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/utils/sessionRestore.ts#L1) | persistence |
| S-032–S-037 | [AgentTool](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/tools/AgentTool/AgentTool.tsx#L323) / [mailbox](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/utils/teammateMailbox.ts#L1) | child/team |
| S-038–S-041 | [tracing](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/utils/telemetry/sessionTracing.ts#L176) / [shutdown](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/utils/gracefulShutdown.ts#L391) | observability/recovery |
| S-043 | [HOOK_EVENTS](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/entrypoints/sdk/coreTypes.ts#L25) | 27 个 hook lifecycle events |
| S-044/S-045 | [permission initialization](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/main.tsx#L1035) / [child permission derivation](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/tools/AgentTool/runAgent.ts#L415) | resume 与 child permission |
| S-046 | [PluginManifestSchema](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/utils/plugins/schemas.ts#L884) | plugin packaging surfaces |
| D-001–D-008 | [Anthropic first-party sources](../evidence/observations.jsonl) | 产品立场，不直接证明源码控制流 |
| X-003 | [论文对照](15-paper-benchmark.md) | v2.1.88 corpus 强指纹 |

## Claim index

| Claims | 结论族 | 章节 |
|---|---|---|
| C-001, C-023–C-026 | snapshot、feature、intent、runtime 与论文 corpus 边界 | 01, 11–15 |
| C-002–C-003 | surfaces 与共享 core | 02 |
| C-004–C-005 | loop 与 tool result 回填 | 03 |
| C-006–C-007 | context 与 compaction | 04 |
| C-008–C-011 | provider、SiFlow、capability/dispatch | 05 |
| C-012–C-014 | permission、sandbox、process audit | 06, 12 |
| C-015–C-016 | JSONL、resume/fork、workspace | 08 |
| C-017–C-020 | Agent child、worktree、teammate/mailbox | 07 |
| C-021–C-022 | telemetry 与 shutdown | 09 |
| C-027 | 跨 subsystem 的架构承诺与五价值/十三原则 | 00-values, 10 |
| C-028 | MCP/Plugin/Skill/Hook 的差异化注入 | 05 |
| C-029 | resume/fork 不恢复 session-scoped permission grants | 06, 08 |

正文 PNG 是 gpt-image-2 根据 evidence-grounded prompt 生成并经人工语义审查的读者图；它们帮助解释，但不是结构化真值。可审计的 node/edge、claim 与 evidence 映射保留在 [story-specs.json](../diagrams/story-specs.json) 和各节链接的技术 SVG 中。最重要的开放 claim 是 C-014：canonical gate 之外的副作用表面是否有等价治理；它会保持 open，直到 runtime reachability 与 OS side-effect matrix 完成。
