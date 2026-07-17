# 设计决策与权衡

> **证据边界。** 本报告分析 source-only commit `16a676f`。其 1,884 个 TS/TSX 文件、关键 symbol 与 feature gates 和论文所述 Claude Code v2.1.88 corpus 强指纹一致，但缺少 package version、上游 tree hash、build manifest，不能视为已证明的 exact 官方 artifact。快照仍有 657 个无法解析的相对 import；除 SiFlow 协议探针外，主循环、安全、session 与 subagent 结论均为 static-only。官方材料只支持产品立场，五价值/十三原则是 analyst synthesis。[X: X-001–X-003] [D: D-001–D-008] [C: C-001, C-024–C-026] 首次遇到缩写或内部名词时，可查 [全局术语表](16-glossary.md)。


这里严格使用 `D → design question → S → I`：官方材料只支持产品目标，源码说明 mechanism，收益/代价仍是 analyst inference。不能把“官方强调 safety”直接写成“作者因此选择了某个函数结构”。

这张表是证据索引，不是完整解释。`D` 列只说官方材料公开强调了什么；`S` 列列出该快照的机制；`I/X` 列才是分析者提出的权衡与反例实验。相同一行中的 D 和 S 不构成已经证明的作者因果链。

| 决策 | First-party stance（D）只支持什么 | 当前机制（S） | Analyst tradeoff 与反例测试（I/X） | 证据边界 |
|---|---|---|---|---|
| 多 surface 共用 `query()` | 官方材料支持 iterative agentic loop 与可验证结果，但不直接说明每个入口的代码结构。 | REPL 的 QueryGuard/onQueryImpl 与 headless QueryEngine 都适配到同一 async generator。 | 复用 tool-result、stop 和 recovery 语义；风险在 UI/headless state 差异。反例测试是给两个入口相同 scripted response，diff event/message sequence。 | D-002；C-003–C-004。当前为 static-only，无双入口 runtime trace。 |
| Context 按生命周期合流 | 官方强调 context scarce、progressive disclosure、memory 可检查与 compaction。 | Prompt、CLAUDE.md、history JSONL、attachments、skills/MCP delta 进入五阶段 ordered shaper。 | 节省无关 context 并保留 provenance；代价是顺序、survivor 和摘要漂移难推理。反例测试是逐项 ablation 与 overflow envelope capture。 | D-005–D-006；C-006–C-007。压缩损失未量化。 |
| Registry 与 exposure 分离 | 官方 stance 支持按任务逐步呈现 capability。 | Tool pool、filter/eligibility、visible schema、dispatch/router 四层分开；MCP/skills/plugins/hooks注入不同位置。 | 动态能力强，审计面也更复杂。反例测试是 built-in/MCP 同名、enabled/disabled、mode 组合矩阵。 | D-005；C-010、C-028。未安装 fixture 实测。 |
| Permission 与 sandbox 分离 | 官方材料支持 human control、bounded autonomy 和 sandboxing 作为安全层。 | Policy decision 先判断 allow/ask/deny；Bash 等执行路径再按 settings/policy 选择 sandbox wrapper。 | 两层可组合，部署灵活；代价是 allow 容易被误读成 isolated。反例测试是同时记录 permission event、process tree、file diff、network attempt。 | D-001、D-003–D-004；C-012–C-014。canonical path 外副作用仍待审计。 |
| Child context 分离、workspace 默认共享 | 官方 team/subagent 材料支持 independent context 的产品概念。 | `runAgent` 重建 context/tool/MCP，写 sidechain；普通 child 默认共享 cwd，worktree 是显式选项。 | 节省 parent token 并便于共享 artifacts；代价是并发文件冲突。反例测试是默认 cwd 与 worktree 下的 same-file experiment。 | D-005、D-007；C-017–C-020。没有 child runtime matrix。 |
| JSONL append + parent chain | 官方 memory stance 支持可检查、可编辑、可延续，但不直接规定 transcript 格式。 | 主 session 与 sidechain 使用 JSONL、parentUuid、boundary 和 metadata；resume 不恢复 session-scoped grants。 | 易审计、易 fork；代价是 parent-chain reconstruction 与 corruption handling 复杂。反例测试是破坏尾记录、中间 parent、sidechain metadata。 | D-001、D-006；C-015–C-016、C-029。corruption/SIGKILL 未测。 |
| 多层 telemetry | 没有足够 first-party 架构意图，只能描述源码机制。 | Events、OTel spans、Query Profiler、Perfetto Trace 分别覆盖计数、时序、本地诊断和 timeline。 | 粒度可选；correlation、sampling 和 redaction 配置复杂。反例测试是并发 LLM/tool span correlation 与 sanitized payload 检查。 | C-021。没有 target interaction spans。 |
| Cleanup 优先的有界 shutdown | 没有足够 first-party 架构意图，只能评价可观察控制流。 | Persistence cleanup 先于 hooks/analytics，并有 cleanup race、hook budget、analytics cap 和 failsafe。 | 降低关键状态丢失风险；代价是 hung cleanup 会被时间预算截断。反例测试是注入慢 flush、慢 hook 和 signal。 | C-022。未做 signal/failure injection。 |

## 表中权衡的展开说明

**共享 query()** 的迁移价值是让 interactive/headless 复用相同 tool-result 和 stop 语义；风险在 surface adapter。验证方法不是比较函数名，而是给两个入口相同 scripted response，比较实际 event/message sequence。

**Context 生命周期合流** 的价值是按需加载和复用稳定内容；风险是 provenance、顺序和 compaction survivor。`ablation` 指一次只关闭一种来源，再比较 request envelope，从而判断该来源真正注入了什么。

**Registry/exposure 分离** 允许 MCP、mode 和 deferred discovery 动态改变模型所见工具；风险是审计者看到 registry 后误报能力面。`same-name/disabled matrix` 是用同名 built-in/MCP、enabled/disabled 和不同 mode 组合测试最终 visible schema 与 dispatch owner。

**Permission/sandbox 分离** 让策略判断与 OS 边界独立配置；风险是把 allow 当成 isolation。`side-effect matrix` 要同时记录 permission event、process spawn、文件 diff 和 network attempt，而不只看 UI 文案。

**Child context 分离但 workspace 共享** 减少 parent token 压力并方便共享 artifacts；风险是两个 child 同时修改同一文件。`same-file experiment` 应比较默认 cwd 与 worktree mode 下的冲突、保留路径和取消行为。

**Append-only JSONL** 便于追踪分支和 resume，但恢复依赖 parent-chain reconstruction；corruption test 应分别破坏尾记录、中间 parent 和 sidechain metadata。Telemetry/shutdown 两行缺少足够 D evidence，因此只评价可观察机制，不声称作者为何选择它们。

## 架构上最值得迁移的三点

第一，工具“存在、可见、被调用、被允许、被隔离、成功执行”应建模为六个状态，不应压成一个 capability edge。第二，subagent 隔离需要 context/process/workspace/policy/transcript/cancellation 六维矩阵。第三，resume 必须把 conversational state 与 external workspace state 分开描述。

## 不应迁移的假确定性

不能把 source-visible feature 当 production feature，不能把 analyst-normalized principle 冒充 Anthropic 官方 taxonomy，也不能把 provider probe 当 end-to-end harness validation。[C: C-023–C-027]
