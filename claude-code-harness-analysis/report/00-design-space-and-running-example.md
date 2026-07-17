# 设计空间与静态 Running Example

> **证据边界。** 本报告分析 source-only commit `16a676f`。其 1,884 个 TS/TSX 文件、关键 symbol 与 feature gates 和论文所述 Claude Code v2.1.88 corpus 强指纹一致，但缺少 package version、上游 tree hash、build manifest，不能视为已证明的 exact 官方 artifact。快照仍有 657 个无法解析的相对 import；除 SiFlow 协议探针外，主循环、安全、session 与 subagent 结论均为 static-only。官方材料只支持产品立场，五价值/十三原则是 analyst synthesis。[X: X-001–X-003] [D: D-001–D-008] [C: C-001, C-024–C-026]


## 六个设计问题

| 问题 | 当前机制 | 可替代方案 | 分析者判断 | 证据 |
|---|---|---|---|---|
| 界面与 loop 是否耦合 | 多入口，共用 query() | 每界面独立 controller | 共享语义减少漂移，state 适配面更大 | C-002–C-004 |
| context 是快照还是流水线 | startup、lazy、per-turn、durable 来源合流 | 每次重建完整 prompt | 有利于 cache/成本，却增加 provenance 与压缩复杂度 | C-006–C-007 |
| registry 是否等于可见工具 | 不是；组装、过滤、exposure、dispatch 分层 | 固定工具全集 | 动态能力面灵活，也更难证明实际暴露范围 | C-010–C-011 |
| approval 与 isolation 是否一件事 | permission 后才是可选 sandbox | 强制 sandbox、无交互审批 | 两层可独立配置，也容易混淆 | C-012–C-014 |
| child 默认共享什么 | context/tool/transcript 分开，workspace 默认共享 | 每 child 强制 worktree | 协作快，写冲突需由任务划分承担 | C-017–C-020 |
| resume 是否是 rollback | 恢复 JSONL，会话外文件继续存在 | 事务式 workspace snapshot | 符合 CLI 工作流，但不能当撤销 | C-015–C-016 |

收益、代价和替代方案均是分析者综合，不是作者动机。官方产品材料可作为 D evidence 支持 human control、sandbox、context scarcity、memory 与 team 等产品立场，但“五价值/十三原则”仍是分析者对 D 与 S 的归纳，不是 Anthropic 正式 taxonomy。[D: D-001–D-008] [I: I-003, I-005] [C: C-024, C-027]

## 静态 running example：一次需要工具的用户提交

![一次 query 的模型工具循环](../diagrams/generated/assets/02-turn-flow.png)

*读者图问题：一次用户 query 如何跨多个 model request 与 tool call 迭代？ 这是 gpt-image-2 读者插图；当前实现边均为 static-only，结构化证据与排除项见 [图片元数据](../diagrams/generated/metadata.json)。*

1. REPL 的 QueryGuard 获得执行权，或 headless QueryEngine 启动；两者准备 context 与工具后调用 query()。[S: S-004–S-006]
2. queryLoop 处理 tool-result budget、压缩候选和 hard limit，再构造一次模型请求。[S: S-007, S-014]
3. 若流中出现 tool_use，router 查找工具、验证 schema/input，运行 pre-tool hook 和 permission decision。[S: S-022–S-024]
4. 允许后，Bash 等工具可能先经过 sandbox wrapper，再由 Shell spawn；拒绝则生成模型可消费的 error result。[S: S-025–S-027]
5. tool_result 与运行时附件进入下一次 context；没有 tool call、达到 max turns、hook stop、abort 或不可恢复错误时退出。[S: S-008–S-009]

Model Stream 是一次 API request；Continue Loop 是同一用户提交中的下一次 agentic iteration；Stop 是 query() 的 terminal transition。三者都不等于 durable session。这个例子是源码路径演练，不是 runtime trace。[技术证据图](../diagrams/turn-flow.svg)

不能由此推出：external bundle 包含所有 feature path、真实模型一定选某工具、permission denied 的 OS 层绝无副作用，或该路径在生产中的频率。
