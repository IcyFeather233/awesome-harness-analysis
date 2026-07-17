# 01 范围与方法

## 冻结对象

- Repository：`https://github.com/earendil-works/pi`
- Tag：`v0.80.7`
- Commit：`818d67457cdd6b60bce6b121d16b23141c252dd8`
- Worktree：detached HEAD，分析开始和结束时目标代码无 tracked changes
- Runtime：Linux x86_64；临时 Node `22.19.0`；npm `10.9.3`；Vitest `4.1.9`
- Real model：`siflow/qwen3.6-35ba3b`，OpenAI-compatible endpoint；无 API key

完整配置见 [manifest.json](../manifest.json)。

## 证据等级

| 标记 | 证据来源 | 可以建立 | 不能单独建立 | 本报告实例 |
|---|---|---|---|---|
| `D` | 固定 commit 的仓库文档 | 明确产品边界、公开设计立场、已知未完成项 | 代码一定实现文档描述，或生产默认启用 | security、extension、AgentHarness lifecycle 文档 |
| `S` | 固定 commit 源码与测试 contract | 类型、控制流、condition 和可到达路径 | 该路径在本轮运行过，或生产出现频率 | `runAgentLoop`、`AgentSession`、JSONL v3 |
| `R` | 真实 SiFlow + official Pi runtime | 命名配置下一次确实发生的路径和事件顺序 | 其他 provider/mode/tool/platform 等价 | text、read-tool、跨进程 resume |
| `X` | faux provider/定向 test suite | controller 分支、顺序、反例和失败 contract | 真实模型质量或部署安全 | 39 + 61 + 31 tests |
| `I` | 多条 D/S/R/X 的分析综合 | 明示 tradeoff、风险和下一步实验 | 作者意图或 HIR 中的直接事实 | workspace/session 缺少共同 checkpoint 的后果 |

每条 claim 都有 falsification test；每个 HIR node/edge 都有 evidence ID。严格 validator 结果为 `0 errors, 0 warnings`。

## 动态安全边界

所有真实 model runs 使用：

- `/tmp/pi-analysis-runtime/home` 作为独立 HOME；
- `/tmp/pi-analysis-runtime/fixture` 作为合成 workspace；
- `/tmp/pi-analysis-runtime/sessions` 作为合成 session store；
- `--no-extensions --no-skills --no-prompt-templates --no-context-files --no-approve`；
- 无工具或只开放 `read`；
- 不运行 write/edit/bash；
- raw trace 只包含合成内容，normalized trace 删除 prompt、thinking、工具参数和文件内容。

## 解释边界

`R` 只能证明某路径在指定模式中发生过一次，不能证明生产频率或所有配置。没有运行到的 path 仍可能存在；没有在源码中找到的行为也不能在 coverage 不完整时直接判定为不存在。设计“为什么”仅在文档明确说明时归为 documented intent，否则只讨论可观察 tradeoff。

## 覆盖

14 个 codebook 模块全部有状态：interfaces/core loop/model/tools/session/recovery 等为 analyzed；context、sandbox、subagents、observability 为 partial。详细文件与未覆盖面见 [coverage.json](../evidence/coverage.json)。
