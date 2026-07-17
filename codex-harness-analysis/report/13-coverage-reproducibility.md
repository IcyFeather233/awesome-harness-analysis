# 覆盖率与复现

## 结构化产物

- [manifest.json](../manifest.json): commit、配置、隔离与 runtime
- [inventory.json](../inventory.json): 有界确定性仓库清点
- [hir.json](../hir.json): 29 nodes / 38 edges 的 harness IR
- [claims.jsonl](../evidence/claims.jsonl): 24 个可证伪 claims
- [observations.jsonl](../evidence/observations.jsonl): D/S/R/X/I 证据
- [coverage.json](../evidence/coverage.json): 14 模块局部覆盖与未知项
- [scenarios/catalog.json](../scenarios/catalog.json): 8 个真实/确定性场景
- [questions.json](../questions.json): 下一轮实验队列
- [generated metadata](../diagrams/generated/metadata.json): gpt-image-2 prompt/output hash 与语义审查

<!-- EXPLANATION:artifact-map -->
## 不同产物分别用来回答什么

- 想快速理解系统：从 [report/index.md](index.md) 和八张读者图开始。
- 想确认一句结论：在 [claims.jsonl](../evidence/claims.jsonl) 找 claim id，再跳到对应 D/S/R/X/I evidence。
- 想程序化比较另一个版本：使用 [hir.json](../hir.json) 的 typed nodes/edges 和 conditions。
- 想复现实验：使用 [scenario catalog](../scenarios/catalog.json)、`experiments/` 和 sanitized traces。
- 想判断“没有观察到”究竟意味着什么：查看 [coverage.json](../evidence/coverage.json) 的 configurations、excluded surfaces 和 unresolved。

当前 bundle 包含 29 个 HIR nodes、38 条 edges、24 个 claims 和 47 条 evidence records。图片不新增任何 claim；它们只是这些结构化事实的读者投影。

## 14 模块覆盖矩阵

`analyzed` 表示固定版本的主机制和关键分支已静态恢复；`partial` 表示仍缺少会改变结论边界的平台、feature 或故障路径动态覆盖。状态不是代码阅读比例。

| 模块 | 状态 | 已恢复机制 | 动态边界 | 未解决问题 |
|---|---|---|---|---|
| `interfaces` | analyzed | CLI/TUI/exec/app-server/MCP server 的入口分派与 thread API 收敛 | 运行了 exec JSON；TUI、app-server、MCP server 未端到端运行 | 无额外模块级未知项；仍受全局配置边界约束 |
| `core_loop` | analyzed | run_turn 的 prompt、stream、tool feedback、follow-up 与 stop 条件 | X-001/002/003/004 观察 stop、二次采样和可恢复 tool error | 无额外模块级未知项；仍受全局配置边界约束 |
| `context_assembly` | analyzed | ContextManager、StepContext、WorldState 与可见 tool specs | X-002 观察 tool output 进入下一请求；未做 WorldState 差分矩阵 | 无额外模块级未知项；仍受全局配置边界约束 |
| `compaction` | partial（关键平台、feature 或故障路径尚缺动态覆盖） | pre-turn/mid-turn selector、remote v2/v1 与 local replacement | 未触发超长上下文；结论限于固定源码路径 | 未用 oversized tool output 或 token fixture 动态触发 pre-turn/mid-turn/remote compaction。 |
| `model_abstraction` | partial（关键平台、feature 或故障路径尚缺动态覆盖） | ModelClientSession、provider dialect、transport fallback 与 retry | 真实 SiFlow 两种方言失败，确定性 Responses fixture 成功 | SiFlow 需要 role/namespace translation adapter 才能执行真实 agent turn；本报告没有修改 target code。 |
| `tools_extensions` | analyzed | ToolSpecPlan、registry/exposure、router、hooks、MCP/dynamic handlers | 覆盖 built-in exec、unknown tool 和 V1 namespace；MCP/dynamic 未运行 | 无额外模块级未知项；仍受全局配置边界约束 |
| `permissions_safety` | analyzed | ExecPolicy、approval cache，以及独立 apply_patch governance | X-004/007 验证 never 前置拒绝与无文件副作用；apply_patch 未动态对照 | 无额外模块级未知项；仍受全局配置边界约束 |
| `sandbox_execution` | partial（关键平台、feature 或故障路径尚缺动态覆盖） | permission profile 到 Linux/macOS/Windows sandbox executor 的变换 | 只观察 sandbox 之前的 policy deny；未实际比较三平台 backend | 宿主没有 Rust toolchain，且当前执行环境无法直接复现所有 platform sandbox backend。 |
| `workspace` | partial（关键平台、feature 或故障路径尚缺动态覆盖） | cwd、文件副作用、resume 后现实状态与多 agent 共享目录 | 验证 denied write 的目录/哈希不变；未做 resume drift 或 child 写冲突 | 未验证 worktree、remote environment 与并发 child 文件冲突。 |
| `sessions_persistence` | analyzed | ThreadStore、LiveThread、rollout append/flush/resume | X-006 验证正常 JSONL 尾部跨进程 resume；未注入 corruption | 无额外模块级未知项；仍受全局配置边界约束 |
| `subagents` | analyzed | AgentControl、CodexDelegate、V1/V2 gate、depth/limit/mailbox | 只运行 V1 root/child request 与 depth exposure；V2 未运行 | 无额外模块级未知项；仍受全局配置边界约束 |
| `orchestration` | analyzed | RegularTask、Task 生命周期、active turn 与 tool 并发锁 | X-001/002/003/004/005 覆盖正常、工具反馈、错误与 V1；未做 hang/cancel | 无额外模块级未知项；仍受全局配置边界约束 |
| `observability` | partial（关键平台、feature 或故障路径尚缺动态覆盖） | 产品 events、app-server notifications 与 OTel logs/traces/metrics | 观察 exec 产品 events 和 provider request log；OTel exporter 关闭 | OTel exporter 关闭，未检查 collector 端 span 拓扑。 |
| `recovery` | partial（关键平台、feature 或故障路径尚缺动态覆盖） | provider retry、cancellation、tool error、flush 与恢复边界 | 覆盖 unsupported tool、policy deny 和正常 resume；未做 crash/timeout/flush failure | 未注入 stream idle timeout、tool process crash、rollout corruption 与 SIGINT。 |

## 关键复现条件

```text
tag: rust-v0.144.5
commit: 87db9bc18ba5bc82c1cb4e4381b44f693ee35623
binary: codex-cli 0.144.5 (official x86_64-unknown-linux-musl release)
default test policy: approval=never, sandbox=read-only
deterministic provider: local Responses SSE fixture on 127.0.0.1
real provider: user-authorized SiFlow qwen3.6-35ba3b
```

动态场景的命令模板、配置约束与 trace 路径记录在 catalog；API key 不属于复现产物。

## 覆盖判断

14 个模块均完成源码调查；6 个模块标为 partial，原因是缺少跨平台、超长上下文、OTel、fault injection 或真实 provider 成功路径。没有把 “not observed” 写成 “absent”。目标 checkout 未修改。

## Claim index

`C-001`–`C-024` 的声明、evidence、coverage 与 falsification test 以 [claims.jsonl](../evidence/claims.jsonl) 为唯一索引；图只做语义投影，不新增事实。
