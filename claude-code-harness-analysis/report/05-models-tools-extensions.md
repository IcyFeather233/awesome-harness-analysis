# 模型、工具与扩展

> **证据边界。** 本报告分析 source-only commit `16a676f`。其 1,884 个 TS/TSX 文件、关键 symbol 与 feature gates 和论文所述 Claude Code v2.1.88 corpus 强指纹一致，但缺少 package version、上游 tree hash、build manifest，不能视为已证明的 exact 官方 artifact。快照仍有 657 个无法解析的相对 import；除 SiFlow 协议探针外，主循环、安全、session 与 subagent 结论均为 static-only。官方材料只支持产品立场，五价值/十三原则是 analyst synthesis。[X: X-001–X-003] [D: D-001–D-008] [C: C-001, C-024–C-026] 首次遇到缩写或内部名词时，可查 [全局术语表](16-glossary.md)。


![Claude Code tool and extension surface](../diagrams/generated/assets/04-tools-extensions.png)

*读者图问题：能力如何变成模型可见 schema，再变成可执行 action？ 这是 gpt-image-2 读者插图；当前实现边均为 static-only，结构化证据与排除项见 [图片元数据](../diagrams/generated/metadata.json)。*

## 一项 capability 从“存在”到“执行”的状态链

1. **Installed/configured**：代码、plugin 或 MCP 配置存在于机器上。
2. **Registered**：loader/registry 已把它转换成候选 capability。
3. **Eligible**：当前 mode、feature、policy 和 provider 条件没有把它过滤掉。
4. **Visible schema**：name、description 和 input schema 被放进这一轮 model request；这是模型“知道可以调用”的边界。
5. **Requested**：模型真的返回匹配的 `tool_use` block。
6. **Dispatched**：router 找到实现并通过 schema/input validation。
7. **Authorized**：hooks/permission 决定允许该具体 input。
8. **Executed**：在可选 sandbox/外部 MCP backend 中运行，并生成 result。

因此“Claude Code 支持某工具”至少可能指前四种不同事实。安全分析必须说明自己证明到了哪一级。

## 固定快照的内置工具清单

