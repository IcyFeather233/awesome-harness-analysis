# Context、Memory 与 Compaction

> **证据边界。** 本报告分析 source-only commit `16a676f`。其 1,884 个 TS/TSX 文件、关键 symbol 与 feature gates 和论文所述 Claude Code v2.1.88 corpus 强指纹一致，但缺少 package version、上游 tree hash、build manifest，不能视为已证明的 exact 官方 artifact。快照仍有 657 个无法解析的相对 import；除 SiFlow 协议探针外，主循环、安全、session 与 subagent 结论均为 static-only。官方材料只支持产品立场，五价值/十三原则是 analyst synthesis。[X: X-001–X-003] [D: D-001–D-008] [C: C-001, C-024–C-026] 首次遇到缩写或内部名词时，可查 [全局术语表](16-glossary.md)。


![Claude Code context lifecycle](../diagrams/generated/assets/03-context-lifecycle.png)

*读者图问题：哪些信息在什么时机进入模型，又经过哪些变换？ 这是 gpt-image-2 读者插图；当前实现边均为 static-only，结构化证据与排除项见 [图片元数据](../diagrams/generated/metadata.json)。*

## 生命周期词典：何时进入、保留多久、是否可恢复

Context 来源不能只按“内容是什么”分类，还要同时回答三个问题：什么时候加载、会携带多久、进程重启后能否恢复。

- **Startup**：建立 session 或 reload 时计算的基线，例如 system prompt 的稳定部分、启动时可见的 project instructions。它可能在配置变化后重算，所以不是“进程一生永不变化”。
- **Lazy**：先记录可发现性，只有任务触发时才加载完整内容。例如 skill 只有被选中时才把详细 instruction 带入 context；目录规则可能在访问对应路径后出现。
- **Per-turn**：为当前用户提交或当前 iteration 生成，例如 diagnostics、task notification、queued input 和最新 tool result。下一轮是否继续携带取决于它是否被写入 message chain。
- **Carry-forward**：已经进入 live message chain，并继续出现在后续 model request 中，直到被 boundary projection、snip 或 compaction 替换。
- **Durable**：已经写到 JSONL 或文件，进程退出后仍存在。durable 不代表模型每轮都看到它；resume 时仍要经过恢复和 context selection。

例如 Bash 的输出最初是 per-turn tool result；追加到 messages 后成为 carry-forward；transcript flush 后又具有 durable copy；之后 microcompact 或 summary boundary 可能只保留 preview/摘要。生命周期是可叠加状态，不是互斥标签。

| 图中标签 | 生命周期 | 典型内容 | 读者注意 |
|---|---|---|---|
| System Prompt | startup/reload，部分 section 会随 mode、tool set 或配置重算。 | tone、task policy、tool/mode guidance、稳定环境说明。 | 它是 provider request 中高优先级内容，不等于项目 memory，也不代表每个 section 永久不变。 |
| CLAUDE.md + Rules | startup 与 lazy 混合；全局/项目规则可启动时加载，目录或 include 规则可能按需出现。 | managed/user/project/local 层级、目录规则、`@include`、add-dir。 | 它是可维护 instruction 来源，不是 transcript；include 还可能触发额外 approval。 |
| History JSONL | durable copy 与 carry-forward view 并存；resume 时再投影当前分支。 | user/assistant/tool chain、parentUuid、compact boundary、summary segment。 | JSONL 保存发生过的记录，模型本轮看到的是经过 selection/projection/compaction 后的 view。 |
| Runtime Attachments | per-turn 或 per-iteration 产生，部分写入消息链后变成 carry-forward。 | MCP/agent delta、skills、memory、tasks、diagnostics、queue、tool result preview。 | Attachment 不是用户原文；是否进入下一轮取决于 message assembly、预算和压缩处理。 |

