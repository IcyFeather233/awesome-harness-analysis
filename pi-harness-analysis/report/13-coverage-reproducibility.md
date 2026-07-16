# 13 覆盖与复现

## 产物

- 固定配置：[manifest.json](../manifest.json)
- 仓库 inventory：[inventory.json](../inventory.json)
- HIR：[hir.json](../hir.json)
- Claims：[claims.jsonl](../evidence/claims.jsonl)
- Evidence：[observations.jsonl](../evidence/observations.jsonl)
- Coverage：[coverage.json](../evidence/coverage.json)
- Scenarios：[catalog.json](../scenarios/catalog.json)
- Raw traces：`traces/raw/`
- Redacted normalized traces：`traces/normalized/`
- Diagram sources/SVG/metadata：`diagrams/`
- Narrative story spec：[story-specs.json](../diagrams/story-specs.json)
- Narrative SVG/metadata：`diagrams/narrative/`

## 关键复现命令

```bash
# 归一化 synthetic traces
python3 reproduce/normalize_pi_trace.py   traces/raw/R-002-read-tool.jsonl   traces/normalized/R-002-read-tool.normalized.jsonl   --scenario-id R-SCENARIO-002

# 重建 structured evidence/HIR
python3 reproduce/compile_analysis.py

# 严格校验
python3 ../harness-analysis/scripts/validate_analysis.py . --strict

# 重渲染图
python3 ../harness-analysis/scripts/render_diagrams.py .

# 重渲染正文叙事图，并校验 HIR/claim/evidence 引用
python3 ../harness-analysis/scripts/render_story_diagrams.py .

# 重写报告
python3 reproduce/compile_report.py

# 检查 Markdown links、SVG accessibility、正文图密度与元数据
python3 ../harness-analysis/scripts/audit_outputs.py . --strict
```

## 验证结果

- Analysis validator：`0 errors, 0 warnings`
- XML parse：8/8 技术 SVG + 5/5 叙事 SVG valid
- Output audit：Markdown links、report-facing SVG 与 narrative metadata 通过 strict
- Diagram density：overview 16 nodes；turn 11；context 9；permission 11；subagent 10；persistence 7
- Narrative density：system 12 nodes；observed turn 12；context 8；extension 11；design space 12
- Tests：39 + 61 + 31 = 131 passed
- Target `git status --short`：clean（依赖目录被 gitignore，不改变固定源码）

## Coverage statement

源码 inventory 共 1021 files，未达到 file/size scan limit。14 模块均有记录；partial 模块与 unresolved 条目不会被“未发现”等价成“不存在”。Runtime coverage 只代表 Linux/Node/JSON-mode/SiFlow 与命名 faux-provider tests。
