# 接口与生命周期

> **证据边界。** 本报告分析 source-only commit `16a676f`。其 1,884 个 TS/TSX 文件、关键 symbol 与 feature gates 和论文所述 Claude Code v2.1.88 corpus 强指纹一致，但缺少 package version、上游 tree hash、build manifest，不能视为已证明的 exact 官方 artifact。快照仍有 657 个无法解析的相对 import；除 SiFlow 协议探针外，主循环、安全、session 与 subagent 结论均为 static-only。官方材料只支持产品立场，五价值/十三原则是 analyst synthesis。[X: X-001–X-003] [D: D-001–D-008] [C: C-001, C-024–C-026]


[CLI bootstrap](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/entrypoints/cli.tsx#L33) 先处理 --version 和 feature-gated fast path，其余才加载 [Commander main](https://github.com/IcyFeather233/claude-code/blob/16a676ffa36eadbfb28eec39007dff73941346b1/src/main.tsx#L585)。main 再区分 interactive、--print/SDK、server、remote/bridge、MCP 与条件子命令。[S: S-002–S-003]

| 表面 | 主要对象 | 与 core 的关系 |
|---|---|---|
| Interactive REPL | React/Ink + AppState + QueryGuard | onQueryImpl 消费共享 query() |
| Print / SDK | QueryEngine + structured I/O | QueryEngine 消费共享 query() |
| MCP/server/bridge | 协议 runner | 是否进入主 loop 取决于子命令 |
| Resume/fork | sessionRestore + sessionStorage | 重建 live session 后进入相同 core |

## Session、query、iteration 与 API request

- **Session**：跨多个用户提交的容器，有 session ID、live state，并可对应 transcript JSONL。[S: S-029–S-031]
- **一次用户 query**：提交输入到这次 query() terminal transition。QueryGuard 防止两个主 query 同时运行，新消息可排队。[S: S-004]
- **Agentic loop iteration**：queryLoop 的一次 while(true)，通常取样一次、可能执行一组工具，再决定继续或 terminal。[S: S-006–S-008]
- **API request / model round**：对 Anthropic Messages 的一次请求。一个用户 query 可因工具回填、retry、fallback 或 recovery 含多个 request。[S: S-007, S-017–S-018]

所以“一个 turn 调几次模型”必须先定义 turn。本报告固定使用上述四个词。

生命周期是：bootstrap 选入口 → main 建配置/permission/provider/extensions/session → surface 接收输入并组 context → query loop → transcript 追加 → terminal 返回；signal 则进入 graceful shutdown。

--print 会跳过 workspace trust dialog，且 non-interactive 场景无法使用普通 UI approval；共用 loop 不表示治理体验完全相同。[S: S-003, S-024]
