# 模型接口、工具与扩展

当前 Coding Agent 的模型入口由 `ModelRegistry` 和 `pi-ai/compat` 连接；工具则由 registry 保存定义，active set 决定本次模型可见的能力。Extensions 可以在输入、消息、工具和 provider 边界参与处理。[S: S-003, S-023, S-024]

## 当前模型请求怎样分派

`createAgentSession()` 为 `Agent` 安装 stream wrapper。每次请求先通过 `ModelRegistry.getApiKeyAndHeaders()` 解析鉴权，合并环境、headers、timeout 和 provider retry 配置，再调用从 `pi-ai/compat` 导入的 `streamSimple()`。[S: S-024]

compat 内部有两个分支：模型匹配内置 catalog，且对应 API 没有被覆盖时，转给 `compatModels.streamSimple()`；否则按 `model.api` 从 API registry 取出实现再调用。自定义 `models.json` 和 extension 的 provider 注册由这套产品配置路径接入。

`Models` 在这里是 compat 内置分支使用的 provider/model 集合。产品层的注册、鉴权与 compat 分派共同构成当前 CLI 的模型路径。历史 SiFlow 场景证明指定自定义端点曾成功接入，并未遍历全部分派分支。[C: C-019; S: S-012, S-024; R: R-001, R-005]

定位：[sdk.ts](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/sdk.ts#L301)、[compat.streamSimple](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/ai/src/compat.ts#L265)。

模型分派选定调用实现后，provider 适配器负责 API 字段，服务端负责模型对应的序列编码。system、messages 和 tools 怎样在这两层转换，以及 Qwen3.8-27B 与 DeepSeek V4 Flash 的格式差异，见[从 Pi 的请求到模型输入](18-model-input-encoding.md)。

## Registry、active set 和工具说明

内置工具定义有 `read`、`bash`、`edit`、`write`、`grep`、`find`、`ls` 七个名称。新 session 的默认 active set 是前四个；CLI/SDK 选项可以调整可用集合。Extension 和 SDK custom tools 按名称加入注册表，同名定义可能替换当前实现。[S: S-003; C: C-004]

| 工具 | 默认新 session | 基本作用 |
|---|---|---|
| read | active | 读取文本或图片，处理分页与输出限制 |
| bash | active | 在 cwd 启动 shell，支持 timeout 与 abort |
| edit | active | 按 old/new 文本修改文件 |
| write | active | 创建或覆盖文件 |
| grep | 需显式启用 | 搜索文件内容 |
| find | 需显式启用 | 按 pattern 查找路径 |
| ls | 需显式启用 | 列出目录内容 |

工具 schema 来自 `agent.state.tools`。system prompt 中的工具摘要还取决于相应 `promptSnippet`；说明文字与真实 tool schema 是两个输出位置。`setActiveToolsByName()` 更新 active set 并重建基础提示；产品层的 `prepareNextTurn` 把当前工具、system prompt、model 和 thinking level 接到下一请求。[S: S-004, S-023]

本次动态工具测试验证了注册后的 registry、active set、来源元数据及 prompt 更新。完整的请求中途配置差分仍需独立测试。[C: C-026; X: X-005]

## 工具输出有模型与应用两个消费方

工具返回的 `content` 提供文本或图片，`details` 保存供日志或界面使用的结构化数据。`createToolResultMessage()` 把两者保留在应用消息中，TUI 的 result renderer 也能拿到两者。已经检查的 OpenAI Completions 和 Anthropic 序列化路径从 `content` 构造模型结果，没有自动把 `details` 展开成正文。[C: C-027; S: S-025, S-026]

例如，搜索工具可以把摘要放在 content，把界面需要的结构化命中项放在 details。这个例子说明如何使用接口，不代表当前 built-in 的具体返回格式。是否把 details 进一步暴露给模型仍取决于 extension 和 provider 实现，不能把这个字段当成保密区。

## Hook 在哪些位置生效

| Hook | 所在位置 | 对行为的作用 |
|---|---|---|
| input | skill/template 展开之前 | 处理输入或变换内容 |
| before_agent_start | 普通 prompt 进入 Agent 之前 | 追加 custom messages 或覆盖该次 system prompt |
| context | 每次模型请求的消息转换之前 | 变换请求消息视图 |
| message_end | 产品层处理最终消息时 | 可替换最终消息，随后进入监听通知和持久化 |
| tool_call | 参数校验之后、execute 之前 | 可阻断该调用并返回理由 |
| tool_result | 实际 handler 结束之后 | 调整 content、details 和错误标记 |
| provider hooks | header、payload、response 边界 | 调整请求或观察响应 |
| session hooks | compact、switch、fork 等操作周围 | 参与会话生命周期 |

`AgentSession` 安装的工具 hook 在执行时读取当前 extension runner，reload 因而可以换用新 runner。Extensions 与主进程拥有相同运行权限；工具 hook 的 block 约束经过该入口的调用，extension 自己的文件或进程操作另有执行路径。[S: S-003, S-019; D: D-002]

Skills 提供可发现、可加载的任务指令。MCP 和 subagent 在这个版本的默认核心中没有对应的内置工作流，可由 extension 接入。分析具体环境时，要检查实际加载的扩展和 active tools。[D: D-004]


## 扩展怎样形成可迭代的工作流

[Armin 的使用记录](https://lucumr.pocoo.org/2026/1/31/pi/)把持久扩展状态和热重载视为持续修改工具的基础。[I: I-001]

当前代码中，`appendEntry()` 把扩展数据写成 custom entry，`buildSessionContext()` 不会自动把这种 entry 送给模型。调用 `AgentSession.reload()` 时，方法先通知 shutdown，再刷新 settings、provider registry 和 resources，重建 runner 与 tool registry；存在相应 bindings 时，再发出 reload 原因的 `session_start`。扩展需要自己从会话记录恢复所需状态，不能假定旧 closure 或 UI 对象自动保持有效。[C: C-028; S: S-008, S-027]

[Julian Prokay](https://jprokay.com/post/018-pi-coding-agent)的任务管理实践将 CLI/SQLite 状态与 Pi 界面扩展分工。它提供了一个使用案例：业务状态可以由应用维护，Pi extension 负责把操作接入会话。[B-11，见来源目录]

## CLI、Skills 和命名工具怎样分工

[Mario 的浏览器工具文章](https://mariozechner.at/posts/2025-11-02-what-if-you-dont-need-mcp/)展示了按需读取说明、再组合脚本的做法。[D: D-012]

对应本版本，read/bash 提供读取说明和执行程序的入口；skill 负责指令的发现与加载，命名工具还提供 schema 校验和结构化回填。额外能力可以存在于工作区程序中，而不必每项都变成初始 tool schema。应检查实际 active set、加载内容和执行后端，而不是用“四个默认工具”推断能力上限。[S: S-001, S-002, S-003]

这也不构成 CLI 普遍优于 MCP 的证据。作者较早的[终端工具实验](https://mariozechner.at/posts/2025-08-15-mcp-vs-cli/)使用 Claude Code，结果随任务与接口形式而变化；其数字不属于本报告的 Pi 实验。
