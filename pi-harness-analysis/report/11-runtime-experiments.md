# 实验记录

本报告保留两批证据：2026 年 7 月的真实 SiFlow 场景和首次定向测试，以及 2026-10-20 的源码复核与本地 mock/faux 检查。本次没有调用外部模型。

## 历史真实模型场景

| 场景 | 实际观察 | 记录 |
|---|---|---|
| R-001 文本 | 一轮 assistant，无工具，最终 settled | [normalized trace](../traces/normalized/R-001-text-only.normalized.jsonl) |
| R-002 read | 两轮模型处理，一次 read，最终返回合成值 314159 | [normalized trace](../traces/normalized/R-002-read-tool.normalized.jsonl) |
| R-003 创建会话 | 记录合成 token 并写入 session | [normalized trace](../traces/normalized/R-003-session-create.normalized.jsonl) |
| R-004 恢复会话 | 独立新进程在未重发 token 时返回 PI_RESUME_2718 | [normalized trace](../traces/normalized/R-004-session-resume.normalized.jsonl) |

另有 R-005 的模型发现记录，以及当前路径的旧 X-001/X-003 的 39、31 项定向测试。原命令与环境摘要保存在 [runtime-tests.md](../runtime-tests.md)。这些数字属于历史执行，不合并成此次新测试的通过数。

## 本次定向检查

下表直接对应保存的 Vitest 结果。通过、失败和跳过分别列出；只用执行通过的具体断言支持行为结论。

| 检查 | 通过 | 失败 | 跳过 | 内容与产物 |
|---|---:|---:|---:|---|
| X-004 | 39 | 0 | 0 | [Agent 与低层 loop](../traces/checks/20261020/X-004.vitest.json) |
| X-005 | 12 | 0 | 5 | [产品事件、动态工具、重试、压缩后队列](../traces/checks/20261020/X-005.vitest.json) |
| X-006 | 46 | 1 | 0 | [session context/tree 与首次 CLI 尝试](../traces/checks/20261020/X-006.vitest.json) |
| X-008 | 15 | 0 | 0 | [faux compaction 与发送前压缩](../traces/checks/20261020-followup/X-008.vitest.json) |
| X-009 | 5 | 0 | 16 | [setSessionFile 名称筛选](../traces/checks/20261020-followup/X-009.vitest.json) |
| X-010 | 1 | 0 | 0 | [CLI + tsx 对照](../traces/checks/20261020-cli/X-010.vitest.json) |

核心循环组重新验证 loop、工具排序、hook 和队列。产品层组检查异步 `message_end` 的记录顺序、动态工具、重试和压缩后队列。持久化组检查 context projection 与分支树。补充组检查当前产品压缩条件、非法文件处理与 CLI 错误呈现。

## 一次失败怎样定位

X-006 中的 46 项进程内检查通过，CLI 用例在子进程解析模块时退出，尚未进入被测的 session 文件校验路径。该测试直接以 Node 启动 `cli.ts`，临时运行环境最初没有配上 Pi 开发入口使用的 tsx/tsconfig 加载方式。

X-009 先单独验证 `SessionManager.setSessionFile`：空文件初始化、非法非空文件拒绝与内容保留均通过。X-010 再给 CLI 用例补上 tsx 加载环境，验证友好错误和原文件不变，结果通过。原 X-006 记录保持失败状态，后续成功记录没有覆盖它。

## 跳过项与运行边界

X-005 的五项真实模型 compaction e2e 因没有凭据而跳过，不能算作压缩验证；相应 controller 行为使用 X-008 的 faux 测试补充。X-009 通过名称筛选只运行五项文件校验用例，其余十六项未选用。

当前范围选用 118 个 passed、1 个 failed、21 个 skipped 的测试条目，其中 CLI 的同一断言先失败后单独通过。这里统计的是当前路径的执行记录。范围外的历史测试仍保存在原始结果与 [runtime-tests.md](../runtime-tests.md)，不计入本表。摘要信息保存在各批次的 `summary.json`，执行脚本见[复现方法](13-coverage-reproducibility.md)。
