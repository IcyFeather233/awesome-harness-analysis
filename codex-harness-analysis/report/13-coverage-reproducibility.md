# 覆盖率与复现

## 结构化产物

- [manifest.json](../manifest.json): commit、配置、隔离与 runtime
- [inventory.json](../inventory.json): 有界确定性仓库清点
- [hir.json](../hir.json): 29 nodes / 38 edges 的 harness IR
- [claims.jsonl](../evidence/claims.jsonl): 23 个可证伪 claims
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

当前 bundle 包含 29 个 HIR nodes、38 条 edges、23 个 claims 和 46 条 evidence records。图片不新增任何 claim；它们只是这些结构化事实的读者投影。

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

`C-001`–`C-023` 的声明、evidence、coverage 与 falsification test 以 [claims.jsonl](../evidence/claims.jsonl) 为唯一索引；图只做语义投影，不新增事实。
