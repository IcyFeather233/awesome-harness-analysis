# 设计决策与权衡

下表的“当前机制”来自代码；“documented intent”只有文档直接支持时才填写；其余 tradeoff 是分析者综合。

<!-- EXPLANATION:decision-table -->
## 怎么读这张表

`当前机制` 只陈述源码实际做法；`Documented intent` 只有仓库文档能直接支持时才填写；`代价/替代方案` 是分析者综合。`置信度=中` 往往不是因为没找到代码，而是因为作者动机未记录、关键 feature 未运行，或结论跨越了多个平台/configuration。

例如“child 独立 context、共享 workspace”的结构证据很明确，但“为什么选择这种隔离粒度”没有作者声明，所以 tradeoff 只能写成可观察后果，不能写成设计团队的真实动机。

| 决策 | 当前机制 | Documented intent | 可观察收益与代价 | 条件/边界 | 证据 | 置信度 | 反例测试 |
|---|---|---|---|---|---|---|---|
| 耐久状态归 thread | `LiveThread` 通过 storage-neutral `ThreadStore` 追加/flush rollout，resume 按 thread id 重建 history。 | Thread-store 文档明确该持久化抽象。 | Resume/fork 语义清晰；代价是 flush、corruption 与 workspace drift 必须分别处理。 | 本轮仅验证 local JSONL 正常尾部与跨进程 resume。 | `D-004`, `S-018`, `S-019`, `X-006` | 高 | 截断 header/middle/tail 并 resume，比较拒绝、降级与 history。 |
| History 与 world state 分离 | Messages 保留 API history；typed world-state snapshot/diff 维护动态环境 baseline。 | AGENTS 要求增量 model-visible context。 | 减少重复注入和 cache churn；baseline 失配会产生陈旧或重复 context。 | Default core；完整 source differential 未执行。 | `D-007`, `S-005`, `S-006`, `I-001` | 中 | 改 cwd/AGENTS/subagent/app 状态并比较 request items 与 diff。 |
| Registry/exposure 分离 | ToolSpecPlan 每 turn 合成 handler registry 与 model-visible specs。 | 未找到直接作者动机。 | 适配 provider/mode/depth；静态工具清单容易被误读为实际能力面。 | Provider capability、feature、MCP、extension、agent depth。 | `S-009`, `X-005` | 高 | 注册 hidden/deferred tool，检查不可见时 model request 与 router 行为。 |
| 进程 exec 使用 policy + sandbox | 普通 command 经 ExecPolicy/approval 后按 permission profile 变换到平台 sandbox；patch 走独立专用链。 | Core README 记录 platform sandbox；统一动机未完整记录。 | 区分授权与隔离；代价是平台、mode 与 handler 矩阵复杂。 | Linux deny 已观察；真实 sandbox backend、MCP/dynamic/patch differential 未跑。 | `D-002`, `S-012`–`S-014`, `S-028`, `I-002` | 中 | 三平台 side-effect matrix，加普通 exec/apply_patch/MCP/dynamic handler 对照。 |
| Child 独立 context、共享 workspace | CodexDelegate/AgentControl 创建独立 child session/history，继承 effective config/cwd。 | 未找到隔离粒度的作者说明。 | 减少 root context；共享 cwd 带来文件竞争与外部状态耦合。 | V1/V2 feature gate；本轮只跑 V1 depth=1。 | `S-015`–`S-017`, `S-027`, `X-005` | 中 | 比较 child context/tools/policy/cwd，并发写同一文件，注入 cancel/crash。 |
| Tool runtime 使用读写锁 | Parallel-capable handler 共享读锁，exclusive handler 获取写锁。 | 未找到直接作者动机。 | 提升只读吞吐并串行化独占副作用；错误分类会破坏安全/顺序假设。 | 由 handler capability 决定，不由工具名称自动推断。 | `S-025` | 中 | 脚本化两 read + 一 exclusive，记录锁、start/end 与 result merge 顺序。 |

## 可证伪性

上述每项都在 [claims](../evidence/claims.jsonl) 中携带 falsification test。特别需要避免两种过度解释：第一，代码的高内聚结构不等于作者明确追求某个价值；第二，一次成功的 deny/resume 实验不等于所有 provider/platform/entrypoint 都具备相同行为。