这里的 **内置工具** 指由 `getAllBaseTools()` 在产品源码中组装的候选实现，不包括动态 MCP server tools、plugin/SDK 注入工具或单纯注入 prompt 的 skill 内容。候选工具还要经过 `getTools()` 的 simple/REPL mode、deny rule 和 `isEnabled()` 过滤，之后才可能成为当前 request 的 visible schema。[源码：base pool](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/tools.ts#L193) [源码：过滤](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/tools.ts#L271) [S: S-019]

### 常规 base candidates

| 工具名 | 作用 | 默认/条件边界 |
|---|---|---|
| `Bash` | 在 shell backend 执行命令并返回 stdout/stderr、退出和 background 信息。 | 常规 base candidate；simple mode 仍保留；具体命令还经过 permission/sandbox。 |
| `Read` | 读取文本、图片等文件内容，并执行范围、大小和 token 限制。 | 常规 base candidate；simple mode 仍保留。 |
| `Edit` | 对文件执行基于匹配内容的局部替换。 | 常规 base candidate；simple mode 仍保留。 |
| `Write` | 创建或覆盖文件。 | 常规 base candidate；simple mode 不包含；写入仍需具体 input 授权。 |
| `NotebookEdit` | 修改 Jupyter notebook cell。 | 常规 base candidate，但 `isEnabled()` 和当前文件/环境仍可过滤。 |
| `Glob`、`Grep` | 分别按路径模式和文件内容搜索。 | 当构建内嵌 bfs/ugrep 时两者从独立 tool pool 移除，搜索改由 shell 内嵌工具承担。 |
| `Agent`（legacy matcher: `Task`） | 启动具有独立 context/sidechain 的 child agent。 | 是否允许及 child tool set 受 agent type、mode、depth 和 policy 约束。 |
| `TaskOutput`、`TaskStop` | 读取 background task/agent 输出，或停止正在运行的 task。 | 只有存在对应 background task 时才有实际对象可操作。 |
| `SendMessage` | 向 team/agent 通信目标发送消息。 | 实现进入 base pool；有效目标取决于 team/agent runtime。 |
| `WebFetch`、`WebSearch` | 获取 URL 内容或使用 web search backend。 | backend、网络 policy、provider/build feature 和 enable state 可使其不可见或不可执行。 |
| `TodoWrite` | 写入旧版 todo list。 | Todo V2 开启时还会增加 task CRUD 工具；旧工具是否可见受 mode/config 影响。 |
| `EnterPlanMode`、`ExitPlanMode` | 进入或退出只规划工作流。 | 当前 mode 决定其中哪个工具有意义；名称存在不表示两者同时可用。 |
| `AskUserQuestion` | 暂停 autonomous path，向用户请求结构化选择或补充信息。 | headless/surface capability 会影响能否完成交互。 |
| `Skill` | 按名称加载并执行 skill 的 instruction/workflow。 | 工具本身内置；具体 skill 来自资源加载，不是另一项内置 executable tool。 |
| `SendUserMessage`（legacy: `Brief`） | 向用户发送消息/brief 类结果。 | base pool 中由 `BriefTool` 实现；旧名称只用于兼容匹配。 |

### 条件内置 candidates

| 条件 | 可能增加的内置工具 | 不能推出 |
|---|---|---|
| Todo V2 | `TaskCreate`、`TaskGet`、`TaskUpdate`、`TaskList` | 开启 Todo V2 不表示旧 transcript 中的 todo 自动迁移。 |
| LSP / worktree | `LSP`；`EnterWorktree`、`ExitWorktree` | LSP 是语言服务入口；worktree 是 Git workspace 隔离，不是 container。 |
| Agent swarms / inbox | `TeamCreate`、`TeamDelete`、`ListPeers` | team capability 仍受 feature、agent role 和 runtime state 限制。 |
| REPL / shell variant | `REPL`、`PowerShell` | REPL mode 会隐藏部分 primitive tools；PowerShell 只在对应平台/配置启用。 |
| Tool discovery / MCP resources | `ToolSearch`；`ListMcpResourcesTool`、`ReadMcpResourceTool` | 后两个在 `getTools()` 中被列为 special tools，不属于普通 base visible set；MCP server 提供的动态 tool 仍是外部能力。 |
| Proactive/Kairos/triggers build | `Sleep`、`CronCreate`、`CronDelete`、`CronList`、`RemoteTrigger`，以及 `MonitorTool`、`WorkflowTool`、`WebBrowserTool` 等 build-gated class | source-only mirror 缺少部分条件模块，类名可以证明组装槽位，不能证明该构建中的最终 model-visible name 或 reachability。 |
| Ant-only / test / verification | `Config`、`TungstenTool`、`SuggestBackgroundPRTool`、`VerifyPlanExecutionTool`、`OverflowTestTool`、`TestingPermissionTool` 等 | 这些不是普通 public configuration 下稳定可见的工具；test-only 工具不能写入产品默认清单。 |

`StructuredOutput` 是协议生成的 synthetic output tool，MCP server tools 由 `assembleToolPool()` 动态合并；二者都不应与上表的普通 base candidates 混为一谈。由于该快照仍有 657 个 unresolved relative imports，条件模块只按固定源码中的组装槽位报告，不把缺失模块的 class name 冒充已验证 schema name。

## 图中层次与扩展名词

- **Built-in Tools**：Bash、Read/Edit/Write、search、Agent、Task、plan 等；进入 pool 仍受 mode、feature、deny 和 enabled state 影响。[S: S-019]
- **MCP Servers**：通过 Model Context Protocol 连接的外部 capability provider。server lifecycle 包括配置、启动/连接、列出 tools/resources/prompts、健康状态与关闭；一次 tool invocation 只是其中一个阶段。[S: S-020]
- **Plugins**：是 packaging/distribution 层，不是单一 runtime injection point。manifest 除 metadata 外可组合 hooks、commands、agents、skills、output styles、channels、MCP、LSP、settings 与 user config 十类 component surfaces。[S: S-046]
- **Skills**：主要把 prompt/workflow 内容按需注入 context，不天然构成 executable sandbox；其低初始 context cost 来自 progressive disclosure，而不是“免费”。[D: D-005] [S: S-013, S-033]
- **Tool Pool**：当前候选集合；built-in 在同名冲突时优先，并稳定排序。[S: S-020]
- **Visible Schemas**：真正发送给模型的 schemas。registry 存在不保证这一轮可见。[S: S-019–S-021]
- **Tool Router**：lookup、schema/input validation、hooks 和 permission 的共同执行路径。[S: S-022]
- **Tool Result**：执行输出被转换成与 `tool_use_id` 对应的模型消息。过大结果可能落盘，只向模型返回 preview/path；所以“工具完整 stdout”不一定等于“模型实际看到的 result”。
- **Hook**：在 27 类 lifecycle event 上运行的观察/修改/阻断逻辑。部分 hook 可以执行外部命令，因此既是扩展点也是需要单独审计的副作用表面。[S: S-028, S-043]
- **LSP**：Language Server Protocol 服务，向编辑/分析能力提供符号、诊断等语言信息；plugin 可以打包 LSP 配置，但它不是 MCP tool 的同义词。[S: S-046]

## Provider、retry 与 fallback

**Provider** 是模型服务的承载路径。direct Anthropic 直接调用 Anthropic API；Bedrock、Vertex 和 Foundry 分别通过 AWS、Google Cloud 和 Azure 承载接口。它们可以共享上层 Messages 语义，但认证、endpoint、header 和错误分类不同。

**Retry** 通常在同一 provider/model 上重试暂时性失败，例如 429/529 或断流；**fallback** 则切到不同 request mode、model 或 provider path。二者都可能让一次用户 query 包含额外 API request，但不会自动重放已经产生副作用的 tool call。

[getAnthropicClient](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/services/api/client.ts#L88) 选择 direct Anthropic、Bedrock、Vertex 或 Foundry。[Messages request builder](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/services/api/claude.ts#L1480) 负责 messages/system/tools、thinking、cache/beta headers 与 stream；[withRetry](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/services/api/withRetry.ts#L170) 处理 auth refresh、429/529、backoff、fallback 和 token correction。[S: S-016–S-018]

## SiFlow 结果

models route 返回 qwen3.6-35ba3b 与 262,144 context；Anthropic /v1/messages 非流式和 SSE 均 HTTP 200；带 tool_choice=echo 与 enable_thinking=false 时返回 tool_use，input 为 {"text":"hello"}。[X: X-002]

这证明协议子集可用，不证明完整 Claude Code request 兼容。真实 envelope 还含 beta headers、thinking/output config、prompt caching、复杂 schemas 与多轮 tool_result。[C: C-009, C-025]

六个不要混淆的等号：installed plugin ≠ enabled plugin；registered tool ≠ visible schema；visible ≠ model 一定调用；tool call ≠ permission allow；allow ≠ sandbox enabled；skill loaded ≠ 独立进程执行。[技术证据图](../diagrams/tool-extension-surface.svg)

## 四类扩展注入的是不同语义位置

> **读者图待生成。** 问题：MCP、Plugins、Skills、Hooks 分别注入 loop 的哪个语义位置？ evidence-grounded story spec 与 gpt-image-2 prompt 已生成；外部图像 API 尚未获本轮风险授权，因此当前不嵌入占位图或技术 SVG。

- **Assemble**：构造模型输入的阶段，决定 system/user context、instructions 和 attachments 中出现什么。
- **Model surface**：放进 request 的 tool schemas/resources/prompts，决定模型知道自己可以调用什么。
- **Authorize/execute**：模型提出 action 之后的 hook、permission、sandbox 和 backend，决定请求能否以及如何产生副作用。
- **Packaging**：把多种 component 一起分发、配置和启用；它不自动等于上述任一 runtime stage。

| 机制 | 主要注入点 | 模型/loop 实际得到什么 | Context 成本与治理 |
|---|---|---|---|
| Skills | Assemble，即 request 组装和 instruction 选择阶段。 | 先暴露短描述供发现；被任务命中后才加载详细 instruction、workflow 或 resource 到 context。 | 初始 token 成本低、使用后增长；skill 内容能指导模型，但不天然获得 shell/file 权限，也不是独立进程。 |
| MCP Servers | Model surface + execute，即模型可见 schema 与外部 server 调用边界。 | 动态 tool schemas、resources 或 prompts；调用时还要经过 MCP client lifecycle、tool dispatch 和 permission/治理。 | schema 可能常驻也可能按需暴露；server 已连接不表示所有 tools visible，更不表示具体 input authorized。 |
| Hooks | Assemble、authorize/execute、lifecycle，即生命周期事件上的观察、修改、阻断或外部命令回调。 | 27 个 hook event 可以读取上下文、改写行为或影响 permission/tool 结果；部分 hook 自身也会产生副作用。 | Event-driven，不是每个 hook 都进入 model context；因为能执行外部命令，所以需要与 tool path 分开审计。 |
| Plugins | Packaging fan-out，即把多种 component surfaces 一起分发、配置和启用。 | 可打包 commands、agents、skills、hooks、MCP、LSP、settings、output styles 等，但运行时仍落到各自机制。 | Plugin 自身没有统一 context 或 execution 语义；安装/启用/可见/执行必须拆开看。 |

这张图按“模型看见什么、模型能调用什么、动作能否/如何执行”分层，而不是按目录或安装格式分组。27 是当前 `HOOK_EVENTS` 常量的源码计数；十类是 manifest component groups，均受 snapshot/feature/config 条件限制，不能外推成所有生产构建始终启用。[S: S-043, S-046] [C: C-028]
