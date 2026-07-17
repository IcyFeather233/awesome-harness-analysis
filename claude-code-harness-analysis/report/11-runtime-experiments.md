# 运行实验

> **证据边界。** 本报告分析 source-only commit `16a676f`。其 1,884 个 TS/TSX 文件、关键 symbol 与 feature gates 和论文所述 Claude Code v2.1.88 corpus 强指纹一致，但缺少 package version、上游 tree hash、build manifest，不能视为已证明的 exact 官方 artifact。快照仍有 657 个无法解析的相对 import；除 SiFlow 协议探针外，主循环、安全、session 与 subagent 结论均为 static-only。官方材料只支持产品立场，五价值/十三原则是 analyst synthesis。[X: X-001–X-003] [D: D-001–D-008] [C: C-001, C-024–C-026] 首次遇到缩写或内部名词时，可查 [全局术语表](16-glossary.md)。


## 实验术语

- **Target runtime**：真实 Claude Code build 启动后的 loop、permission、tool 和 persistence 行为。只有它能产生本报告定义的 R evidence。
- **Protocol probe**：直接向模型 endpoint 发送最小合成 request，检查 HTTP/SSE/tool-use 方言。它绕过了 Claude Code，所以只能证明 provider 接口子集。
- **Scripted model**：按测试脚本返回确定性 model/tool blocks 的假模型，用来强制 harness 走指定分支；它测试 harness，不测试真实模型判断质量。
- **Fault injection**：主动制造 timeout、deny、corruption、oversized output 或 crash，观察恢复路径。
- **Sanitized result**：移除 credential、私有 prompt、代码和路径后保存的实验摘要；sanitized 不等于原始 trace 完整保留。
- **Blocked scenario**：实验前置条件不成立，未形成目标行为证据；它不是“测试失败”，更不是“机制不存在”。

## 已执行

| ID | 实验问题 | 设置与前置 | 结果 | 证据边界 |
|---|---|---|---|---|
| X-SCENARIO-001 | 当前 source snapshot 能否自包含启动成 target runtime。 | Clean commit；静态 import resolver 检查相对 import、manifest 和闭合 module graph。 | 发现 657 个 missing relative imports，且缺少 package/build manifest。 | 证明本轮不能安全形成 target runtime R evidence；不证明这些源码机制在官方 artifact 中不存在。 |
| X-SCENARIO-002 | SiFlow endpoint 是否支持报告后续实验需要的 Anthropic Messages 方言子集。 | 无真实用户凭据、无私有 prompt；qwen3.6-35ba3b；非流式、SSE、forced tool_use 最小请求。 | models/messages/SSE/tool_use 均 HTTP 200，forced echo 返回结构合法。 | 只证明 provider protocol 子集可用；没有经过 Claude Code request builder、retry、permission 或 tool loop。 |
| X-SCENARIO-008 | 本地快照是否与论文声称的 Claude Code v2.1.88 TypeScript corpus 同源。 | 文件计数、关键 symbol、feature gates 和高辨识度机制 fingerprint。 | 1,884 TS/TSX 精确匹配，关键机制同名且结构强一致。 | 支持 strong fingerprint；缺少 package version、tree hash 或字节 artifact，不能升级为 exact identity。 |

Provider probe 的 forced call 是 echo({"text":"hello"})，并使用 `chat_template_kwargs.enable_thinking=false`，避免默认 thinking 消耗短输出预算。SSE（Server-Sent Events）是服务器在一条 HTTP response 上持续推送事件的文本流协议；HTTP 200 + 合法 SSE/tool_use 只能说明 endpoint 理解这组最小请求。原始内容仅含合成 prompt，sanitized 结果保存在 [provider-probe.json](../experiments/provider-probe.json)。[X: X-002]

## 未执行及原因

| ID | 场景 | 目标 claim | 为什么阻塞 | 下一步需要什么 |
|---|---|---|---|---|
| X-SCENARIO-003 | scripted text-only query | C-003/C-004 | 无闭合 module/build graph，无法启动真实 `query()` 并替换 callModel。 | 同 commit package/lock、source map 或 compiled bundle；然后用 scripted response 比较 event/message sequence。 |
| X-SCENARIO-004 | permission deny 无 side effect | C-012–C-014 | 无可启动 target，因此无法同时观测 permission event、process tree、filesystem diff 和 network attempt。 | 可运行 bundle，加 deny fixture、sandbox on/off、hook/MCP lifecycle matrix。 |
| X-SCENARIO-005 | context overflow | C-006/C-007 | 无法构造真实 request envelope，也无法触发实际 threshold、snip、microcompact 或 autocompact。 | 可运行 target、超长 synthetic history、sanitized request digest 与 survivor comparison。 |
| X-SCENARIO-006 | resume/fork | C-015/C-016 | 无法产生和恢复真实 JSONL、metadata、file history 与 permission context。 | 可运行 target、resume/fork/corruption fixture、permission grant freshness check。 |
| X-SCENARIO-007 | child inheritance matrix | C-017–C-020 | 无法启动 AgentTool/runAgent 的 sync、async、worktree、teammate 分支。 | Child runtime fixture，记录 pid、cwd、tools、mode、abort controller、transcript 和 result channel。 |

“blocked”不表示机制不存在，只表示本轮不能形成 R/X evidence。为了避免把 injector 行为冒充原系统，本报告没有手工补齐 657 个 import、伪造 package.json 或用 Python 重写 query loop。

## 下一轮最小 runtime package

需要同 commit 对应的 `package.json`/lock（依赖、版本与可重复安装信息）、完整 source-map contents（bundle 到原始模块的映射与可能内嵌源码）、`bun:bundle` feature manifest（构建时到底保留哪些 feature 分支），或已编译 external bundle。

恢复前置条件后，先跑 `version/help` 验证 bootstrap，再利用 `query/deps.ts` 的 **callModel seam**（core 调模型时可替换的依赖边界）注入 scripted response，执行 deterministic tool loop；最后才接真实 SiFlow endpoint。这样能把“harness 状态机错误”和“真实模型随机选择”分开。
