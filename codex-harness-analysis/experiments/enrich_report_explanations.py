#!/usr/bin/env python3
"""Add reader-oriented terminology and figure walkthroughs to every report chapter."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "report"


def insert_before(filename: str, anchor: str, marker: str, block: str) -> None:
    path = REPORT / filename
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    if anchor not in text:
        raise ValueError(f"anchor not found in {filename}: {anchor}")
    text = text.replace(anchor, block.strip() + "\n\n" + anchor, 1)
    path.write_text(text, encoding="utf-8")


def enrich_reports() -> None:
    insert_before(
        "index.md",
        "## 一句话结论",
        "<!-- EXPLANATION:report-glossary -->",
        """
<!-- EXPLANATION:report-glossary -->
## 先读懂图 1：这些方框不是源码目录

图 1 把多个 Rust 类型聚合成读者可理解的运行职责。例如 `Thread / Session` 同时概括 thread manager、session 和 active persistence handle；`Tool runtime` 概括 tool spec、router 与 handler execution。它不是“一个方框对应一个文件”的包依赖图。

从左到右的实线是一次使用 `exec_command` 时的主路径：入口创建或恢复 thread，turn loop 组装请求，Responses API 返回模型输出，tool runtime 解释工具调用，`Exec Policy + Sandbox` 决定并约束副作用，最后才触达 workspace。下方红色回路表示 tool output 先进入 context，再触发下一次 model request；它不是 tool 直接调用模型。

图中常用词可以先这样理解：

| 术语 | 本报告中的准确含义 |
|---|---|
| thread | 可持久化、可 resume/fork 的会话身份和历史容器 |
| session | 当前进程中负责处理该 thread 的运行对象 |
| turn | 一次用户请求到 `TurnComplete/TurnAborted` 的调度单位；内部可有多次模型请求 |
| `StepContext` | 某次 sampling/tool invocation 固定使用的 model、cwd、policy、tools 等请求级快照 |
| context | 模型可见 history、动态 world state、当前输入和 tool specs 的组合 |
| rollout | 按顺序记录 session items 的 durable JSONL 事件历史 |
| registry | 当前进程已经有实现的工具集合 |
| exposure | 本次 model request 实际向模型公开的工具子集 |
| mailbox | V2 agent 之间暂存 completion/message 的 session-scoped 通信队列 |
| OTel | OpenTelemetry；独立于产品事件的 logs/traces/metrics 输出层 |

图片只承担“快速建立心智模型”；条件、例外和精确定义以相应章节、[HIR](../hir.json)和 evidence 为准。
""",
    )

    insert_before(
        "00-design-space-and-running-example.md",
        "## 六个反复出现的设计问题",
        "<!-- EXPLANATION:design-space-figure -->",
        """
<!-- EXPLANATION:design-space-figure -->
## 怎么读图 8

每一行都从左向右读：`Constraint` 是 harness 必须面对的问题，`Recovered mechanism` 是在 v0.144.5 源码中找到的当前实现，`Analyst synthesis` 是由实现推导出的工程代价。最后一列带 `INFERENCE`，是为了明确它不是 OpenAI 作者声明。

例如第一行不是说“rollout 一定会损坏”，而是说：既然跨进程 resume 依赖 `LiveThread + Rollout`，那么 flush 失败、尾部截断和 corruption 就成为必须测试的边界。第四行同理：`Exec Policy + Sandbox` 提供分层治理，但跨平台实现不同，所以不能用一次 Linux deny 实验推出所有平台都等价。[S: `S-012`–`S-014`, `S-018`, `S-019`] [X: `X-004`, `X-006`]
""",
    )

    insert_before(
        "01-scope-and-method.md",
        "## 主要限制",
        "<!-- EXPLANATION:method-terms -->",
        """
<!-- EXPLANATION:method-terms -->
## 如何理解“验证过”

本文把“源码中存在”“本轮真的发生过”和“推断的设计代价”分开。`S` 证据能证明一条路径在固定 commit 中可见；`R/X` 能证明它至少在某个命名配置下发生；二者都不能证明生产使用频率。`partial` 也不是“模块只读了一半”，而是指静态机制已经恢复，但关键平台、feature flag 或失败路径没有动态覆盖。

