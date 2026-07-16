# 范围与方法

## 冻结快照

- Repository: `openai/codex`
- Annotated tag: `rust-v0.144.5`（tag object `efea0e66996d4e7f4f805f3df32a169d327f2f73`）
- Peeled commit: `87db9bc18ba5bc82c1cb4e4381b44f693ee35623`
- Source worktree: clean，分析后 `git status --short` 为空
- Official release binary: `codex-cli 0.144.5`
- Host: Linux；宿主没有 `rustc`/`cargo`/`just`

因此，本轮没有用另一个工具链重编译 target，也没有修改 Codex 源码。动态实验使用官方 release binary；确定性分支由本地 Responses SSE fixture 驱动。

## 证据规则

- `D`: 仓库文档/README/AGENTS 直接声明。
- `S`: 固定 commit 的源码结构与潜在路径。
- `R`: 官方 binary 对真实 SiFlow endpoint 的实际运行。
- `X`: 受控 scripted model、权限拒绝、文件哈希或 resume 实验。
- `I`: 基于多条证据的分析者综合，不代表作者动机。

运行观察只能证明“在命名配置下发生过”。静态存在也不能证明生产启用频率。完整记录见 [manifest](../manifest.json)、[coverage](../evidence/coverage.json)、[scenarios](../scenarios/catalog.json)。

## 配置与安全

测试使用独立 `/tmp/codex-analysis-home` 与 `/tmp/codex-analysis-workspace`，默认 `approval_policy=never`、`sandbox_mode=read-only`、memories/V1/V2 multi-agent 关闭；subagent 场景只临时启用 V1。真实网络只访问用户明确授权的 SiFlow endpoint；fixture 只监听 `127.0.0.1`。凭据没有写入 bundle，provider request 只保留 item type、role、tool name 与内容哈希。

## 主要限制

没有 Rust toolchain，因此未运行仓库 `just test`；没有动态触发 compaction、MCP、OTel exporter、真实 sandbox backend、V2 multi-agent、memory consolidation、fork/corrupt rollout。真实 SiFlow 也无法完整接收 stock Codex 请求方言，详见运行实验。
