# 专题阅读与查证索引

[Pi Agent Harness 分析报告](index.md)是可以连续阅读的主文。下面的资料用于追查具体机制，不要求按文件编号逐篇读完。

## 从一个操作追到代码

- [一次请求的运行过程](00-task-walkthrough.md)：历史 read 场景及其事件路径。
- [入口、对象与生命周期](02-interfaces-lifecycle.md)：对象关系，turn 与三个结束事件的例子。
- [核心循环与工具执行](03-core-loop.md)：参数准备、并发排序、队列与错误回填。
- [AgentSession 的状态与运行收尾](10-implementation-details.md)：配置刷新、代码规则触发的重试、退避与最终收尾。

## 理解消息、状态与扩展

- [上下文、消息转换与压缩](04-context-memory-compaction.md)：持久历史、当前分支、请求视图，custom/Bash/摘要的转换例子，以及压缩切点、长任务分段和压缩期间的输入队列。
- [从 Pi 的请求到模型输入](18-model-input-encoding.md)：API 字段、对话模板与 token，以及 Qwen3.8-27B / DeepSeek V4 Flash 的工具格式对照。
- [模型接口、工具与扩展](05-models-tools-extensions.md)：模型分派、工具 registry、content/details 与 reload。
- [会话、持久化与恢复](08-sessions-persistence-recovery.md)：首次写入、分支、fork 和重新打开文件。

## 查看执行边界和旁支

- [项目信任、执行权限与工作区](06-permissions-sandbox-workspace.md)：trust、hook 与部署隔离分别控制什么。
- [子代理与多进程编排](07-subagents-delegation.md)：扩展示例及实验性实例管理的旁支资料。
- [事件与可观测性](09-observability.md)：事件说明了什么，以及任务验收还需要什么。

## 查证范围和依据

- [范围与方法](01-scope-method.md)：固定版本、证据分类和分析范围。
- [实验记录](11-runtime-experiments.md)、[失败与待验证路径](12-failure-modes-open-questions.md)、[覆盖与复现](13-coverage-reproducibility.md)。
- [源码与结论索引](14-source-claim-index.md)、[术语表](16-glossary.md)、[外部解读与源码对照](17-external-perspectives.md)。

这些资料保留详细参数、源码编号和实验状态，供需要深入核对时使用。
