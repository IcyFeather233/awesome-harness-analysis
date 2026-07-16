# 核心循环与编排

![Observed Codex turn](../diagrams/generated/codex-observed-turn.png)

> 图 2（gpt-image-2 读者插图）：严格对应 `X-SCENARIO-002` 的两次 Responses 请求；permission、compaction、subagent 等未发生路径没有混入主轴。Evidence: `S-002`, `S-003`, `S-010`, `S-025`, `X-002`。

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

## 两层循环

外层 `RegularTask` 管一个用户 turn：发开始事件、调用 `run_turn`、处理排队输入。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tasks/regular.rs#L37) 内层 `run_turn` 才是 agent loop：检查 compaction、刷新 world state/skills/hooks、构造 prompt、采样、dispatch tools、判断 follow-up，最后执行 stop hooks 和结束事件。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/session/turn.rs#L224) [S: `S-002`, `S-003`]

`OutputItemDone` 遇到 function/custom tool 时不会同步阻塞整个 stream parser，而是创建 tool future；Response completed 后再综合 `needs_follow_up`、pending input 与 compaction 条件。只读/parallel-capable handler 可共享读锁，exclusive handler 获取写锁。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/tools/parallel.rs#L42) [S: `S-025`]

## 被实验验证的闭环

`X-SCENARIO-002` 的 provider 日志显示第一次 input types 是三条 `message`；第二次变成 `message ×3 + function_call + function_call_output`。fixture 只有看到 `call-read` output 才返回最终值，因此“tool result 确实进入下一轮模型上下文”不是根据最终文本猜测。[X: `X-002`]

`X-SCENARIO-003` 又验证错误分支：未知工具在 router/registry 处产生 unsupported error，但该错误作为 tool output 回到模型，turn 仍可结束。[X: `X-003`]

## 停止与恢复

正常停止条件是 response complete 且没有 tool follow-up/pending input；取消由 token 传播到 tool runtime，provider stream retry 有界。开始新 task 会 abort 旧 task；turn 完成前尝试 flush rollout。[S: `S-008`, `S-022`]

未覆盖：并行多 tool 的真实 interleaving、user interrupt、stream idle、stop hook 阻断和中途 compaction。因此图 2 只表达已经发生的 read-only 主线。
