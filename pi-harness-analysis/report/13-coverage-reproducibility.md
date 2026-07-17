# 13 覆盖与复现

## 产物

- 固定配置：[manifest.json](../manifest.json)
- 仓库 inventory：[inventory.json](../inventory.json)
- HIR：[hir.json](../hir.json)
- Claims：[claims.jsonl](../evidence/claims.jsonl)
- Evidence：[observations.jsonl](../evidence/observations.jsonl)
- Coverage：[coverage.json](../evidence/coverage.json)
- Scenarios：[catalog.json](../scenarios/catalog.json)
- Raw traces：`traces/raw/`
- Redacted normalized traces：`traces/normalized/`
- Diagram source models/metadata：`diagrams/`
- Narrative story spec：[story-specs.json](../diagrams/story-specs.json)
- Reader PNG/prompt/review metadata：`diagrams/generated/`

## 结构化规模

当前 bundle 包含 **29 个 HIR nodes、35 条 typed edges、20 个 supported claims 和 35 条 D/S/R/X evidence records**。这些计数描述可审计产物规模，不代表源码覆盖百分比或生产路径频率。

## 14 模块覆盖矩阵

`analyzed` 表示固定版本主机制和关键条件已静态恢复；`partial` 表示仍缺少会改变结论边界的平台、feature、真实 side effect 或故障注入。状态不是“读了多少行代码”。

| 模块 | 状态 | 已恢复机制 | 动态边界 | 未解决问题 |
|---|---|---|---|---|
| `compaction` | analyzed | overflow、threshold 与 AgentHarness manual compaction helper | 31 Coding Agent tests + AgentHarness helper tests；无真实长上下文 | 未用真实模型触发 262K 上下文 overflow。 |
| `context_assembly` | partial（关键运行或故障路径尚缺动态覆盖） | system/resources/session/toolResult/extensions/hooks 到 per-request context | 动态验证最小 prompt、toolResult、resume；资源/trust/hook payload 差分未跑 | 未代理捕获完整 provider request；未动态差分 skills/context files/extensions。 |
| `core_loop` | analyzed | runAgentLoop 的 provider/tool/steering/follow-up/stop 双层循环 | R-001/002 + 39 tests 覆盖 stop、tool feedback、queue、双顺序 | 无额外模块级未知项；仍受全局运行配置限制 |
| `interfaces` | analyzed | CLI interactive/print/JSON/RPC 收敛到 cwd-bound AgentSession runtime | 真实运行 JSON mode；TUI/RPC 仅静态检查 | 无额外模块级未知项；仍受全局运行配置限制 |
| `model_abstraction` | analyzed | pi-ai provider/model/auth/base URL/stream runtime contract | SiFlow model discovery/text/read 成功；未比较其他 provider | SiFlow 服务端默认 thinking 与 Pi reasoning=false 存在兼容差异。 |
| `observability` | partial（关键运行或故障路径尚缺动态覆盖） | agent events、JSON/RPC stream、session JSONL 与 adapter design notes | R-001/002 JSON events 可重建；无默认 OTel exporter | 默认没有 trace/span correlation IDs；OTel adapter 设计未实现。 |
| `orchestration` | analyzed | 当前 AgentSession 产品编排与迁移中 AgentHarness snapshot/save point | 当前 AgentSession 真实运行；AgentHarness 61 tests，未做差分迁移 | Coding Agent 迁移到新 AgentHarness 尚未完成。 |
| `permissions_safety` | analyzed | project trust、可选 tool gate、protected paths 与默认进程权限 | 只验证 trust/resource source；未运行 deny 或副作用工具 | 未执行破坏性 allow/deny side-effect 场景；结论主要来自明确文档与源码。 |
| `recovery` | analyzed | retry、overflow、truncated call、abort、hook/orchestrator failures | 定向 tests 覆盖逻辑分支；无 SIGINT、timeout、crash、半持久 turn | 未执行真实 SIGINT、tool timeout、进程 crash 或半持久 turn recovery。 |
| `sandbox_execution` | partial（关键运行或故障路径尚缺动态覆盖） | Gondolin selective routing 与 whole-process Docker/OpenShell/VM 边界 | Gondolin/Docker/OpenShell/VM 均未动态执行 | Gondolin 要求 Node >=23.6 与 QEMU，本轮 Node 22.19 环境未运行；Docker/OpenShell 未运行。 |
| `sessions_persistence` | analyzed | JSONL v3 parent tree、leaf、branch/fork/resume/migration | R-003/004 验证正常跨进程恢复；无 corruption/fork 动态矩阵 | 未做 corrupted JSONL 注入与跨版本 migration 动态测试。 |
| `subagents` | partial（关键运行或故障路径尚缺动态覆盖） | 默认无 subagent、示例 extension 子进程、experimental orchestrator | 示例和 orchestrator 仅源码；未创建 child | 核心无内置 subagent；可选 extension 与 experimental orchestrator 均未动态运行。 |
| `tools_extensions` | analyzed | built-in/custom/extension registry 与 input/context/tool/provider/session hooks | hooks/registry 有定向 tests；真实 runs 禁用 extensions | 未动态运行自定义 extension tool。 |
| `workspace` | analyzed | cwd、host filesystem、session branch 与共享 subagent workspace | 合成 read workspace 与 session resume；未测写入、branch drift、冲突 | 只验证只读 workspace；写/edit/bash 未动态执行。 |

## 关键复现命令

```bash
# 归一化 synthetic traces
python3 reproduce/normalize_pi_trace.py   traces/raw/R-002-read-tool.jsonl   traces/normalized/R-002-read-tool.normalized.jsonl   --scenario-id R-SCENARIO-002

# 重建 structured evidence/HIR
python3 reproduce/compile_analysis.py

# 严格校验
python3 ../../harness-analysis-skill/scripts/validate_analysis.py . --strict

# gpt-image-2 prompts 和发布图位于 diagrams/generated/；metadata 固定 prompt/output hash

# 重写报告
python3 reproduce/compile_report.py

# 检查 Markdown links、8 张正文 PNG、hash 与 semantic review metadata
python3 ../../harness-analysis-skill/scripts/audit_outputs.py . --strict
```

## 验证结果

- Analysis validator：`0 errors, 0 warnings`
- PNG decode/hash：8/8 reader figures valid
- Output audit：Markdown links、8 张 report-facing PNG、prompt/output hash 与 semantic review metadata 通过 strict
- Diagram density：overview 16 nodes；turn 11；context 9；permission 11；subagent 10；persistence 7
- Narrative density：system 12 nodes；observed turn 12；context 8；extension 11；design space 12
- Tests：39 + 61 + 31 = 131 passed
- Target `git status --short`：clean（依赖目录被 gitignore，不改变固定源码）

## Coverage statement

源码 inventory 共 1021 files，未达到 file/size scan limit。14 模块均有记录；partial 模块与 unresolved 条目不会被“未发现”等价成“不存在”。Runtime coverage 只代表 Linux/Node/JSON-mode/SiFlow 与命名 faux-provider tests。
