# 项目信任、执行权限与工作区

Pi 的默认工具和 extensions 以启动进程的 OS 权限运行。Project trust 控制项目启动资源的加载；逐工具确认或路径保护由可选 extension 实现。容器、VM 或其他 OS policy 才提供相应的执行隔离。[D: D-002, D-007; S: S-006, S-007, S-017]

## Project trust 怎样决策

`resolveProjectTrusted()` 依次处理显式 override、是否存在需要信任的项目资源、extension 的 trust 决策、已保存的 trust 记录，以及 default policy。`ask` 模式在没有 UI 且没有前序决策时返回 false；有 UI 时让用户选择并按选项保存记录。[S: S-006]

`DefaultResourceLoader` 先用不信任项目的状态加载 bootstrap extensions，再解析 trust 并加载最终资源集合。受控对象包括 `.pi` 项目配置和相应资源。AGENTS/CLAUDE context 文件有自己的加载路径，不能用“未信任项目”推断所有项目文本均未进入 prompt。[S: S-005; D: D-002]

## 一次工具调用经过什么边界

工具进入 registry 后先校验参数，再经过可选 `tool_call` hook。hook 返回 block 会生成错误结果并跳过 handler。默认配置没有全局逐工具审批弹窗；`protected-paths.ts` 展示的是可选 hook 如何拦截 write/edit。[S: S-003, S-017, S-018]

内置 bash 在指定 cwd 启动 shell并继承进程环境；timeout 参数可选。Unix 分支使用进程组处理，abort/timeout 走终止进程树的逻辑。这里描述内置 bash backend；subagent 示例自己的 `spawn/kill` 行为应单独检查。[S: S-007]

| 边界 | 控制对象 | 阅读时需要保留的范围 |
|---|---|---|
| Project trust | 项目配置、包和 extensions 等启动资源 | 不构成后续 read/bash/write 的权限决策 |
| tool_call hook | 经过工具调用入口的命名 handler | extension 的直接 fs/process/network 操作不必经过它 |
| 工具路由到 guest | 被配置为委托执行的 backend | 未委托的 custom tool 仍可能在 host 执行 |
| whole-process container/VM | Pi 及其子进程的部署边界 | 挂载目录和网络配置决定实际可访问范围 |

工作区是工具访问的真实文件系统。切换会话分支会改变模型上下文，但没有为文件内容创建对应的事务式回滚。[C: C-008]

本次通过 mock/faux 检查部分工具阻断和事件逻辑，未部署容器/VM，也未运行完整的 extension 副作用矩阵。源码与官方安全说明见 [security.md](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/docs/security.md#L3)。

## 怎样理解外部文章中的安全评价

Haochuan 将这种职责划分评价为[明确的安全边界](https://blog.haochuanz.net/posts/agent-harness-04-pi)。本报告采用可检查的机制区分：trust 约束资源加载，hook 约束经过它的调用，OS/container/VM 约束实际执行权限。文章的评价不替代部署测试，也不能推出其他权限系统都无效。[D: D-002, D-007; S: S-006, S-017]
