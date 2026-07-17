# 失败模式与开放问题

> **证据边界。** 本报告分析 source-only commit `16a676f`。其 1,884 个 TS/TSX 文件、关键 symbol 与 feature gates 和论文所述 Claude Code v2.1.88 corpus 强指纹一致，但缺少 package version、上游 tree hash、build manifest，不能视为已证明的 exact 官方 artifact。快照仍有 657 个无法解析的相对 import；除 SiFlow 协议探针外，主循环、安全、session 与 subagent 结论均为 static-only。官方材料只支持产品立场，五价值/十三原则是 analyst synthesis。[X: X-001–X-003] [D: D-001–D-008] [C: C-001, C-024–C-026]


## 对分析结论影响最大的风险

1. **Snapshot identity gap**：1,884-file/symbol fingerprint 强匹配论文 v2.1.88 corpus，但无 package version/tree hash/build manifest。缓解：所有 source URL 固定 commit，身份写 strong fingerprint 而非 exact。[C-001, C-026]
2. **Feature reachability ambiguity**：feature() 分支可能被 DCE。缓解：mode/extension/hook 计数都写条件，图不把 source-visible 分支标 runtime verified。[C-023]
3. **Process-wide policy gap**：canonical tool gate 很清楚，但 hooks/startup/MCP 等需独立 reachability audit。这是 open claim，不宣称已有 bypass。[C-014]
4. **Compaction semantic loss**：静态可列保留项，不能量化 summary 丢失。[C-007]
5. **Child isolation ambiguity**：普通 child、async、worktree、teammate/pane 的边界不同；用一个 subagent 标签会造成安全误判。[C-017–C-020]
6. **Session/workspace confusion**：resume/fork 不自动回滚普通 files。[C-016]
7. **Telemetry blind spot**：本轮没有 target spans，无法报告性能、成本和频率。[C-021, C-025]

## 优先实验队列

| 优先级 | 可证伪问题 | 判别数据 |
|---|---|---|
| P0 | 哪个 feature set 构成 external bundle | build manifest、bundle strings、entrypoint reachability |
| P0 | 非 canonical side effects 是否有等价 policy | process/file/network trace + permission events |
| P1 | sync/async/teammate 实际 inheritance | pid、cwd、tools、mode、abort、transcript matrix |
| P1 | compact 后再 resume 保留什么 | request digest、boundary、restored history |
| P2 | concurrent tools 的真实排序 | start/end span 与 context modifier order |
| P2 | corrupted JSONL 如何降级 | controlled byte corruption + resume result |

## 产品风险与分析限制要分开

“某机制尚未验证”是分析限制；“源码显示存在无 gate 的副作用路径”才可能是产品风险。本轮只把 C-014 保留为待审计边界，没有将未运行状态包装成漏洞结论。