因此，图上的 `OBSERVED` 只对应具体 scenario；`CONDITIONAL`、`EXPERIMENTAL`、`V1/V2` 或 `NOT TESTED` 都必须结合 manifest 中的 feature/configuration 阅读。
""",
    )

    insert_before(
        "02-interfaces-lifecycle.md",
        "动态验证覆盖了",
        "<!-- EXPLANATION:lifecycle-terms -->",
        """
<!-- EXPLANATION:lifecycle-terms -->
## Thread、Session、Turn 的包含关系

先把它们看成三种不同时间尺度的对象：**thread 是可持久化的对话身份，session 是当前进程中运行该 thread 的实例，turn 是 session 正在处理的一次任务边界**。用运行时所有权表示是：

```text
Codex process
└─ ThreadManager                         0..N 个已加载 thread
   └─ thread_id = T                    可持久化的逻辑身份
      └─ CodexThread handle
         └─ Session S                  当前进程的 live runtime
            └─ active_turn = None | U  同一时刻最多 1 个
               └─ Turn U
                  ├─ model request 1
                  ├─ tool call / tool result
                  └─ model request 2 ... N
```

这是运行时关系，不是持久化文件的目录结构。`ThreadManager` 在内存中维护 `ThreadId -> Arc<CodexThread>` 映射；`CodexThread` 是向 interface 提供 submit/event/shutdown 的 handle，内部包装真正的 `Session`。对同一个 manager，如果某个 thread 已经在运行，resume 会返回现有 handle，而不是再建一个并发 session。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/thread_manager.rs#L182) [源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/thread_manager.rs#L1526)

### 1. Thread：“这是哪段对话”

Thread 是跨 turn、也可以跨进程的逻辑身份。它的核心是 `thread_id`、会话历史和 metadata，而不是某个常驻 Rust 对象。

- `start` 产生新 `thread_id` 和新历史。
- `resume` 使用原 `thread_id` 加载原历史；新进程会为它创建新的 live session。
- `fork` 复制选定的历史快照，但分配**新** `thread_id`，因此不是在原 thread 内新建一个 turn。
- local store 通常用 rollout JSONL 保存 canonical history，用 SQLite 保存可查询 metadata；`LiveThread` 隔离了 core 与具体存储后端。

Thread 记录“Codex 看过和产生过什么”，但它不拥有 workspace 的版本。恢复 thread 会恢复对话 history，不会自动把文件系统回滚到旧状态。[D: `D-004`] [S: `S-018`] [X: `X-006`]

### 2. Session：“谁正在运行这段对话”

Session 是一个 live、in-process 的运行对象。它带着同一个 `thread_id`，但还拥有只在当前运行期有意义的状态：event channel、model/provider 配置、permission profile、MCP/services、input queue、内存 conversation state，以及指向持久化后端的 `LiveThread` handle。

`Session` 源码明确声明“at most 1 running task at a time”，并以 `active_turn: Mutex<Option<ActiveTurn>>` 表示这个约束。它在生命周期中可以顺序处理多个 turn；开始替代任务时，旧任务会通过 cancellation 边界中止。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/session/session.rs#L25) [源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tasks/mod.rs#L325)

因此，一个 thread 在时间上可以对应多个先后出现的 session：进程 A 中的 `S1` 退出后，进程 B resume 同一 thread 会创建 `S2`。`S1` 与 `S2` 的内存地址、channel 和 service 对象不同，但它们共享同一个 `thread_id` 和已持久化历史。

### 3. Turn：“这一次任务什么时候结束”

Turn 是 `TurnStarted` 到 `TurnComplete` 或 `TurnAborted` 之间的调度单位。它有自己的 `turn_id`/`TurnContext` 和 mutable `TurnState`：本轮使用的 model、cwd/environment、approval/permission profile、dynamic tools、取消 token、token usage，以及正在等待的 approval、user input 或 dynamic-tool response。

**Turn 不等于一次模型 API 请求。** 一个 turn 可以是：

```text
TurnStarted(U1)
  -> model request #1
  -> model proposes exec_command
  -> permission + sandbox + tool execution
  -> tool result appended to history
  -> model request #2
  -> final assistant message
  -> flush rollout
TurnComplete(U1)
```

两次 model request、tool call 和 tool result 都属于同一个 `U1`。只有下一次发出新的 `TurnStarted(U2)` 才是新 turn。`TurnComplete/TurnAborted` 后，`active_turn` 被清空并再次 flush terminal event，session 回到 idle，thread 不因此消失。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tasks/mod.rs#L756) [S: `S-002`]

### 4. 一个跨进程的具体例子

