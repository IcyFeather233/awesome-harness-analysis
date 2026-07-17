# 与 arXiv 2604.14228v2 的对照

> **证据边界。** 本报告分析 source-only commit `16a676f`。其 1,884 个 TS/TSX 文件、关键 symbol 与 feature gates 和论文所述 Claude Code v2.1.88 corpus 强指纹一致，但缺少 package version、上游 tree hash、build manifest，不能视为已证明的 exact 官方 artifact。快照仍有 657 个无法解析的相对 import；除 SiFlow 协议探针外，主循环、安全、session 与 subagent 结论均为 static-only。官方材料只支持产品立场，五价值/十三原则是 analyst synthesis。[X: X-001–X-003] [D: D-001–D-008] [C: C-001, C-024–C-026]


对照对象是 [Dive into Claude Code: The Design Space of Today’s and Future AI Agent Systems](https://arxiv.org/html/2604.14228v2)。论文明确分析 Claude Code v2.1.88 的 1,884-file TypeScript corpus；本地快照的 TS/TSX 数量及高辨识度 symbols/feature gates 强匹配，但缺少 exact tree 证明。[X: X-003] [C: C-026]

## 不是“谁更长”，而是回答层级不同

| 维度 | 论文 v2 | 本报告改进前 | 本次改进后 | 仍有差距 |
|---|---|---|---|---|
| 研究 framing | 五 values、十三 principles、未来设计空间 | 机制章强，价值层弱 | 新增 D→I→S 的价值/原则/机制章 | taxonomy 仍需跨 harness 验证 |
| 版本身份 | 直接称 v2.1.88 | 只写 unknown | strong fingerprint / exact unproven | 需要 npm/tree hash |
| 核心 loop | turn flow 清楚，机制描述密集 | 生命周期词更精确 | 扩成九阶段，保留 Session/query/iteration/request 区分 | 无 runtime trace |
| Context | hierarchy、mutability、accessibility 表达强 | provenance/compaction 较强 | 补 context 结构、五阶段真实顺序与条件 | 压缩损失未量化 |
| Extensions | Figure 5 的注入位置很有效 | 主要是 capability pipeline | 新增 Assemble/Model Surface/Authorize-Execute 投影 | 未安装 fixture 实测 |
| Permissions | 分层治理叙述强 | canonical path 与 audit 边界更谨慎 | 精确区分 5 external、feature-gated auto、internal bubble；补 resume grants | process-wide audit 未跑 |
| Subagents | isolation 与 agent types 易读 | child 机制/取消/后端区分更细 | 补 derive+override 权限矩阵 | 没有 child runtime matrix |
| Persistence | session 图直观 | JSONL/parentUuid/sidechain 更具体 | 补 trust freshness；避免把 resume 画成 rollback | corruption/SIGKILL 未测 |
| 可复现性 | 论文给 methodology，但无机器可读 claim graph | HIR/evidence/scenario 较强 | 29 claims、62 evidence、54 edges、benchmark appendix | snapshot 不可启动 |
| 图像 | 论文图密度高，按研究问题投影 | 读者图风格统一但少三类投影 | 新增 3 个 story spec/prompt 与 caption/glossary/exclusions contract | 外部 API 待授权；生成后仍需人工语义审核 |

## 论文做得更好的地方

1. **解释链完整。** 它不是从文件树开始，而是用 values/principles 组织 mechanism，读者更容易理解“为什么这个细节值得看”。本报告原先大量使用 I evidence，却没有足够 D evidence 约束价值判断。
2. **机制 census 更密。** 论文显式列出 compaction variants、hook event、permission modes、extension categories 与 built-in agents，使读者能感知设计表面大小。
3. **图按问题投影。** Figure 3、5、6 分别回答 layered responsibility、extension injection、context hierarchy；它们没有把完整 call graph 塞进一张图。
4. **研究讨论更远。** 它把 Claude Code 放进 agent systems design space，并讨论 future directions；本报告主要是单仓 source-grounded recovery。

## 本报告更强或更谨慎的地方

1. **版本与证据不越级。** “1,884 files 一致”只能给 strong fingerprint，不能给 exact identity；paper conclusion 也不直接当 S evidence。
2. **生命周期词更精确。** Session、一次用户 query、agentic iteration 与 API request 分开，避免把一个 tool loop 误叫一个 session/turn。
3. **条件计数更精确。** external modes 是五个；`auto` feature-gated 且 externalize 为 default；`bubble` internal-only。source union 不是 production UI census。
4. **安全声明保留反例空间。** canonical tool path 有 permission gate，不自动证明 startup、hooks、MCP lifecycle、bridge/daemon 的所有副作用都走同一 gate。[C: C-014]
5. **Subagent 不被压成一个盒子。** normal/fork、sync/async、worktree、in-process teammate 与 terminal-pane teammate 的 context/process/workspace/transcript/cancellation 边界分别描述。
6. **可审计产物更完整。** 每条重要结论回到 evidence ID；图只是解释层，HIR/claims/observations/scenarios 才是 structured truth。

## 对照时发现并纠正的实质问题

最重要的事实修正是 compaction source order。旧报告写成 `budget → microcompact → history snip`；逐语句检查 [query.ts](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/query.ts#L365) 后确认是 `budget → optional HISTORY_SNIP → microcompact → optional CONTEXT_COLLAPSE → autocompact`，之后才进入 hard-limit/recovery。[S: S-014] [C: C-007]

另外三处不是简单补字，而是改变模型：

- Plugins 从“另一种扩展”改为跨 hooks/commands/agents/skills/output styles/channels/MCP/LSP/settings/user-config 的 packaging layer。[S: S-046]
- Permission state 从“resume 恢复 mode”细化为“恢复 conversation metadata，但不反序列化 session-scoped grants”。[S: S-044] [C: C-029]
- 五 values/十三 principles 明确标 I evidence；官方材料只支撑 product stance，不把 analyst taxonomy 冒充作者原话。[D: D-001–D-008] [C: C-024, C-027]

## 图像质量差异与本次策略

论文图的优势是信息架构：有限颜色、清晰分组、箭头承担语义、一个 figure 只回答一个问题。弱点是部分标签把 build-time/internal/source-visible 机制并列，且图边没有逐条 evidence link。旧报告的 gpt-image-2 图更统一、视觉更轻，但缺少 layered architecture、extension injection 和 values-to-mechanisms 三个研究投影。

本次新增三张正文图的 story spec 与 gpt-image-2 prompt；由于自定义外部 API 的凭据发送在本轮被审批器拒绝，当前报告不嵌入这三张未生成图片。已有八张位图继续使用；全部图强制四项 caption contract：

- `question`：这张图只回答哪个问题；
- `glossary`：首次出现的缩写/项目内名词如何解释；
- `exclusions`：图明确不表达什么；
- `evidence_ids`：结构来自哪些 D/S/X/I records。

技术 SVG 继续保留为可重复生成的 evidence map，但正文只嵌入 gpt-image-2 PNG。生成图不是事实源；如果文字顺序、计数或箭头与 structured spec 冲突，就应拒收/重生成，而不是用 caption 修补错误图片。

## 剩余最高价值工作

当前最大差距不是再写一章，而是 **target runtime evidence 为零**。拿到同 commit 的 package/build artifact 后，优先运行：ordered context envelope capture、permission denied side-effect matrix、session-grant resume test、sync/async child inheritance matrix 与 compaction-before/after request digest。完成这些实验后，报告才会从 source-grounded architecture recovery 升级成 active harness archaeology。
