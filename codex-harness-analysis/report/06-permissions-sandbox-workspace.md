# 权限、Sandbox 与 Workspace

![Codex permission pipeline](../diagrams/generated/codex-permission-pipeline.png)

> 图 5（gpt-image-2 读者插图）：三分支明确区分 allow 直达 sandbox、ask 经 User Approval，以及 deny；红色拒绝支路是 `X-SCENARIO-004` 实际发生路径，sandbox backend 未执行。Evidence: `D-002`, `S-012`–`S-014`, `X-004`, `X-007`, `I-002`。

<!-- EXPLANATION:permission-figure -->
## 图 5 的三条分支

`Exec Policy` 不是 sandbox，它先回答“是否允许进入执行阶段”：

- `allow`：规则和 mode 已足以授权，不弹用户确认，直接进入 `Platform Sandbox`。
- `ask`：需要 `User Approval`；`Session cache` 只可能复用同一 session 中明确批准的 decision，然后同样进入 sandbox。
- `NEVER + escalation`：当前 policy 明确不允许询问提权，直接产生 `Tool error to model`；图中的 `OBSERVED` 只标记这条本轮实验路径。

两个 allow/ask 分支汇合后，`Filesystem profile` 和 `Network profile` 决定 sandbox 给 process 的实际能力，`Process` 才可能读取/写入 `Workspace`。所以“允许命令”不等于“无限制执行”，“用户批准”也不等于“关闭 sandbox”。[S: `S-012`–`S-014`] [X: `X-004`, `X-007`]

## 决策层

`ExecPolicy` 先把复合命令拆成 segments，综合 rules 与 fallback。只有每个 segment 都显式 allow 才能绕过额外 sandbox 决策；危险/未知命令在不同 approval mode 下会 forbid、prompt 或依赖 sandbox。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/exec_policy.rs#L169) [S: `S-012`]

`AskForApproval` 包含 `UnlessTrusted`、`OnRequest`、`Granular`、`Never`。session approval cache 只复用明确的 `ApprovedForSession`，并不是把一次批准变成全局 allow。[S: `S-013`]

## 执行层

通过 policy 后，`SandboxManager` 将 filesystem/network permission profile 转换为平台执行后端：Linux、macOS、Windows 有不同 transform 与 fallback。[源码](https://github.com/openai/codex/blob/87db9bc18ba5bc82c1cb4e4381b44f693ee35623/codex-rs/core/src/exec.rs#L117) [D: `D-002`] [S: `S-014`]

因此可审计边界是组合关系：policy 决定是否允许/询问/拒绝，sandbox 限制获准执行能触达什么。[I: `I-002`] 把二者任意一个画成“唯一安全层”都会丢失真实语义。

## 特殊治理路径：apply_patch 不是普通进程 exec

源码复核发现，shell 与 unified-exec handler 会先调用 `intercept_apply_patch`；若输入确实是 patch，它在创建普通 command 的 exec-policy requirement 之前转入 `ApplyPatchRuntime`。该 runtime 仍执行 patch safety assessment、按文件路径生成 approval keys、复用 session approval cache，并作为 sandboxable runtime 落地文件变更；它不是“跳过治理直接 spawn”。[S: `S-028`] [C: `C-024`]

| Tool 输入族 | 进入副作用前的主要路径 | 当前证据能证明什么 | 不能泛化的结论 |
|---|---|---|---|
| 普通 shell/exec command | Escalation mode guard → ExecPolicy decision → optional user approval/cache → permission profile/sandbox transform → process。 | `never + require_escalated` 在本实验中先于进程创建被拒绝。 | 不能据此覆盖 apply_patch、MCP、dynamic host tool 或 startup side effects。 |
| `apply_patch`（直接 tool 或 shell interception） | Patch parse/safety → per-path approval requirement/cache → ApplyPatchRuntime → sandboxed file mutation。 | 源码证明它有独立治理链，并非普通 command policy chain。 | 尚未运行三入口 differential scenario，不能宣称所有入口事件序列完全等价。 |
| MCP / dynamic / extension tool | 各自 handler 与 host callback，是否复用 exec/sandbox 取决于具体实现。 | Registry/router 和 handler source 已覆盖。 | “工具都经过同一个 ExecPolicy”不成立为已证明的 universal claim。 |

## 反例实验

fixture 请求 `touch forbidden-marker` 且显式 `sandbox_permissions=require_escalated`，配置为 `approval_policy=never`。router 返回 “you cannot ask for escalated permissions if the approval policy is Never”；随后 fixture 只有收到 tool output 才结束。运行前后 `FACTS.txt` SHA-256 都是 `277992...8ed`，目录仍只有 `FACTS.txt`。[X: `X-004`, `X-007`]

这证明 **never+require_escalated 的前置拒绝**，但没有证明 read-only sandbox 能阻挡所有绕行，也没有覆盖 MCP/dynamic tool 是否共享相同 exec gate。