| 时间 | 发生的事 | 仍然相同 | 已经变化 |
|---|---|---|---|
| 进程 A 启动 | start thread `T`，建立 session `S1` | `thread_id=T` | 新 session |
| 用户提问 | `S1` 开始 turn `U1`，内含两次 model request 和一次 tool call | `T`, `S1`, `U1` | model request/step 变化 |
| `U1` 完成 | terminal event 和 history flush，`S1` 继续 idle | `T`, `S1` | `active_turn: U1 -> None` |
| 进程 A 退出 | `S1` 消失，rollout 保留 | `T` 和 durable history | live session 消失 |
| 进程 B resume | 加载 `T` 并建立 `S2` | 同一 `thread_id=T` 和旧 history | `S2` 是新 live object |
| 用户再提问 | `S2` 开始新 turn `U2` | `T` | session 和 turn 都与首轮不同 |

本轮的跨进程实验已观察到：第二个进程 resume 后 `thread_id` 不变，provider input 包含首轮 assistant history。这直接验证了“thread 跨进程，session 不跨进程”的主路径。[X: `X-006`]

### 5. 失败会影响到哪一层

| 事件 | 通常结束或改变的边界 | 不能自动推出的结论 |
|---|---|---|
| 单次 provider stream 错误 | 当前 sampling/request，可能在 turn 内有界 retry | 不等于 thread 已删除 |
| tool error | 错误可以作为 tool output 回到当前 turn | 不一定结束 session |
| `TurnAborted` | 当前 turn | session 仍可接受新 turn |
| interface/websocket 断开 | 客户端连接 | 不等于 durable thread 被删除 |
| session/process shutdown | live runtime | flush 成功时 thread 仍可 resume |
| thread archive/delete | durable identity/history 的可见性或存在性 | 不会自动回滚 workspace |

所以最简短的记忆方式是：**Thread 回答“哪段对话”，Session 回答“哪个 live runtime 正在处理它”，Turn 回答“当前这次任务的边界在哪里”。** Interface 只决定这些操作通过 TUI、`exec`、app-server 还是 MCP server 进入 core。[D: `D-003`, `D-004`] [S: `S-002`, `S-018`]

""",
    )

    insert_before(
        "03-core-loop.md",
        "## 两层循环",
        "<!-- EXPLANATION:turn-figure -->",
        """
<!-- EXPLANATION:turn-figure -->
## 图 2 的逐步阅读

1. `User request` 进入外层 `RegularTask`。外侧长括号表示这个 task 管理完整 turn。
2. 内层 `run_turn` 建立 `Request 1`，`Build prompt` 把 history、当前输入和可见工具规格组装成 Responses 请求。
3. 第一次 `Responses` 没有给最终答案，而是返回 `exec_command` function call。
4. harness 读取 `FACTS.txt`，把结果包装成 `function_call_output`。黑色回箭头表示它进入 history，不是直接显示给用户。
5. `Request 2` 使用 `Updated history` 再调用一次 Responses；此时请求里同时存在原 function call 和对应 output。
6. fixture 只有确认 output 存在后才返回 `HXA-1445`，所以第二次请求不是图示假设，而是实验门槛。
7. 没有新的 tool call、pending input 或 follow-up 后，turn 才进入 `Turn complete`。[X: `X-002`]

图里重复出现的 `Responses` 表示同一 model boundary 的两次调用，不是两个模型实例；`RegularTask` 与 `run_turn` 也不是并列的两个 agent loop，而是 turn 调度层与内部 sampling/tool loop。
""",
    )

    insert_before(
        "04-context-memory-compaction.md",
        "## History 与 world state",
        "<!-- EXPLANATION:context-figure -->",
        """
<!-- EXPLANATION:context-figure -->
## 图 3 的节点和回路

| 图中节点 | 具体表示什么 |
|---|---|
| Base instructions | config override、persisted conversation metadata 或 model default 选出的基础指令 |
| History | 已规范化的模型可见 message/tool items；图中左右两个 History 图标是同一份 history 的两个视图 |
| World state diff | AGENTS、环境、subagents、apps/plugins 等相对 baseline 的 typed snapshot/diff |
| Visible tool specs | registry 中经过当前 provider、feature 和 exposure 规则筛出的本轮工具 schema |
| Context Manager | 负责 history 顺序、token 估计和 world-state baseline 的内存状态管理器 |
| `StepContext + Prompt` | 把本次请求固定的 cwd/model/policy/tools 与输入组合成 sampling 所需对象 |
| Tool runtime/output | 模型提出调用后，由 harness 执行并产生可追加到 history 的结果 |

