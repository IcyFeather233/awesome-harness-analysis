# 术语表

| 术语 | 在本版本中的含义 |
|---|---|
| Harness | 组织模型请求、工具执行、上下文、状态和运行控制的系统 |
| AgentSessionRuntime | 当前产品的 session 与 cwd 相关服务管理层，负责切换、清理和重建 |
| AgentSession | Coding Agent 的 prompt、extension、重试、压缩和收尾编排 |
| Agent | 低层 loop 的状态包装，拥有消息、队列、tools/model 和取消信号 |
| turn | 低层循环中的一轮 assistant 响应及工具处理；用户请求可包含多个 turn |
| agent_end | 一次低层运行的结束事件，产品层还可能继续处理 |
| agent_settled | 当前 Coding Agent 完成该次运行收尾；任务成功需要另行判定 |
| registry | 已注册的工具定义，可能包含默认未启用的工具 |
| active tools | 当前 Agent 中启用并用于模型请求的工具集合 |
| toolCall / toolUse | toolCall 是消息内容块，toolUse 是可能的 assistant stop reason |
| toolResult | 与工具调用关联的结果消息，可携带错误并进入下一请求 |
| steering | 由提交方式或 API 显式选择，在当前 turn 边界后注入；默认运行中 Enter 选择此队列 |
| follow-up | 由提交方式或 API 显式选择，在工具与 steering 耗尽时消费；默认运行中 Alt+Enter 选择此队列 |
| nextTurn | 产品层留给下一次普通 prompt 附带的消息 |
| context | 当前请求使用的 system、messages、tools；不等于整个 session 文件 |
| 持久历史 | 已保存的会话记录，可以包含多个分支、摘要、配置与扩展数据 |
| 当前分支 | 从当前 leaf 沿 parentId 选出的历史路径 |
| 请求视图 | 本轮实际使用的信息，经分支选择、压缩边界和消息转换后与 system/tools 组装 |
| AgentMessage | Pi 应用层消息；除普通模型消息外，还可包含 custom、bashExecution 和摘要类型 |
| CustomEntry / CustomMessageEntry | 前者保存默认不入模型的扩展状态；后者会重建为 custom 应用消息并参与消息转换 |
| bashExecution | 用户通过 ! 执行命令的内部记录；不同于模型调用 bash 后得到的 toolResult |
| convertToLlm | 普通 TypeScript 转换函数：将应用消息映射为 pi-ai Message[]，再由 provider 适配器构造实际 API 请求 |
| chat template / 对话编码器 | 将结构化消息和工具定义组织为模型对应的输入格式；此处讨论服务端职责，具体实现因模型而异 |
| tokenizer | 将文本和控制标记转换为 token IDs；与 Pi 的应用消息类型转换是不同阶段 |
| tool-call parser | 将模型生成的调用格式解析为 API 工具调用字段，之后由 Harness 执行工具 |
| ModelRegistry | 当前产品的模型配置与请求鉴权注册表 |
| compat | pi-ai 兼容入口，按条件连接内置 Models 或 API registry |
| Models | pi-ai 的 provider/model 集合接口，当前 compat 的内置模型分支会使用它 |
| leaf / parentId | 会话树的当前位置与父记录引用，决定当前分支 |
| compaction boundary | 带摘要和 firstKeptEntryId 的历史选择边界 |
| project trust | 项目启动资源加载的信任决策，职责不同于执行 sandbox |
| R / X evidence | R 表示真实模型运行；X 表示控制实验或定向测试 |

具体条件和调用顺序在对应章节展开，查证入口见[源码与结论索引](14-source-claim-index.md)。
