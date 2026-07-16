# Awesome Harness Analysis

一个面向 AI agent harness 的架构分析集合。

本项目使用 [harness-analysis-skill](https://github.com/IcyFeather233/harness-analysis-skill) 阅读和运行真实 agent harness 仓库，从源码结构、运行轨迹、权限边界、上下文生命周期、扩展机制、subagent、持久化与恢复等维度，整理出带证据、可复现的深度架构报告。

它不是普通的代码 Wiki，也不只是文件树和调用关系摘要。每个分析都会先冻结到明确的 tag/commit，再结合静态源码调查、真实模型场景、scripted model、定向测试或故障实验，逐步恢复 harness 的设计框架与实际执行逻辑。

![Pi agent harness overview](pi-harness-analysis/diagrams/generated/pi-system-overview.png)

## 分析方法

`harness-analysis-skill` 将分析过程组织为一套证据驱动的架构恢复流程：

1. **冻结研究对象**：记录仓库 tag、commit、入口、运行时、provider 和启用配置。
2. **静态架构恢复**：调查 agent loop、context、tools、permissions、sandbox、subagents、session、recovery 和 observability。
3. **结构化证据**：区分文档证据（D）、静态源码（S）、真实运行（R）、控制实验（X）和分析推断（I）。
4. **主动运行验证**：在隔离环境中运行代表场景，用真实 trace 或定向测试验证关键路径和反例。
5. **Harness IR**：将组件、状态、边界和执行关系整理成统一的中间表示，使报告、图和证据保持一致。
6. **多层可视化**：同时保留读者友好的架构插图、确定性叙事图和可追溯的技术证据图。
7. **怀疑性复核**：检查隐藏入口、条件分支、policy 绕行、static/runtime 冲突和未经证实的设计意图。

重要结论必须能够回到源码、文档、场景或实验记录；没有找到的机制不会直接写成“不存在”，推断出的权衡也不会伪装成作者声明。

## 已收录分析

| Agent harness | 冻结版本 | 分析入口 | 简要结论 |
|---|---|---|---|
| [earendil-works/pi](https://github.com/earendil-works/pi) | `v0.80.7` / `818d674` | [Pi Agent Harness 架构恢复报告](pi-harness-analysis/report/index.md) | 薄核心、强扩展、外部隔离；当前 `AgentSession` 与新 `AgentHarness` 构成一条尚未完成的迁移线 |

Pi 分析同时提供：

- [设计空间与贯穿案例](pi-harness-analysis/report/00-design-space-and-running-example.md)
- [核心循环与编排](pi-harness-analysis/report/03-core-loop.md)
- [上下文、记忆与压缩](pi-harness-analysis/report/04-context-memory-compaction.md)
- [权限、sandbox 与 workspace](pi-harness-analysis/report/06-permissions-sandbox-workspace.md)
- [运行实验](pi-harness-analysis/report/11-runtime-experiments.md)
- [Harness IR](pi-harness-analysis/hir.json)
- [Claims 与证据索引](pi-harness-analysis/report/claim-index.md)

## 后续计划

Pi 是这个集合的第一个案例。后续会继续使用同一套 `harness-analysis-skill`、证据模型和可视化规范，加入更多 coding agent、通用 agent runtime、多 agent framework 和 controller/harness 项目的独立分析。

每个新项目会保留自己的冻结版本、HIR、evidence、scenarios、traces、diagrams 和 report，完成单项目验证后再进行跨项目设计空间比较，避免用不一致的分析口径得出表面结论。

## 目录结构

```text
awesome-harness-analysis/
├── README.md
└── pi-harness-analysis/
    ├── manifest.json
    ├── hir.json
    ├── evidence/
    ├── scenarios/
    ├── traces/
    ├── diagrams/
    └── report/
```

分析 Skill 独立维护在 [IcyFeather233/harness-analysis-skill](https://github.com/IcyFeather233/harness-analysis-skill)。