右侧闭环要读成 `Responses API → Tool runtime → Tool output → History → Context Manager → next request`。下方 compaction 是另一条条件回路：达到 token/window 阈值后生成 replacement，再用 replacement 改写模型可见 history。`History replacement` 不是回滚 workspace，也不是删除 durable rollout；它改变的是后续模型请求的有效上下文。[S: `S-005`–`S-007`] [X: `X-002`]

`Long-term memory` 带 `EXPERIMENTAL`，表示它属于默认关闭的 memories feature；`WHEN NEEDED` 表示 compaction 是阈值触发，不是每轮固定执行。
""",
    )

    insert_before(
        "05-models-tools-extensions.md",
        "## Model boundary",
        "<!-- EXPLANATION:tool-figure -->",
        """
<!-- EXPLANATION:tool-figure -->
## 图 4 的七段能力管线

这张图最容易误读成“工具注册后马上执行”。实际上必须按编号从左向右读：

1. **Capability sources**：`Built-ins` 是 Codex 自带工具；`MCP + Extensions` 是外部/插件贡献；`Dynamic + Multi-agent` 是 host 在运行时提供的函数和 feature-gated collaboration 工具。
2. **Tool registry**：保存 tool name 到 handler implementation 的映射。进入 registry 只说明 Codex 知道如何处理它，不代表模型现在看得见。
3. **Per-turn exposure**：`VISIBLE NOW` 是本次 request 的公开子集。provider capability、feature flag、agent depth 和 deferred/hidden 规则都会改变它。例如 root 有 `spawn_agent`，达到深度上限的 child 可以没有。
4. **Responses API**：模型收到 prompt 和暴露后的 tool schemas。图上自动生成的 `tool call only` 只是强调这条箭头承载 model-proposed tool call，不是说 Responses 只能返回工具调用；它也可以返回普通 assistant text。
5. **Router + Hooks**：router 解析 function/custom/namespace call，绑定准确的 `StepContext`；pre-tool hooks 可在 handler 前阻断或改写输入。
6. **Handler runtime**：真正执行 handler。`parallel read` 表示允许并行的工具共享读锁；`exclusive write` 表示有副作用或需独占的工具获取写锁。这个分类由 handler capability 决定，并非按工具名称猜测。
7. **Result to Context**：成功值或 model-facing error 被包装成 tool output，追加到 history；`next request` 才让模型看到它。

以报告的 read scenario 为例：`exec_command` 已在 registry，read-only 配置下也处于 exposure；模型提出 call 后 router 找到 handler，runtime 读取文件，结果回到 context，再发第二次 Responses 请求。`X-SCENARIO-003` 的未知工具则在 router/registry 查找阶段失败，但错误仍沿第 7 段返回模型。[S: `S-009`–`S-011`, `S-025`, `S-026`] [X: `X-002`, `X-003`, `X-005`]
""",
    )

    insert_before(
        "06-permissions-sandbox-workspace.md",
        "## 决策层",
        "<!-- EXPLANATION:permission-figure -->",
        """
<!-- EXPLANATION:permission-figure -->
## 图 5 的三条分支

`Exec Policy` 不是 sandbox，它先回答“是否允许进入执行阶段”：

- `allow`：规则和 mode 已足以授权，不弹用户确认，直接进入 `Platform Sandbox`。
- `ask`：需要 `User Approval`；`Session cache` 只可能复用同一 session 中明确批准的 decision，然后同样进入 sandbox。
- `NEVER + escalation`：当前 policy 明确不允许询问提权，直接产生 `Tool error to model`；图中的 `OBSERVED` 只标记这条本轮实验路径。

两个 allow/ask 分支汇合后，`Filesystem profile` 和 `Network profile` 决定 sandbox 给 process 的实际能力，`Process` 才可能读取/写入 `Workspace`。所以“允许命令”不等于“无限制执行”，“用户批准”也不等于“关闭 sandbox”。[S: `S-012`–`S-014`] [X: `X-004`, `X-007`]
""",
    )

    insert_before(
        "07-subagents-delegation.md",
        "## 静态拓扑",
        "<!-- EXPLANATION:subagent-figure -->",
        """
<!-- EXPLANATION:subagent-figure -->
## 图 6 中每个标签是什么意思

