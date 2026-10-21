# 外部解读与当前源码的对照

本轮从作者文章、使用者记录、源码分析和产品评测中筛选了 16 篇页面。15 篇阅读了相关正文，1 篇只能读取元数据与搜索摘要。实现仍固定在 `v0.80.7 / 818d674` 的当前 AgentSession 路径；完整来源信息见 [external-sources.json](../evidence/external-sources.json)。

## 吸收的阅读角度

“极简”可以帮助确定检查顺序：看模型请求中实际有什么，再看是谁决定加入这些内容。作者的上下文控制动机已放入[上下文章节](04-context-memory-compaction.md)，与 system prompt、active tools、context hook 和会话分支的具体入口对应。这里没有把短 prompt 写成普遍的性能优势。

扩展的作用需要沿着持久状态、reload 和工具 registry 一起看。使用者写出一段扩展后，怎样继续修改并恢复状态，比“能注册一个函数”更能解释接口的用途。[工具与扩展章节](05-models-tools-extensions.md)补充了工具结果的两个消费方和资源重建顺序。

树状会话适合解释临时探索后回到主线的过程。配合 `branchWithSummary()`，可以选择带回哪些对话信息；文件副作用则沿真实工作区保留。这一工作流已融入[会话章节](08-sessions-persistence-recovery.md)。

队列和事件也有使用者层面的含义。steering 与 follow-up 给出不同的输入消费时机；事件完成与任务验收则是两种观测结果。这些解释分别放入[循环](03-core-loop.md)和[可观测性](09-observability.md)，并继续保留源码条件。

## 哪些说法需要修正或限定

| 外部表述 | 对照固定版本后的处理 |
|---|---|
| 部分文章概括为只有四个内置工具 | 当前定义有七个名称，默认 active set 为 read/bash/edit/write。原作者也提到可选只读工具。按 registry 与 active set 分开描述。 |
| 把最近约 20000 token 与 reserve 混称 | `reserveTokens=16384` 用于触发阈值；`keepRecentTokens=20000` 用于保留片段估算，见 S-028/S-029。 |
| 将 follow-up 说成等待整个 run settled 后才开始 | 当前低层 loop 在发出 agent_end 前先检查 follow-up，产品 settled 更晚，见 S-001/S-019。 |
| 将 SYSTEM.md 说成改系统提示的唯一入口 | 当前 `before_agent_start` 也能提供 system prompt，SDK 还有配置路径。按具体入口解释，见 S-002/S-004。 |
| 使用 agent/pre-step、agent/request 等 hook 名称 | 本报告核对的接口名是 context、before_agent_start、before_provider_request 等；未把社区层或其他版本名称套到当前类型。 |
| 较新分析使用 prepareRequest、context_edit 等机制 | 这些文章标注的是其他版本；只保留其阅读视角，具体功能不回填到本版本。 |
| 由个人成本案例、产品评分或标题推断“极简总是更好” | 未采纳这类普遍结论。原作者的 MCP/CLI 实验也有不同任务与评测对象，不能当作本报告的 Pi 测量。 |

