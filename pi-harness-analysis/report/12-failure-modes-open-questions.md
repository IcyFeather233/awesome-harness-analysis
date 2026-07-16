# 12 失败模式与开放问题

## 已验证或源码明确的 failure path

| 失败 | 当前行为 | Evidence |
|---|---|---|
| Provider retryable error | 指数退避；maxRetries 有界；live context 移除 error，session 保留 | `S-010`, `X-003` |
| Context overflow | compact；错误型 overflow 最多自动 retry 一次 | `S-009`, `X-003` |
| Length-truncated tool call | 全部拒绝执行，返回 error result | `S-001`, `X-001` |
| Tool exception | 转为 `isError` toolResult，进入模型 context | `S-001`, `X-001` |
| Bash timeout/abort | kill process tree；输出保留并带状态 | `S-007` |
| Session file 非空但无合法 header | 拒绝打开 | `S-008` |
| New AgentHarness hook failure | 归一化 AgentHarnessError；某些 post-commit hook failure 不回滚 | `D-003`, `S-011` |
| Orchestrator child exit | instance 标 error、reject pending、清理 resources | `S-016` |

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

1. AgentSession vs AgentHarness differential scenario suite。
2. Container/VM 内的 permission bypass matrix：built-in、`!`、custom tool、extension direct process、subagent。
3. JSONL corruption matrix：header/middle/tail/parent/compaction/leaf。
4. Provider proxy capture：context source differential + redaction。
5. Orchestrator restart/crash 与 child cleanup。

机器可读问题清单见 [questions.json](../questions.json)。
