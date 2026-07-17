# 失败模式与开放问题

> **证据边界。** 本报告分析 source-only commit `16a676f`。其 1,884 个 TS/TSX 文件、关键 symbol 与 feature gates 和论文所述 Claude Code v2.1.88 corpus 强指纹一致，但缺少 package version、上游 tree hash、build manifest，不能视为已证明的 exact 官方 artifact。快照仍有 657 个无法解析的相对 import；除 SiFlow 协议探针外，主循环、安全、session 与 subagent 结论均为 static-only。官方材料只支持产品立场，五价值/十三原则是 analyst synthesis。[X: X-001–X-003] [D: D-001–D-008] [C: C-001, C-024–C-026] 首次遇到缩写或内部名词时，可查 [全局术语表](16-glossary.md)。


## 风险术语

- **Identity gap**：知道本地 corpus 很像某个发布版本，但缺少 tree hash/package linkage，无法证明完全相同。
- **Reachability ambiguity**：源码里存在一条路径，但不清楚当前 build feature、mode 和 runtime config 是否能走到它。
- **DCE（dead-code elimination）**：构建时根据 feature 常量删除分支；被删除的源码机制不会出现在 external bundle。
- **Canonical path**：最主要、证据最完整的 model→tool 执行路径。证明 canonical path 有 gate，不等于证明所有后台/启动路径有相同 gate。
- **Semantic loss**：压缩后语法仍合法、任务仍能继续，但某些约束、事实或出处已经丢失。
- **Blind spot**：当前观测手段看不到的维度，例如没有 target spans 时无法知道生产 latency/frequency。

## 对分析结论影响最大的风险

1. **Snapshot identity gap**：1,884-file/symbol fingerprint 强匹配论文 v2.1.88 corpus，但无 package version/tree hash/build manifest。缓解：所有 source URL 固定 commit，身份写 strong fingerprint 而非 exact。[C-001, C-026]
2. **Feature reachability ambiguity**：feature() 分支可能被 DCE。缓解：mode/extension/hook 计数都写条件，图不把 source-visible 分支标 runtime verified。[C-023]
3. **Process-wide policy gap**：canonical tool gate 很清楚，但 hooks/startup/MCP 等需独立 reachability audit。这是 open claim，不宣称已有 bypass。[C-014]
4. **Compaction semantic loss**：静态可列保留项，不能量化 summary 丢失。[C-007]
5. **Child isolation ambiguity**：普通 child、async、worktree、teammate/pane 的边界不同；用一个 subagent 标签会造成安全误判。[C-017–C-020]
6. **Session/workspace confusion**：resume/fork 不自动回滚普通 files。[C-016]
7. **Telemetry blind spot**：本轮没有 target spans，无法报告性能、成本和频率。[C-021, C-025]

## 优先实验队列

`P0` 表示不解决就会动摇核心安全/版本结论，`P1` 是重要行为边界，`P2` 是在核心模型稳定后补充的排序与鲁棒性问题。

| 优先级 | 可证伪问题 | 为什么优先 | 判别数据 |
|---|---|---|---|
| P0 | 哪个 feature set 构成 external bundle。 | 直接决定 source-visible path 能否代表用户可达产品；没有它，mode、hook、auto、collapse 等计数都只能写条件。 | build manifest、bundle strings、source map、entrypoint reachability、feature constant value。 |
| P0 | 非 canonical side effects 是否有等价 policy。 | 这是核心安全声明的反例空间：canonical tool path 受控不自动覆盖 startup、hooks、MCP lifecycle、bridge/daemon。 | process/file/network trace、permission events、hook events、MCP lifecycle logs、deny-path side effects。 |
| P1 | sync/async/teammate 的实际 inheritance。 | Subagent 隔离是多维概念，静态矩阵需要 runtime 验证 prompt owner、policy owner、workspace 和 cancellation。 | pid、cwd、tool list、effective mode、rule provenance、abort controller、transcript path、result channel。 |
| P1 | compact 后再 resume 保留什么。 | 它连接 context 质量和 persistence 语义；只看 token 数无法判断关键约束是否存活。 | 压缩前后 request digest、summary boundary、survivor list、restored history、resume 后 model-visible context。 |
| P2 | concurrent tools 的真实排序。 | 并发执行若与协议合并顺序不一致，可能污染模型看到的结果顺序。 | tool start/end span、original `tool_use` block order、context modifier merge order、error cancellation record。 |
| P2 | corrupted JSONL 如何降级。 | 影响恢复可靠性，但不先于 P0/P1；需要可运行 target 和可控损坏 fixture。 | controlled byte corruption、tail truncation、中间 parent 缺失、sidechain metadata 破坏、resume result。 |

## 产品风险与分析限制要分开

“某机制尚未验证”是分析限制；“源码显示存在无 gate 的副作用路径”才可能是产品风险。本轮只把 C-014 保留为待审计边界，没有将未运行状态包装成漏洞结论。