`AgentControl` 是一个 root agent tree 共享的控制面，负责 agent registry、并发/深度限制、消息发送、interrupt 和 child 生命周期。`Root Session` 与 `Child Session` 是两个独立 Codex session；`spawn_agent` 创建 child 后，child 拥有自己的 thread id、model-visible context 和 history，因此 child 的中间推理不会自动塞进 root history。[S: `S-015`, `S-016`]

图上方的 `model + policy + cwd` 表示 child 从父 turn 的 effective configuration 继承 model provider、approval policy、sandbox policy 和工作目录；这不是共享 context。下方两条 `shared files` 线表示 root/child 看见同一个 workspace，所以 context 隔离并不能避免文件竞争。`max depth 1` 是本版本默认配置：达到深度上限的 child 不再暴露 spawn namespace，并不表示 child 不能使用普通工具。[S: `S-015`–`S-017`] [X: `X-005`]

### `V2 mailbox` 的准确含义

它不是电子邮件服务，也不是一个额外 agent。它是 MultiAgent V2 的 **session-scoped inter-agent message queue**：child completion 或 agent-to-agent communication 先进入 parent 的 pending mailbox，再由 parent turn 决定何时吸收。

- turn 开始时处于 `CurrentTurn`，pending mail 可以加入当前 turn 的下一次 model request。
- parent 已输出用户可见 final 后，晚到 mail 通常留在队列，推迟到 `NextTurn`，避免悄悄延长已经显示完成的答案。
- 如果 parent 仍在 reasoning/commentary 阶段发现 pending mail，sampling 可以提前结束并进入 follow-up，使新消息更快进入 context。
- V2 child 的 terminal event 会被包装成 completion message 转发给直接 parent。

图上的虚线和 `NOT TESTED` 表示这套逻辑只由固定 commit 的源码确认，本轮没有启用 V2 动态验证；本轮真正观察到的是 V1 `spawn_agent` 路径。[S: `S-027`] [X: `X-005`]
""",
    )

    insert_before(
        "08-sessions-persistence-recovery.md",
        "## Live 与 durable state",
        "<!-- EXPLANATION:persistence-figure -->",
        """
<!-- EXPLANATION:persistence-figure -->
## 图 7 的持久化链条

| 阶段 | 作用 |
|---|---|
| Turn items | user/assistant/tool/compaction 等已经规范化、准备持久化的事件 |
| `LiveThread` | 当前活跃 session 使用的高层持久化 handle；过滤 rollout items，并同步派生 metadata |
| `ThreadStore` | storage-neutral 接口；core 不需要知道后端是本地文件、内存还是仓库外实现 |
| Rollout JSONL | local store 的 canonical append history；用于重建 conversation history |
| New process | 原进程结束后启动的另一个 Codex CLI/app-server process |
| Resume same thread | 用同一 thread id 调用 store 的 resume/load history |
| Restored history | 重新进入 `ContextManager`、供后续 model request 使用的有效会话历史 |

`Turn complete → Rollout JSONL` 旁的小箭头表示完成 turn 前会尝试 flush，不表示只有 turn 完成时才 append。`OBSERVED` 覆盖的是正常 create、flush、换进程、resume 路径。[S: `S-018`, `S-019`, `S-022`] [X: `X-006`]

图下方的 `Workspace — not rolled back` 是另一条状态轨道：rollout 记录对话和 tool items，但 resume 不会把文件恢复到旧版本。上方 `Compaction summary — CONDITIONAL` 表示恢复的 history 可能包含压缩后的模型可见表示；它不是另一个 thread store。`Corruption / partial write — NOT TESTED` 是明确的未知项，本轮没有故意截断 JSONL，也没有证明损坏文件能自动修复。
""",
    )

    insert_before(
        "09-observability.md",
        "任务层创建 turn span",
        "<!-- EXPLANATION:observability-terms -->",
        """
<!-- EXPLANATION:observability-terms -->
## 三类可观测数据

- **Product events**：`thread.started`、`turn.started`、item/tool/turn completion 等，供 TUI、`exec --json` 和 app-server 客户端驱动 UI 或业务状态。
- **OTel span/log/metric**：供 collector 和 tracing backend 做跨组件关联；span 表示有父子关系的耗时操作，metric 表示可聚合计数/时延，log 记录离散事件。
- **Rollout items**：durable session history，主要用于 resume/replay；它不是为低开销监控设计的 telemetry stream。

