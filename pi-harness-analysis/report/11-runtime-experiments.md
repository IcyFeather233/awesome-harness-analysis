# 11 运行实验

完整命令和结果见 [runtime-tests.md](../runtime-tests.md)，场景机器可读记录见 [catalog.json](../scenarios/catalog.json)。

## R-SCENARIO-001：最短文本路径

- 配置：JSON mode、no session、no tools、禁 extensions/skills/templates/context files。
- 预期：一次 turn，无 tool event，最终 settled。
- 结果：通过，最终 `PI_TEXT_OK`；1 turn、0 tool。
- 证据：`R-001`；normalized trace `traces/normalized/R-001-text-only.normalized.jsonl`。

## R-SCENARIO-002：真实 read tool loop

- Fixture：`fixture.txt` 含合成未知值 `PI_FIXTURE_VALUE=314159`。
- 配置：只开放 `read`。
- 预期：模型必须 toolUse，result 回填后再次调用模型。
- 结果：通过；2 turn、1 tool start/end、最终 `314159`。
- 证据：`R-002`。

## R-SCENARIO-003/004：跨进程 resume

- 进程 A：持久 session `analysis-resume-001`，记忆合成 token。
- 进程 B：相同 session-id，不在 prompt 重复 token。
- 结果：A 返回 ACK，B 返回 `PI_RESUME_2718`。
- 证据：`R-003`, `R-004`。

## X-SCENARIO-001：agent-core faux provider

- Files：`agent-loop.test.ts`, `agent.test.ts`。
- 结果：2 files，39 tests passed。
- 覆盖：parallel/sequential、hooks、queue、termination、length stop、event settlement。

## X-SCENARIO-002：新 AgentHarness

- Files：`agent-harness.test.ts`, `session.test.ts`, `compaction.test.ts`。
- 结果：3 files，61 tests passed。
- 覆盖：save point refresh、pending write ordering、hooks、abort、session/compaction helpers。

## X-SCENARIO-003：Coding Agent recovery

- Files：`agent-session-compaction.test.ts`, network retry regression, session build-context。
- 结果：3 files，31 tests passed。
- 覆盖：overflow/threshold compaction、bounded retry、active context rebuild。

## 意外观察

自定义 model 声明 `reasoning:false` 且 `supportsReasoningEffort:false`，但 SiFlow 服务端仍流出 thinking block。此前直接 endpoint smoke test 通过 `chat_template_kwargs.enable_thinking=false` 可关闭；Pi 的 standard models.json path 本轮没有注入该 request body。该差异不否定 harness loop，但 raw trace 可能包含 reasoning，已在 normalized trace 中移除。
