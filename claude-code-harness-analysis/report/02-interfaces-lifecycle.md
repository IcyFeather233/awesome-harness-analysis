# 接口与生命周期

> **证据边界。** 本报告分析 source-only commit `16a676f`。其 1,884 个 TS/TSX 文件、关键 symbol 与 feature gates 和论文所述 Claude Code v2.1.88 corpus 强指纹一致，但缺少 package version、上游 tree hash、build manifest，不能视为已证明的 exact 官方 artifact。快照仍有 657 个无法解析的相对 import；除 SiFlow 协议探针外，主循环、安全、session 与 subagent 结论均为 static-only。官方材料只支持产品立场，五价值/十三原则是 analyst synthesis。[X: X-001–X-003] [D: D-001–D-008] [C: C-001, C-024–C-026] 首次遇到缩写或内部名词时，可查 [全局术语表](16-glossary.md)。


[CLI bootstrap](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/entrypoints/cli.tsx#L33) 先处理 --version 和 feature-gated fast path，其余才加载 [Commander main](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/main.tsx#L585)。main 再区分 interactive、--print/SDK、server、remote/bridge、MCP 与条件子命令。[S: S-002–S-003]

## 先理解 surface、adapter 和 core

- **Bootstrap** 是进程刚启动时的最小分发层：解析少量参数，处理无需完整应用初始化的 fast path，再决定是否加载 main。它不等于 agent loop。
- **Surface** 是输入/输出产品界面。REPL（Read-Eval-Print Loop）面向人在终端中连续交互；`--print`/SDK（Software Development Kit）面向脚本和调用方；server/bridge/MCP 子命令面向其他协议。
- **Adapter** 把某个 surface 的状态转换成 core 能理解的 messages、tools、permission callback 和 event consumer。共享 core 不要求 UI、输出格式或 approval 交互相同。
- **AppState** 是交互进程中的 live mutable state，包括当前 messages、tool permission context、tasks、agents 等；它不是 durable transcript 本身。
- **QueryGuard** 是 REPL 的并发入口保护，确保一个主 query 获得执行权，后来的输入排队或作为附件处理。
- **QueryEngine** 是 headless/SDK 侧的 controller。`headless` 表示没有交互式终端 UI；`structured I/O` 表示用机器可解析的记录而不是屏幕文本交换事件。QueryEngine 负责这种 I/O、非交互 permission 语义和调用共享 `query()`。

| 表面 | 主要对象 | 进入 core 前准备什么 | 读者注意 |
|---|---|---|---|
| Interactive REPL | React/Ink UI、AppState、QueryGuard | 维护终端渲染、输入队列、ESC/abort、approval dialog 和 live task/agent state，然后由 `onQueryImpl` 调用共享 `query()`。 | 共享的是 model/tool 状态机，不是 UI 行为；REPL 能做人类交互，headless 入口不一定能。 |
| Print / SDK | QueryEngine、structured I/O event consumer | 把机器输入转成 messages/attachments，以 JSON/event records 输出进度，并为非交互场景提供 permission 决策路径。 | 它消费同一 `query()`，但 approval、错误呈现和 backpressure 与 REPL 不同。 |
| MCP/server/bridge | 协议 runner、子命令 handler | 先处理协议握手、server lifecycle 或 bridge/remote 子命令；只有进入 agent execution 的分支才会触达主 loop。 | 不能把“同一 binary 里有 server/MCP 代码”直接解释成所有协议请求都走 canonical query path。 |
| Resume/fork | sessionRestore、sessionStorage、metadata loader | 先从 JSONL、parentUuid 和 metadata 重建 live session view，再按当前 settings/CLI 重新建立运行上下文。 | 恢复会话不等于回滚 workspace，也不从旧 transcript 恢复临时 permission grants。 |

## Session、query、iteration 与 API request

- **Session**：跨多个用户提交的容器，有 session ID、live state，并可对应 transcript JSONL。[S: S-029–S-031]
- **一次用户 query**：提交输入到这次 query() terminal transition。QueryGuard 防止两个主 query 同时运行，新消息可排队。[S: S-004]
- **Agentic loop iteration**：queryLoop 的一次 while(true)，通常取样一次、可能执行一组工具，再决定继续或 terminal。[S: S-006–S-008]
- **API request / model round**：对 Anthropic Messages 的一次请求。一个用户 query 可因工具回填、retry、fallback 或 recovery 含多个 request。[S: S-007, S-017–S-018]

所以“一个 turn 调几次模型”必须先定义 turn。本报告固定使用上述四个词。

一个具体包含关系可以写成：`一个 Session` 包含多次 `用户 query`；一次 query 包含一到多次 `loop iteration`；一次 iteration 通常包含一次 `model API request`，还可能执行零到多个 tool calls。provider retry 可能让一次 iteration 内出现额外 request，因此这不是严格的一对一数学关系。

## 从进程启动到一次提交结束

1. **Bootstrap** 选择入口，只加载当前 mode 需要的模块。
2. **Main initialization** 读取 settings、permission mode、provider、plugins/MCP、session metadata，并建立 surface state。
3. **Surface intake** 把用户文本或 structured input 转成 messages/attachments；REPL 还处理队列、ESC 和渲染。
4. **Query execution** 进入共享 `query()`，在 model request 与 tool execution 之间循环。
5. **Persistence** 把 message/tool chain 追加到 transcript；这一步使部分 live state 变成 durable state。
6. **Terminal/next input** 当前 query 返回，但 session 可以继续接收下一次提交；收到 signal 时则转入 graceful shutdown。

--print 会跳过 workspace trust dialog，且 non-interactive 场景无法使用普通 UI approval；共用 loop 不表示治理体验完全相同。[S: S-003, S-024]
