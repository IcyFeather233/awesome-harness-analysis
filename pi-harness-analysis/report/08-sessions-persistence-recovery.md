# 会话、持久化与恢复

`SessionManager` 把会话存为带 `id/parentId` 的 JSONL entry 树。新 entry 以当前 leaf 为 parent，再把 leaf 移到自己。模型使用的是当前分支投影出的消息；文件保留的历史可能包含其他分支、旧错误、摘要及配置记录。[S: S-008]

## 内存记录何时写成文件

![新会话什么时候真正创建文件，之后如何追加？](../diagrams/generated/pi-session-first-write-v3.png)

对新建且尚未写过文件的持久会话，user/配置 entry 先留在内存，首条 assistant entry 触发创建文件并写入已有记录，之后逐条追加。已有空文件、格式迁移与分支副本另有条件路径。证据：S-020、X-006。[提示词、生成参数与复核记录](../diagrams/generated/metadata.json)。

`newSession()` 先生成 header、session id 和文件路径，初始化内存索引。每次 append 都先更新 `fileEntries`、`byId` 和 leaf，再调用 `_persist()`。

对尚未写过文件的新会话，`_persist()` 检查历史中是否已有 assistant entry。只有 user 或初始配置记录时先留在内存；首条 assistant entry 出现后，以排他创建模式写入当前全部记录。之后新 entry 逐条追加。[C: C-023; S: S-020]

因此 `getSessionFile()` 返回路径、`message_end` 已发生和数据已落盘是不同观察点。fork 的路径若只有 user 消息，也会延迟到 assistant 出现后写文件。本次 tree-traversal 测试覆盖了这个条件。[X: X-006]

普通新增历史采用追加方式；格式迁移、初始化已有空文件及创建含已有 assistant 的分支副本有明确重写路径。“append-only tree”描述普通历史追加和分支语义，不应理解为文件永远不重写。源码也未在这些写入步骤中提供与 workspace 共同提交的事务。[S: S-020]

## Branch 与 fork

`branch(entryId)` 在当前 manager 中移动 leaf，下一条 append 成为该点的子节点，已有历史保持不变。`createBranchedSession()` 则提取 root 到指定 leaf 的路径，创建新的 session id 和文件，并重建保留项的 parent 链及标签。[S: S-008]

`branch()` 更新当前 manager 的内存 leaf；随后新增 entry 的 parentId 记录分支关系。重新打开文件时，索引从已有记录重建。[S: S-008]

这些操作都改变会话视图，workspace 文件仍保持现实状态。恢复旧上下文后，工具下一次读取到的可能是后来修改过的文件。

## 会话树怎样支持临时探索

Armin 用[分支处理临时任务后回到主线](https://lucumr.pocoo.org/2026/1/31/pi/)说明会话树的用途。它为“为什么需要 branch，而不只有线性历史”提供了具体工作流。[I: I-001]

在本版本中，可以从已有 entry 开始一条支线，处理工具或调查问题，再选择回到较早 leaf；`branchWithSummary()` 可以追加支线摘要。原支线记录仍保留，下一次请求使用重新选出的分支。如果支线修改了文件，回到旧 leaf 后文件仍是修改后的状态。会话树控制对话视图，文件版本仍需独立管理。[S: S-008]

## Resume 怎样构建上下文

读取 JSONL 后，`buildSessionContext()` 从 leaf 沿 parent 链向上找到分支，恢复 model/thinking 设置。若有 compaction，选取最新摘要、保留片段和之后的消息，再把 entries 映射为应用消息。普通扩展 custom entry 不进入模型上下文。[S: S-008, S-022]

历史 `R-003/R-004` 在两个独立进程中创建并恢复同一 session，第二个进程在未重发 token 的提示中返回 `PI_RESUME_2718`。本次 `X-006` 另外验证会话树和 compaction-aware context 的进程内构建。[R: R-003, R-004; X: X-006]

## 非法文件如何处理

解析器跳过不能解析的行，再检查 session header。打开非空且不构成有效 session 的文件时，manager 抛出错误并保留内容；打开空文件时，可以写入新的 header。这些是具体的加载规则，不能推出任意中段损坏都能正确恢复 parent chain。[S: S-008, S-020]

本次 `X-009` 的五项进程内用例通过。CLI 用例首次因临时副本缺少 tsx 加载配置而在模块解析阶段失败；补上开发入口对应的加载方式后，`X-010` 验证友好报错与原文件保持不变。[X: X-009, X-010]

源码：[SessionManager](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/session-manager.ts#L788)、[_persist](https://github.com/earendil-works/pi/blob/818d67457cdd6b60bce6b121d16b23141c252dd8/packages/coding-agent/src/core/session-manager.ts#L946)。
