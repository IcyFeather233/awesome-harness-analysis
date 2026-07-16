# 设计决策与权衡

下表的“当前机制”来自代码；“documented intent”只有文档直接支持时才填写；其余 tradeoff 是分析者综合。

| 决策 | 当前机制 | Documented intent | 代价/替代方案 | 条件 | 证据 | 置信度 |
|---|---|---|---|---|---|---|
| 耐久状态归 thread | LiveThread + append rollout | thread-store 文档说明 storage-neutral boundary | resume/fork 清晰；需处理 flush、corruption、workspace drift | local store | `D-004`, `S-018`, `S-019`, `X-006` | 高 |
| history 与 world state 分离 | messages + typed snapshot/diff | AGENTS 要求增量 model-visible context | 减少重复；baseline 同步更复杂 | default core | `D-007`, `S-005`, `S-006`, `I-001` | 中 |
| registry/exposure 分离 | ToolSpecPlan 每 turn 选择 specs | 未记录 | provider/mode 适配；静态工具清单容易误导 | provider capabilities/features | `S-009`, `X-005` | 高 |
| 安全采用双层边界 | exec policy + approval + sandbox transform | core README 记录 platform sandbox | defense in depth；矩阵与平台差异增加测试成本 | approval/sandbox/platform | `D-002`, `S-012`–`S-014`, `I-002` | 中 |
| child 独立 context、共享 workspace | CodexDelegate + AgentControl | 未记录 | 节省 root context；共享 cwd 产生文件竞争 | V1/V2 feature gate | `S-015`–`S-017`, `X-005` | 中 |
| read/write tool locks | parallel read, exclusive write | 未记录 | 提升吞吐且保护串行副作用；handler 分类错误会破坏假设 | tool capability | `S-025` | 中 |

## 可证伪性

上述每项都在 [claims](../evidence/claims.jsonl) 中携带 falsification test。特别需要避免两种过度解释：第一，代码的高内聚结构不等于作者明确追求某个价值；第二，一次成功的 deny/resume 实验不等于所有 provider/platform/entrypoint 都具备相同行为。