四工具概括可见 [PiLot](https://www.pivscode.com/blog/pi-minimal-extensible-coding-agent/) 与 [Holbreich](https://alexander.holbreich.org/posts/2026/pi-coding-agent/)；预算用语见 [Haochuan](https://blog.haochuanz.net/posts/agent-harness-04-pi)；follow-up 表述见 [Shilin](https://edward40.com/p/pi-agent-internal/)；提示与 hook 名称见 [Walking Labs](https://walkinglabs.github.io/learn-harness-engineering/zh/harness-designs/pi/)；较新版本例子见 [Rememorio](https://rememorio.github.io/blog/agent-framework/en/pi-agent-harness/)。它们提供待核对的解释，表中的实现判断来自固定源码。

## 来源与采用范围

| 来源 | 日期或版本 | 本报告如何使用 |
|---|---|---|
| [B-01 · Mario Zechner：作者的 Pi 设计回顾](https://mariozechner.at/posts/2025-11-30-pi-coding-agent/) | 2025-11-30；早期实现，未固定本报告 commit | 控制上下文、检查交互；工具内容与显示数据分工。 |
| [B-02 · Armin Ronacher：Pi 与可定制工作流](https://lucumr.pocoo.org/2026/1/31/pi/) | 2026-01-31；早期使用体验，未固定 commit | 扩展状态、热重载和树状会话支持迭代工作流。 |
| [B-03 · Mario Zechner：浏览器脚本与按需说明](https://mariozechner.at/posts/2025-11-02-what-if-you-dont-need-mcp/) | 2025-11-02；浏览器工具案例；非 v0.80.7 实验 | 通过按需读取说明和脚本组合提供额外能力。 |
| [B-04 · Mario Zechner：MCP / CLI 终端工具实验](https://mariozechner.at/posts/2025-08-15-mcp-vs-cli/) | 2025-08-15；Claude Code 与终端工具比较；不是 Pi 评测 | 原实验没有给出 CLI 对 MCP 的普遍胜负结论。 |
| [B-05 · Haochuan：双队列、会话树与边界](https://blog.haochuanz.net/posts/agent-harness-04-pi) | 2026-08-25；文章声明 8fa7eebd2353；与 818d674 不同 | 双队列对应两种输入时机；压缩预算术语需修正。 |
| [B-06 · Shilin：内部机制导读](https://edward40.com/p/pi-agent-internal/) | 2026-07-21；发布日期接近，但源码链接未固定本报告 commit | 应用消息与 provider 格式分离；据此追查数据转换。 |
| [B-07 · Rememorio：v1.0.0 源码导读](https://rememorio.github.io/blog/agent-framework/en/pi-agent-harness/) | 日期未明示；明确固定 v1.0.0 / a13d35a742c6ef8462812a28fbe1d8c8b7431c32 | 可参考存储历史、分支、请求三种视图的阅读方式。 |
| [B-08 · Walking Labs：中文 Harness 设计拆解](https://walkinglabs.github.io/learn-harness-engineering/zh/harness-designs/pi/) | 日期未明示；未固定版本，混合主项目与社区扩展 | 扩展可编程性是有用视角；接口名须逐项核查。 |
| [B-09 · Kahtaf Alam：领域 Agent 构建记录](https://kahtaf.com/blog/lessons-from-building-a-domain-agent/) | 2026-06-22；OpenCandle 的应用层经验，非本报告实验 | 按职责和轨迹定位失败，并单独评价产物。 |
| [B-10 · Scott Spence：my-pi 构建与观测](https://scottspence.com/posts/building-my-pi-claude-code-alternative-with-pi) | 2026-04-26；持续更新的 my-pi 派生配置，未固定 Pi commit | telemetry 区分运行故障与已完成但答错的结果。 |
| [B-11 · Julian Prokay：pic 任务管理扩展](https://jprokay.com/post/018-pi-coding-agent) | 2026-02-15；自建 pic CLI / task extension | 任务状态由 CLI/SQLite 管理，extension 负责交互。 |
| [B-12 · Alexander Holbreich：定制工具的投入](https://alexander.holbreich.org/posts/2026/pi-coding-agent/) | 2026-06-03；未固定版本，含当时产品与价格比较 | 定制能力伴随维护工作流的投入。 |
| [B-13 · DeepakNess：日常配置与使用](https://deepakness.com/blog/pi-agent-setup) | 2026-05-29；页面标注更新 2026-08-14；个人配置含扩展 | 日常使用涉及模型选择、队列和定制界面。 |
| [B-14 · DevOpsTales：v0.84.2 产品评测](https://devopstales.github.io/ai/pi-coding-agent-review/) | 2026-09-07；声明对齐 v0.84.2；晚于目标版本 | 阅读其上手与治理讨论，机制仍核对本地版本。 |
| [B-15 · PiLot Studio：PiLot 产品方解读](https://www.pivscode.com/blog/pi-minimal-extensible-coding-agent/) | 2026-09-23；VS Code 产品方文章，主要转述作者论点 | 可作生态入口；默认工具数与 registry 数需区分。 |
| [B-16 · Matteo Chieppa：工具栈入门指南](https://www.matteochieppa.com/en/blog/pi-coding-agent-complete-guide) | 2026-04-05；搜索摘要声明 2026-04-27 / v0.70.2；正文读取受客户端渲染限制 | 检索用于发现工具/资源分层线索，未据此新增机制结论。 |

作者原文提供其当时的设计目的，使用者文章提供具体工作方式，代码解读提供追查线索。转述同一原文的多篇文章不构成多份独立验证。后续版本的文章只用于识别版本边界，本报告没有据此扩大到新版实现或新增性能结论。
