# 覆盖与复现

报告的结论由固定源码、历史 trace 和本次测试记录支持。当前 HIR 含 28 个 nodes、34 条 edges；正文采用 28 条 claims 和 65 条 evidence records，其余历史记录标记为范围外。计数用于核对产物，不表示代码覆盖率。

## 从哪里查证

| 产物 | 用途 |
|---|---|
| [manifest](../manifest.json) 与 [analysis brief](../analysis-brief.json) | 固定版本、历史/本次执行范围和待解释问题 |
| [claims](../evidence/claims.jsonl) 与 [observations](../evidence/observations.jsonl) | 结论、依据、条件和反例检查 |
| [coverage](../evidence/coverage.json) | 14 个模块的具体检查范围与剩余未知项 |
| [外部来源目录](../evidence/external-sources.json) | 16 篇页面的作者、版本、阅读状态与采用方式 |
| [模型输入来源](../evidence/model-input-sources.json) | 外部模板和编码器的查阅范围；未执行模型或抓取云端 prompt |
| [HIR](../hir.json) | 组件、关系和证据标记 |
| [scenario catalog](../scenarios/catalog.json) | 历史和新增检查的配置、结果与 artifact |
| [20261020](../traces/checks/20261020/summary.json)、[followup](../traces/checks/20261020-followup/summary.json)、[CLI](../traces/checks/20261020-cli/summary.json) | 本次逐组命令、时间、通过/失败记录 |

## 本次覆盖的机制

主线从 CLI/SDK session 构建到 AgentSession、Agent、低层循环、模型与工具边界，再到会话记录。新增阅读集中在 compat 分派、事件等待、工具 preflight、next-turn 刷新、压缩条件和首次文件写入。Subagent、orchestrator 与外部隔离作为静态旁支记录。

动态覆盖采用本地 mock/faux/controller 测试；原来的真实 JSON-mode 文本、read、resume 证据保留。TUI/RPC 的完整交互、真实长上下文、OS 崩溃、并发 child 文件竞争和容器/VM backend 不在本次运行覆盖内。

## 复现定向测试

需要固定 commit 的 Pi checkout、它的依赖和 Node 22.19.0。脚本检查 commit，将源码导出到临时目录，使用已安装依赖，关闭测试缓存并使用独立 agent 配置；不会安装包或调用外部模型。

```bash
python3 pi-harness-analysis/reproduce/run_mechanism_checks.py   --repo /path/to/pi   --node /path/to/node   --output /tmp/pi-mechanism-results   --group X-004 --group X-008 --group X-009 --group X-010
```

`--output` 必须为空，以免覆盖既有记录。`--group X-005` 可复现产品层组及其五个 e2e 跳过项；`--group X-006` 保留原未加载 tsx 的诊断配置，CLI 子项可能在模块解析时失败。X-010 是相应的加载器对照组。各组具体文件清单在脚本和 summary 中。

Node 官方归档 URL 与 SHA-256 保存在[运行时来源](../traces/checks/node-runtime-provenance.json)。依赖 lockfile hash 在每批 summary 中；这些记录不包含模型凭据。

## 重建分析产物与报告

```bash
python3 pi-harness-analysis/reproduce/compile_analysis.py
python3 pi-harness-analysis/reproduce/compile_report.py
python3 /path/to/harness-analysis-skill/scripts/render_diagrams.py pi-harness-analysis
python3 /path/to/harness-analysis-skill/scripts/validate_analysis.py pi-harness-analysis --strict
python3 /path/to/harness-analysis-skill/scripts/audit_outputs.py pi-harness-analysis --strict
```

`compile_analysis.py` 先构建历史记录，再应用本次源码复核及已保存测试结果；它不会重新运行实验。`compile_report.py` 写入此次维护的正文，并从当前 claims/evidence 生成索引。当前正文使用 6 张经复核的插图；图片、提示词、生成参数与审核状态见[插图记录](../diagrams/generated/README.md)。图片与机制说明使用同一组证据。