三者可能共享 conversation/turn/call id，但目的和保留策略不同。报告中的 provider-side sanitized request log 是本次分析额外加的观察点，不是 Codex 默认对外 API。

""",
    )

    insert_before(
        "10-design-decisions.md",
        "| 决策 | 当前机制",
        "<!-- EXPLANATION:decision-table -->",
        """
<!-- EXPLANATION:decision-table -->
## 怎么读这张表

`当前机制` 只陈述源码实际做法；`Documented intent` 只有仓库文档能直接支持时才填写；`代价/替代方案` 是分析者综合。`置信度=中` 往往不是因为没找到代码，而是因为作者动机未记录、关键 feature 未运行，或结论跨越了多个平台/configuration。

例如“child 独立 context、共享 workspace”的结构证据很明确，但“为什么选择这种隔离粒度”没有作者声明，所以 tradeoff 只能写成可观察后果，不能写成设计团队的真实动机。

""",
    )

    insert_before(
        "11-runtime-experiments.md",
        "## 为什么真实模型没有伪装成成功",
        "<!-- EXPLANATION:experiment-modes -->",
        """
<!-- EXPLANATION:experiment-modes -->
## 表中模式与结果怎么解释

`R-*` 是官方 Codex binary 连接真实 SiFlow endpoint 的兼容性观察；失败仍是有效结果，因为它说明 stock request 在模型输出前被哪一层拒绝。`X-*` 是 deterministic Responses fixture：fixture 不理解任务，只按预先写好的 call id/item type 强制 Codex 走指定分支，因此适合验证 harness control flow。

`passed` 表示预先声明的区分性断言成立，不表示整个功能面都正确。例如 X-004 证明 `never` 在该 escalation 请求上先于 process 拒绝，并用文件哈希检查了无副作用；它没有证明所有 shell/MCP/dynamic tool 都经过同一 gate。详细配置和 trace 路径在 [scenario catalog](../scenarios/catalog.json)。
""",
    )

    insert_before(
        "12-failure-modes-open-questions.md",
        "## 高价值未知项",
        "<!-- EXPLANATION:failure-terms -->",
        """
<!-- EXPLANATION:failure-terms -->
## 这里的“失败”分三类

- **Provider dialect failure**：HTTP endpoint 存在，但不接受 Codex 使用的 message role 或 tool schema；这不是 agent loop 自身失败。
- **Handled tool failure**：unknown tool 或 policy deny 被包装为 model-facing output，当前 turn 仍可能恢复并完成。
- **Durability/recovery failure**：timeout、process crash、partial rollout、corruption 或 workspace drift，可能影响跨 turn/process 恢复；本轮大多尚未故障注入。

因此下面的开放问题既包括产品风险，也包括分析覆盖缺口。`V2 mailbox preemption` 指 parent 在 reasoning/commentary 期间收到 child mail 时提前结束当前 sampling、转入吸收消息的 follow-up；它不等于强制终止整个 parent session。[S: `S-027`]
""",
    )

    insert_before(
        "13-coverage-reproducibility.md",
        "## 关键复现条件",
        "<!-- EXPLANATION:artifact-map -->",
        """
<!-- EXPLANATION:artifact-map -->
## 不同产物分别用来回答什么

- 想快速理解系统：从 [report/index.md](index.md) 和八张读者图开始。
- 想确认一句结论：在 [claims.jsonl](../evidence/claims.jsonl) 找 claim id，再跳到对应 D/S/R/X/I evidence。
- 想程序化比较另一个版本：使用 [hir.json](../hir.json) 的 typed nodes/edges 和 conditions。
- 想复现实验：使用 [scenario catalog](../scenarios/catalog.json)、`experiments/` 和 sanitized traces。
- 想判断“没有观察到”究竟意味着什么：查看 [coverage.json](../evidence/coverage.json) 的 configurations、excluded surfaces 和 unresolved。

当前 bundle 包含 29 个 HIR nodes、38 条 edges、23 个 claims 和 46 条 evidence records。图片不新增任何 claim；它们只是这些结构化事实的读者投影。
""",
    )

    coverage_path = REPORT / "13-coverage-reproducibility.md"
    coverage_text = coverage_path.read_text(encoding="utf-8")
    coverage_text = coverage_text.replace("29 nodes / 37 edges", "29 nodes / 38 edges")
    coverage_path.write_text(coverage_text, encoding="utf-8")


if __name__ == "__main__":
    enrich_reports()
