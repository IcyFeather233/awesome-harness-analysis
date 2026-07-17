# 运行实验

> **证据边界。** 本报告分析 source-only commit `16a676f`。其 1,884 个 TS/TSX 文件、关键 symbol 与 feature gates 和论文所述 Claude Code v2.1.88 corpus 强指纹一致，但缺少 package version、上游 tree hash、build manifest，不能视为已证明的 exact 官方 artifact。快照仍有 657 个无法解析的相对 import；除 SiFlow 协议探针外，主循环、安全、session 与 subagent 结论均为 static-only。官方材料只支持产品立场，五价值/十三原则是 analyst synthesis。[X: X-001–X-003] [D: D-001–D-008] [C: C-001, C-024–C-026]


## 已执行

| ID | 问题 | 设置 | 结果 | 能证明什么 |
|---|---|---|---|---|
| X-SCENARIO-001 | snapshot 能否自包含运行 | clean commit；静态 import resolver | 657 missing relative imports；无 manifest | 当前快照不满足 target runtime 前置条件 |
| X-SCENARIO-002 | SiFlow 是否支持关键 Anthropic 方言 | 无凭据、无私有 prompt；qwen3.6-35ba3b | models/messages/SSE/tool_use 均 HTTP 200 | provider 协议子集可用 |
| X-SCENARIO-008 | 本地快照与论文 v2.1.88 corpus 是否同源 | 文件计数 + 高辨识度 symbol/feature fingerprint | 1,884 TS/TSX 精确匹配，关键机制同名 | strong match；不能证明 exact tree |

Provider probe 的 forced call 是 echo({"text":"hello"})，并使用 chat_template_kwargs.enable_thinking=false，避免默认 thinking 消耗短输出预算。原始内容仅含合成 prompt，sanitized 结果保存在 [provider-probe.json](../experiments/provider-probe.json)。[X: X-002]

## 未执行及原因

| ID | 场景 | 目标 claim | 阻塞 |
|---|---|---|---|
| X-SCENARIO-003 | scripted text-only query | C-003/C-004 | 无闭合 module/build graph |
| X-SCENARIO-004 | permission deny 无 side effect | C-012–C-014 | 无可启动 target |
| X-SCENARIO-005 | context overflow | C-006/C-007 | 无可启动 target |
| X-SCENARIO-006 | resume/fork | C-015/C-016 | 无可启动 target |
| X-SCENARIO-007 | child inheritance matrix | C-017–C-020 | 无可启动 target |

“blocked”不表示机制不存在，只表示本轮不能形成 R/X evidence。为了避免把 injector 行为冒充原系统，本报告没有手工补齐 657 个 import、伪造 package.json 或用 Python 重写 query loop。

## 下一轮最小 runtime package

需要同 commit 对应的 package.json/lock、完整 source map contents、bun:bundle feature manifest 或已编译外部 bundle。然后先跑 version/help，再用 query/deps.ts 的 callModel seam 做 deterministic tool loop；最后才接真实 SiFlow endpoint。
