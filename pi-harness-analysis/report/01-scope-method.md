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

| 标记 | 含义 | 本报告用途 |
|---|---|---|
| `D` | 仓库文档 | 产品边界、明确意图、已知未完成项 |
| `S` | 固定 commit 源码 | 实现结构与可能路径 |
| `R` | 真实运行观察 | 命名配置下一次确实发生的路径 |
| `X` | 控制实验/定向测试 | controller 分支与反例验证 |
| `I` | 分析推断 | 本轮没有把纯推断写成 HIR 事实 |

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
