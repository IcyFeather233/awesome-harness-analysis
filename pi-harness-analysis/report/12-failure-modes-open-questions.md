# 12 失败模式与开放问题

## 已验证或源码明确的 failure path

| 失败/触发 | 当前行为 | 状态影响范围 | 可恢复条件 | 尚未验证的边界 | Evidence |
|---|---|---|---|---|---|
| Provider retryable error | 指数退避，`maxRetries` 有界；live context 移除 error，session 保留 entry | 当前 provider request/产品 prompt | 后续 retry 成功或用户再次 prompt | 真实断网、rate-limit header、进程重启时 budget 是否保留 | `S-010`, `X-003` |
| Context overflow | 生成 compaction；错误型 overflow 最多自动 retry 一次 | active context 与当前 prompt | summary 成功且 compact 后 request 可接受 | 真实长上下文、summary provider 失败、连续 model window 变化 | `S-009`, `X-003` |
| Length-truncated tool call | 全部拒绝执行，为每个 call 生成 error result | 当前 tool batch | 模型下一 turn 重发完整参数 | 部分工具已先产生 delta 时是否有额外 side effect surface | `S-001`, `X-001` |
| Tool exception | 转为 `isError` toolResult 并进入模型 context | 单个 call；batch 继续按 contract 汇总 | 模型可根据 error 自我修复 | extension 在抛错前已产生的主机副作用不能自动回滚 | `S-001`, `X-001` |
| Bash timeout/abort | kill detached process group/tree；保留输出和状态 | shell process tree | handler 返回后 session 可继续 | orphan/grandchild、不可中断 I/O、Windows 行为 | `S-007` |
| Session file 非空但无合法 header | 拒绝打开 | 整个 session file | 需人工修复/恢复合法 header | 中段 malformed line 被跳过后 branch 是否静默错误 | `S-008` |
| New AgentHarness hook failure | 归一化 `AgentHarnessError`；部分 post-commit failure 不回滚 | 当前 phase/save point | host 根据错误和 committed state 决定继续 | reentrancy、settled 与半持久 turn 仍 provisional | `D-003`, `S-011` |
| Orchestrator child exit | instance 标 error、reject pending、清理 resources | 单个 RPC Pi instance | supervisor 可新建/重启实例 | in-flight task、session 与外部副作用不能恢复 | `S-016` |

## 产品风险，不是分析器缺陷

- 默认无 permission/sandbox，对 untrusted/unattended workload 风险高。
- AGENTS/CLAUDE context 不受 project trust gate，prompt injection 是明确接受的本地 agent 风险。
- optional tool-routing sandbox 不自动覆盖 arbitrary extension tools。
- session branch 与 workspace filesystem 没有事务性一致性。
- subagent child 默认共享 cwd 与环境，context 隔离不等于 capability 隔离。

## 分析限制

- 未运行 write/edit/bash、Gondolin、Docker、OpenShell、subagent extension、orchestrator。
- 未做 corrupted session、SIGINT、tool timeout、child crash、long-context real model。
- 未获得 production feature flags、使用频率或 maintainer 访谈。
- 新 AgentHarness lifecycle 文档自己标记 phase/settled/reentrancy 仍 provisional。

## 优先实验

| 优先级 | 实验 | 要区分的假设 | 通过标准 | 仍不能推出 |
|---|---|---|---|---|
| P0 | `AgentSession` vs `AgentHarness` differential suite | 共享 low-level loop 是否足以保证产品行为等价 | 相同 scripted turns 对齐 messages、events、retry、compaction、writes 与 settled；差异有明确 contract | 单元场景一致不代表迁移已完成 |
| P0 | Container/VM permission bypass matrix | 可选 gate/路由是否覆盖所有副作用 backend | built-in、`!`、custom tool、extension direct process、subagent 分别记录 host/guest 文件、进程、网络副作用 | 单一 container 配置不代表所有 bind mount/credential 策略 |
| P1 | JSONL corruption matrix | parser 宽容跳行是否可能形成静默错误 branch | header/middle/tail/parent/compaction/leaf 注入后明确分类拒绝、修复或降级 | conversation 恢复不证明 workspace 一致 |
| P1 | Provider proxy context differential | 九类 context source 的装载和 request 时机是否符合静态结论 | 每次 request 保存 redacted type/hash diff，并对 trust/reload/hook 条件逐项开关 | 一个 provider 方言不覆盖其他 adapter |
| P2 | Orchestrator restart/crash | supervisor cleanup 与 durable session 能否恢复 in-flight child | crash 前后 instance/session/pending request/resource 状态可重放并有明确 terminal result | orchestrator 结果不能外推到 subagent extension |

机器可读问题清单见 [questions.json](../questions.json)。
