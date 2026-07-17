# 范围、证据与方法

> **证据边界。** 本报告分析 source-only commit `16a676f`。其 1,884 个 TS/TSX 文件、关键 symbol 与 feature gates 和论文所述 Claude Code v2.1.88 corpus 强指纹一致，但缺少 package version、上游 tree hash、build manifest，不能视为已证明的 exact 官方 artifact。快照仍有 657 个无法解析的相对 import；除 SiFlow 协议探针外，主循环、安全、session 与 subagent 结论均为 static-only。官方材料只支持产品立场，五价值/十三原则是 analyst synthesis。[X: X-001–X-003] [D: D-001–D-008] [C: C-001, C-024–C-026]


## 冻结对象

| 字段 | 值 |
|---|---|
| 本地仓库 | /volume/med/work/users/mzchen/work/claude-code |
| remote | https://github.com/IcyFeather233/claude-code.git |
| commit | 16a676ffa36eadbfb28eec39007dff73941346b1 |
| branch / dirty / tag | main / clean / 无 tag |
| 目标身份 | source-only public mirror；与论文 v2.1.88 corpus 强指纹一致，exact artifact 未证明 |
| README | 按用户要求，不把人为 README 架构叙述作为证据 |

分析按 14 个 module 深读入口、loop、context、compaction、provider、tools、permission、sandbox、workspace、session、subagent、orchestration、observability 和 recovery。重要结论先写 claim，再关联 evidence，最后投影到 HIR 与图。

本轮 D 是 first-party 产品材料，S 是源码结构，X 是控制实验，I 是分析推断。没有 R，因为 target harness 未启动。论文只作为 prior-analysis benchmark 和反例线索，不直接作为实现真值。[C: C-024–C-026]

## 版本指纹，而不是版本猜测

本快照有 1,884 个 TS/TSX 与 18 个 JS/JSX 文件。论文明确报告 v2.1.88 corpus 有 1,884 个 TypeScript 文件；本地还命中同一批高辨识度符号和 feature gates，包括 `HISTORY_SNIP`、`CACHED_MICROCOMPACT`、`CONTEXT_COLLAPSE`、`TRANSCRIPT_CLASSIFIER` 与 `MAX_OUTPUT_TOKENS_RECOVERY_LIMIT=3`。[X: X-003] [C: C-026]

这构成 **strong fingerprint match**，但缺少 package version、上游 tree hash、lockfile/build manifest，不能升级为 exact match。分析对象因此仍固定为 commit，而不是把论文版本号写进源码事实。

## 可运行性安全门

scan_snapshot.py 在 1,902 个 TS/JS 文件中发现 12,958 个相对 import，其中 657 个目标缺失；顶层没有 package manifest、lockfile 或 tsconfig。这不是只安装 Bun 即可修复的缺口：依赖图和 feature() 构建值都不完整。[X: X-001]

SiFlow 探针确认 endpoint 可用：Anthropic /v1/messages、SSE、强制 tool use 都是 HTTP 200；关闭默认 thinking 后得到 echo({text: hello})。它排除了 provider 基础方言不兼容，却不能补全快照。[X: X-002]

## 有效性威胁

- 无 tag/package manifest，虽然与 v2.1.88 corpus 强指纹一致，仍不能证明 exact artifact identity。
- feature() 是编译时 DCE；源码存在不等于 external bundle 存在。
- loop、安全、resume、child 均无 target runtime evidence。
- 缺失文件既有 type-only 也有实际模块，不能整体忽略。
- 源码注释只能解释局部机制，不能自动升级为产品动机。

复现材料：[manifest](../manifest.json)、[完整性扫描](../experiments/snapshot-integrity.json)、[provider probe](../experiments/provider-probe.json)、[coverage](../evidence/coverage.json)。