[claudemd.ts](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/utils/claudemd.ts#L1) 保留来源 provenance，并处理多层目录、@include 和外部 include approval；[attachments.ts](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/utils/attachments.ts#L1) 区分 user-triggered、every-thread 与 main-only attachment。[S: S-012–S-013]

## Context 是有结构的位置，不只是字符串拼接

这里的 **system prompt** 是 provider request 中具有高指令优先级的 system 内容；**system context** 是 harness 计算出的环境/模式信息；**user context** 则以 user-side context block 形式加入项目规则、memory 和动态附件。它们都可能影响模型，但在 request 中的位置、cache 行为和指令优先级不同。

**Provenance** 指每段 context 的来源记录，例如来自 managed CLAUDE.md、用户级文件、项目文件、某个 skill 或某次 tool result。保留 provenance 能帮助 reload、approval 和调试，也让 compaction 后的“哪些来源仍然存活”可被追踪。

System prompt/context 放产品约束、tool/mode guidance 与稳定环境信息；user context 则把 CLAUDE.md、memory、skills、MCP/agent/tool delta 和 runtime attachments 以可追踪来源带入消息链。`CLAUDE.md` 还分 managed、user、project、local 与目录层级，可通过 `@include` 引入外部文件；auto memory 是可审计文件，不等于 transcript。[D: D-005–D-006] [S: S-010–S-013]

## Compaction 不是一个摘要按钮

| 实际顺序 | Stage | 条件 | 主要效果 | 不是 |
|---|---|---|---|---|
| 1 | Tool-result budget | 常规路径，优先处理旧工具输出占用。 | 缩减或替代高体积 tool result，使后续 request 先释放低价值 token。 | 不是整段会话摘要，也不改变所有历史消息。 |
| 2 | History snip | `HISTORY_SNIP` feature 条件满足时。 | 从当前 projection 中剪掉符合条件的历史 segment，降低进入本轮 request 的历史量。 | 不是删除 durable transcript；被 snip 的记录仍可能存在于 JSONL。 |
| 3 | Microcompact | 常规路径；cache 行为另受 feature 控制。 | 对旧内容/结果做细粒度清理，尽量在不生成大摘要的情况下回收 token。 | 不是 autocompact，也不一定产生新的 summary boundary。 |
| 4 | Context collapse | `CONTEXT_COLLAPSE` feature 条件满足时。 | 条件性折叠更大历史结构，作为更强的 projection/替代机制。 | 源码存在不证明 external bundle 一定启用。 |
| 5 | Autocompact | token threshold/config 满足且前序处理仍不足或策略要求时。 | 通过模型生成 summary boundary，并重注入仍需保留的文件、plan、skill、MCP/agent/tool delta。 | 不是无损压缩；survivor 需要单独检查。 |
| 6 | Hard-limit recovery | 上述步骤后仍 prompt-too-long、max-output 或 request 不合法。 | 尝试最后恢复、报错或 terminal transition，避免构造非法 model request。 | 不是日常 memory 管理 stage，而是失败收束路径。 |

这个顺序直接来自 [query.ts ordered shapers](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/query.ts#L365)；早先报告把 microcompact 与 history snip 颠倒，已由逐语句 source-order audit 纠正。[S: S-014] [C: C-007]

这些 stage 处理的粒度不同：

- **Tool-result budget** 优先缩减旧工具输出，因为它们往往体积大、可由文件路径或 preview 替代；它不等于总结整段对话。
- **History snip** 按条件把某些旧 message segment 从本轮 projection 中剪掉，原始 durable transcript 不一定同时消失。
- **Microcompact** 做更局部的内容清理，目标是先回收低价值 token，避免立即调用模型生成大摘要。
- **Context collapse** 是 feature-gated 的更大范围结构折叠；“源码存在”不证明 external build 启用。
- **Autocompact** 在 threshold/config 满足时生成 summary boundary，用摘要替代较老 history，同时重注入仍需要的文件、plan、skill 和动态状态。
- **Hard-limit recovery** 是前述处理后仍无法形成合法 request 时的最后恢复/终止路径，不是第六种日常 memory。

`boundary` 是“从哪里开始把摘要视为新的有效历史起点”；`survivor` 则是 compaction 后仍被明确保留或重新注入的信息。判断 compaction 质量不能只看 token 数，还要检查关键约束和 provenance 是否成为 survivor。

`compactConversation` 通过另一次模型调用生成 summary boundary，再有限重注入近期文件、plan、skill、MCP/agent/tool delta。[S: S-015] 这些机制分别可能清理旧结果、投影历史段，或用摘要替换历史。Memory 与 transcript 都会进入 context，但前者是可维护知识来源，后者是 durable execution history；所有权和恢复语义不同。[S: S-012–S-015, S-029]

最大未知项是摘要信息损失、实际 threshold、启用的 feature projection 和长任务语义漂移。需要可运行构建强制 overflow，再比较压缩前后 request envelope 与 resume。[技术证据图](../diagrams/context-lifecycle.svg)
