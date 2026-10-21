#!/usr/bin/env python3
"""Apply the 2026-10-20 source recheck and recorded tests to the original bundle."""
from __future__ import annotations

import json
from pathlib import Path

COMMIT = "818d67457cdd6b60bce6b121d16b23141c252dd8"


def read_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def write_lines(path: Path, records: list[dict]) -> None:
    path.write_text("".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records))


def refine(root: Path) -> None:
    claims = {item["id"]: item for item in read_lines(root / "evidence/claims.jsonl")}
    evidence = {item["id"]: item for item in read_lines(root / "evidence/observations.jsonl")}
    conditions = {"commit": COMMIT, "review": "2026-10-20"}
    sources = [
        ("S-018", "packages/agent/src/agent-loop.ts", 375, 755,
         "工具开始事件先于 preflight；length、unknown、blocked 路径可返回错误而不调用 execute；整批结果都 terminate 才停止工具 follow-up。", ["C-015", "C-020", "C-021"]),
        ("S-019", "packages/coding-agent/src/core/agent-session.ts", 547, 740,
         "Agent 先处理 message_end 更新 live state，再等待 AgentSession；extension message_end 可就地替换消息，之后通知外部监听者并追加 session entry。", ["C-022"]),
        ("S-020", "packages/coding-agent/src/core/session-manager.ts", 788, 979,
         "新会话先在内存追加 entry；首次 assistant entry 触发整批写入，之后逐条追加；已有空文件和格式迁移有明确重写路径。", ["C-008", "C-023"]),
        ("S-021", "packages/coding-agent/src/core/agent-session.ts", 1890, 2161,
         "已完成 stop 响应即使 usage 越界也只压缩、不重答；错误 overflow 有一次恢复限制；threshold 后存在 queued messages 时仍继续处理队列。", ["C-009", "C-024"]),
        ("S-022", "packages/coding-agent/src/core/messages.ts", 146, 203,
         "convertToLlm 将 custom/bashExecution/summary 转为 user messages，excludeFromContext 的 bashExecution 被过滤，普通 user/assistant/toolResult 原样保留。", ["C-003", "C-025"]),
        ("S-023", "packages/coding-agent/src/core/agent-session.ts", 467, 493,
         "AgentSession 在 prepareNextTurn 阶段用当前 system prompt、tools、model 和 thinking level 刷新下一次模型请求。", ["C-004", "C-026"]),
        ("S-024", "packages/ai/src/compat.ts", 209, 287,
         "Coding Agent SDK 使用 ModelRegistry 和 compat.streamSimple；匹配内置模型且 API 未覆盖时转 compatModels，否则按 model.api 查 API registry；新 AgentHarness 直接使用 Models。", ["C-019", "C-010"]),
    ]
    for eid, path, start, end, statement, supported in sources:
        evidence[eid] = {
            "id": eid, "record_type": "evidence", "kind": "S", "summary": statement,
            "source": {"path": path, "start_line": start, "end_line": end,
                       "locator": f"{path}:{start}-{end}",
                       "url": f"https://github.com/earendil-works/pi/blob/{COMMIT}/{path}#L{start}"},
            "supports_claims": supported, "contradicts_claims": [],
            "conditions": conditions, "confidence": "high",
        }
    evidence["S-019"]["notes"] = "另见 packages/agent/src/agent.ts:525-581 的 processEvents；外部监听通知先于 SessionManager.appendMessage，因而监听回调开始时不能假设文件已更新。"
    evidence["S-024"]["notes"] = "交叉定位：packages/coding-agent/src/core/sdk.ts:301-400；packages/coding-agent/src/core/model-registry.ts:375-780；packages/agent/src/harness/agent-harness.ts:359-381。S-012 描述新 Models API，本身不覆盖当前 Coding Agent 的完整模型路径。"
    claims["C-019"].update(
        statement="Coding Agent 通过 ModelRegistry 解析模型与请求凭据，再调用 pi-ai/compat.streamSimple；compat 根据内置模型与 API 覆盖条件选择 Models 或 API registry。新 AgentHarness 直接使用 Models。",
        evidence_ids=["S-024", "S-012", "R-005", "R-001"],
        scope="v0.80.7 Coding Agent SDK and generic AgentHarness model entrypoints",
        notes="本次修订区分两代入口；历史 SiFlow 成功记录不证明所有 provider 分支均被执行。",
    )
    claims["C-015"]["statement"] = "工具默认并行；全局 sequential 或任一命中工具声明 executionMode=sequential 会使整批串行。并行结果按模型调用顺序生成 toolResult，再由 AgentSession 接入持久化。"
    claims["C-009"]["statement"] = "AgentSession 分别处理有界普通重试与自动压缩：错误 overflow 最多 compact-and-retry 一次；已完成 stop 响应的 usage 越界不重答；threshold 压缩后仍可消费排队输入。"
    new_claims = [
        ("C-021", "tool_execution_start 标记工具调用进入处理流程；unknown、hook block 与 length-stop 路径也会发出该事件，因此单靠它不能确认 handler 已执行。", ["S-018"], ["core_loop", "observability", "tools_extensions"], "构造被 block 或 length 截断的调用，同时记录 start 事件与 execute 计数；二者应可分别为 1 和 0。"),
        ("C-022", "message_end 由 Agent 先更新内存消息，再等待产品层 extension 和持久化处理；异步 extension 不应使 assistant 与对应 toolResult 的记录顺序颠倒。", ["S-019", "X-005"], ["core_loop", "sessions_persistence", "tools_extensions"], "让 assistant 的 message_end hook 等待，再检查分支消息顺序；X-005 的 settlement 回归用例已执行。"),
        ("C-023", "新建持久会话通常在首条 assistant entry 出现后才创建并写入文件；内存已有 user entry 或已分配 sessionFile 路径并不保证文件已经存在。", ["S-020", "X-006"], ["sessions_persistence", "recovery"], "从只有 user 消息的分支 fork，检查文件在 assistant 前后是否由不存在变为完整写入；X-006 的 tree-traversal 用例覆盖该路径。"),
        ("C-024", "压缩后的 continuation 取决于响应状态与队列：已完成 stop 的 overflow 不重答，threshold 后有 queued messages 时可继续处理新输入，旧边界前的 usage 不重复触发压缩。", ["S-021", "X-008", "X-005"], ["compaction", "recovery", "orchestration"], "分别构造 successful over-window、stale usage、queued input；核对 summary 调用、willRetry 和后续请求。"),
        ("C-025", "Coding Agent 的应用消息与 provider messages 不是同一集合；custom、bashExecution 和 summary 在 convertToLlm 中映射为 user，标记 excludeFromContext 的 bashExecution 被过滤。", ["S-022"], ["context_assembly", "sessions_persistence"], "对同一组含 custom、summary、普通消息及 excluded bash 的输入调用转换器，比较 provider roles 与原 session entries。"),
        ("C-026", "Coding Agent 的 active tools、system prompt、model 和 thinking level 可在 prepareNextTurn 边界更新到下一请求；registry 与 active set 分开维护。", ["S-023", "X-005"], ["tools_extensions", "context_assembly", "orchestration"], "注册或替换动态工具，检查 active set 和 prompt；请求中途刷新时机还需专门的 request diff。"),
    ]
    for cid, statement, eids, modules, test in new_claims:
        claims[cid] = {"id": cid, "record_type": "claim", "statement": statement,
                       "scope": "Pi v0.80.7 pinned mechanism recheck", "importance": "high",
                       "status": "supported", "evidence_ids": eids, "counterevidence_ids": [],
                       "confidence": "medium" if cid in {"C-021", "C-025", "C-026"} else "high",
                       "conditions": conditions, "coverage_refs": modules, "falsification_test": test}
    mappings = {
        "X-004": ["C-002", "C-015", "C-020"],
        "X-005": ["C-004", "C-009", "C-020", "C-022", "C-024", "C-026"],
        "X-006": ["C-008", "C-023"],
        "X-007": ["C-010", "C-016"],
        "X-008": ["C-009", "C-020", "C-024"],
        "X-009": ["C-008"],
        "X-010": ["C-008"],
    }
    catalog = json.loads((root / "scenarios/catalog.json").read_text())
    scenarios = {s["id"]: s for s in catalog["scenarios"]}
    runs = []
    for summary_path in sorted((root / "traces/checks").glob("*/summary.json")):
        summary = json.loads(summary_path.read_text())
        runs.append({"artifact": str(summary_path.relative_to(root)), "node": summary["node_version"],
                     "started_at": summary["started_at"], "groups": [g["evidence_id"] for g in summary["groups"]]})
        for group in summary["groups"]:
            eid = group["evidence_id"]
            result_path = summary_path.parent / group["result_file"]
            result = json.loads(result_path.read_text())
            skipped = result.get("numPendingTests", 0)
            scenario_id = "X-SCENARIO-" + eid.split("-")[1]
            message = f"2026-10-20 {group['package']} 定向测试：{group['passed']} passed，{group['failed']} failed，{skipped} skipped；exit={group['exit_code']}。"
            if eid == "X-006":
                message += "失败发生于 CLI 子进程模块解析；46 项进程内 context/tree 测试通过，后续 X-010 加载器对照单独记录。"
            if eid == "X-005":
                message += "5 项真实模型 e2e 因未提供凭据跳过；通过项包含 settlement、动态工具、网络错误重试与压缩后队列。"
            if eid == "X-009":
                message += "仅选择 setSessionFile 组，16 项未选用；5 项空文件/非法文件处理检查通过。"
            relative_result = str(result_path.relative_to(root))
            evidence[eid] = {"id": eid, "record_type": "evidence", "kind": "X",
                             "summary": message, "source": {"locator": relative_result,
                             "path": relative_result, "scenario_id": scenario_id,
                             "command": " ".join(group["command"])},
                             "supports_claims": mappings[eid], "contradicts_claims": [],
                             "conditions": {**conditions, "model_mode": "mock/faux", "node": summary["node_version"]},
                             "confidence": "high" if not group["failed"] else "medium",
                             "notes": "仅以通过的具体断言支持 claims；setup 失败、skipped 用例不构成行为验证。"}
            scenarios[scenario_id] = {"id": scenario_id, "title": f"Mechanism recheck {eid}: {group['package']}",
                "mode": "scripted", "status": "passed" if not group["exit_code"] else "partial",
                "claims_tested": mappings[eid], "configuration": {"commit": COMMIT, "node": summary["node_version"], "config": group["config"]},
                "test_files": group["test_files"], "result": {"passed": group["passed"], "failed": group["failed"], "skipped": skipped,
                "exit_code": group["exit_code"], "evidence_ids": [eid], "artifact": relative_result},
                "notes": message}
            for cid in mappings[eid]:
                if cid not in claims:
                    continue
                if eid not in claims[cid]["evidence_ids"]:
                    claims[cid]["evidence_ids"].append(eid)
    for eid, observation in evidence.items():
        if eid.startswith("S-"):
            for cid in observation["supports_claims"]:
                if cid in claims and eid not in claims[cid]["evidence_ids"]:
                    claims[cid]["evidence_ids"].append(eid)
    write_lines(root / "evidence/claims.jsonl", list(claims.values()))
    write_lines(root / "evidence/observations.jsonl", list(evidence.values()))
    write_lines(root / "evidence/conflicts.jsonl", [{
        "id": "CF-001", "record_type": "conflict", "subject_id": "C-019",
        "evidence_ids": ["S-012", "S-024"], "status": "resolved",
        "description": "旧正文将新 Models API 的描述直接用于 Coding Agent 模型路径，缺少 ModelRegistry/compat 入口及内置/自定义分派条件。",
        "resolution": "重写 C-019、模型章节和 HIR 模型适配节点；保留 Models 在 compat 内置分支及新 AgentHarness 中的实际用途。",
    }])
    catalog["scenarios"] = list(scenarios.values())
    write_json(root / "scenarios/catalog.json", catalog)
    hir = json.loads((root / "hir.json").read_text())
    for node in hir["nodes"]:
        if node["id"] == "N-Models":
            node.update(name="ModelRegistry + pi-ai/compat", summary="Coding Agent model/auth entrypoint; compat selects builtin Models or the API registry by model and override conditions.", evidence_ids=["S-024", "R-001", "R-005"])
            node["source_refs"] = [{"path": "packages/coding-agent/src/core/sdk.ts", "start_line": 301, "end_line": 400}, {"path": "packages/ai/src/compat.ts", "start_line": 209, "end_line": 287}]
        if node["id"] == "N-SessionStore":
            node["summary"] = "Parent-linked JSONL entries; new files are deferred until the first assistant entry, with explicit rewrite paths for migration and empty files."
            node["evidence_ids"] = list(dict.fromkeys(node["evidence_ids"] + ["S-020", "X-006", "X-009"]))
    for edge in hir["edges"]:
        if edge["id"] == "E-Models-Call":
            edge["evidence_ids"] = ["S-024", "R-001"]
            edge["label"] = "compat stream dispatch"
    write_json(root / "hir.json", hir)
    coverage = json.loads((root / "evidence/coverage.json").read_text())
    coverage["global"]["mechanism_recheck"] = {"date": "2026-10-20", "runs": runs,
        "scope": "同版本源码复核与本地 mock/faux 测试；保留 2026-07 的真实模型 trace，未重新调用 SiFlow。"}
    for module in coverage["modules"].values():
        module.setdefault("notes", "")
    for module_id, ids in {
        "core_loop": ["X-004", "X-005"], "compaction": ["X-008"],
        "tools_extensions": ["X-005"], "sessions_persistence": ["X-006", "X-009", "X-010"],
        "orchestration": ["X-005", "X-007"], "recovery": ["X-005", "X-008", "X-009", "X-010"],
    }.items():
        coverage["modules"][module_id]["recheck_evidence"] = ids
    write_json(root / "evidence/coverage.json", coverage)
    manifest = json.loads((root / "manifest.json").read_text())
    manifest["analysis_mode"] = "focused"
    manifest["objective"] = "解释 Pi 当前产品路径中的模型工具循环、上下文转换、事件顺序、持久化与恢复；区分新 AgentHarness。"
    manifest["last_reviewed_at"] = "2026-10-20"
    manifest["review"] = {"historical_execution": "manifest.execution and R-001..R-005 describe the July analysis",
                          "current_execution": runs, "model_api_calls": 0,
                          "source_dirty": False, "notes": "CLI 首次缺少 tsx 加载环境的失败与后续对照均保留。"}
    provenance = json.loads((root / "reproduce/review-provenance.json").read_text())
    manifest["tooling"]["review_skill_sha256"] = provenance["skill_sha256"]
    write_json(root / "manifest.json", manifest)
    write_json(root / "analysis-brief.json", {"schema_version": "1.0", "mode": "focused",
        "objective": manifest["objective"], "selected_questions": [
            "AgentSession、Agent、runAgentLoop 分别持有什么状态？",
            "工具准备、执行完成、结果回填和 session append 按什么顺序发生？",
            "应用消息怎样变为 provider messages，动态配置何时刷新？",
            "压缩、重试、排队输入如何共同决定 settled？",
            "新会话何时创建文件，branch/resume 如何选择上下文？"],
        "excluded_topics": ["最新版本迁移", "跨产品优劣排名", "成本或成功率优化实验"],
        "evidence_boundary": "新验证使用本地 mock/faux；历史真实模型记录保留原日期与配置。"})
    apply_session_scope(root)
    from enrich_external_reading import enrich
    enrich(root)


def apply_session_scope(root: Path) -> None:
    """Project the retained investigation onto the current product implementation."""
    excluded_claims = {"C-010", "C-016"}
    excluded_evidence = {"D-003", "D-008", "S-011", "X-002", "X-007"}
    excluded_scenarios = {"X-SCENARIO-002", "X-SCENARIO-007"}
    claims = read_lines(root / "evidence/claims.jsonl")
    observations = read_lines(root / "evidence/observations.jsonl")
    for record in claims:
        if record["id"] in excluded_claims:
            record.setdefault("conditions", {})["report_scope"] = "historical_only"
        if record["id"] == "C-019":
            record["statement"] = "Coding Agent 通过 ModelRegistry 解析模型与请求凭据，再调用 pi-ai/compat.streamSimple；compat 根据内置模型与 API 覆盖条件选择 Models 或 API registry。"
            record["scope"] = "v0.80.7 current Coding Agent model request path"
            record["notes"] = "当前请求入口与 compat 内部分派分开描述；历史 SiFlow 记录只验证指定端点路径。"
    for record in observations:
        if record["id"] in excluded_evidence:
            record.setdefault("conditions", {})["report_scope"] = "historical_only"
        if record["id"] == "S-024":
            record["summary"] = "Coding Agent SDK 使用 ModelRegistry 和 compat.streamSimple；匹配内置模型且 API 未覆盖时转 compatModels，否则按 model.api 查 API registry。"
            record["supports_claims"] = ["C-019"]
            record["notes"] = "交叉定位：packages/coding-agent/src/core/sdk.ts:301-400；packages/coding-agent/src/core/model-registry.ts:375-780。"
    write_lines(root / "evidence/claims.jsonl", claims)
    write_lines(root / "evidence/observations.jsonl", observations)
    conflicts = read_lines(root / "evidence/conflicts.jsonl")
    for record in conflicts:
        if record["id"] == "CF-001":
            record["resolution"] = "修正 C-019、模型章节和 HIR，分别说明 ModelRegistry/compat 入口及 compat 的内置/自定义分派条件。"
    write_lines(root / "evidence/conflicts.jsonl", conflicts)

    hir = json.loads((root / "hir.json").read_text())
    archived_nodes = [n for n in hir["nodes"] if n["id"] == "N-AgentHarness"]
    archived_edges = [e for e in hir["edges"] if e["source"] == "N-AgentHarness" or e["target"] == "N-AgentHarness"]
    archive = root / "evidence/out-of-scope.json"
    if archived_nodes or not archive.exists():
        write_json(archive, {"scope": "New AgentHarness is retained as historical evidence, outside the current AgentSession report.",
                            "claim_ids": sorted(excluded_claims), "evidence_ids": sorted(excluded_evidence),
                            "scenario_ids": sorted(excluded_scenarios), "hir_nodes": archived_nodes, "hir_edges": archived_edges})
    hir["nodes"] = [n for n in hir["nodes"] if n["id"] != "N-AgentHarness"]
    hir["edges"] = [e for e in hir["edges"] if e["source"] != "N-AgentHarness" and e["target"] != "N-AgentHarness"]
    for node in hir["nodes"]:
        if node["id"] == "N-LowLoop":
            node["summary"] = "Low-level model/tool/queue loop invoked by Agent on the current Coding Agent path."
    write_json(root / "hir.json", hir)

    coverage = json.loads((root / "evidence/coverage.json").read_text())
    for module in coverage["modules"].values():
        for field in ("files", "directories"):
            module[field] = [path for path in module.get(field, []) if "packages/agent/src/harness" not in path]
        module["scenarios"] = [sid for sid in module.get("scenarios", []) if sid not in excluded_scenarios]
        if "recheck_evidence" in module:
            module["recheck_evidence"] = [eid for eid in module["recheck_evidence"] if eid not in excluded_evidence]
        module["unresolved"] = [item for item in module.get("unresolved", []) if "AgentHarness" not in item]
    coverage["global"]["report_scope"] = "Current AgentSession, Agent, shared loop and supporting Coding Agent services"
    coverage["global"]["excluded_evidence_ids"] = sorted(excluded_evidence)
    coverage["global"]["unresolved_high_value_questions"] = [q for q in coverage["global"].get("unresolved_high_value_questions", []) if q != "Q-001"]
    write_json(root / "evidence/coverage.json", coverage)
    questions = json.loads((root / "questions.json").read_text())
    questions["questions"] = [q for q in questions["questions"] if q["id"] != "Q-001"]
    write_json(root / "questions.json", questions)
    catalog = json.loads((root / "scenarios/catalog.json").read_text())
    for scenario in catalog["scenarios"]:
        if scenario["id"] in excluded_scenarios:
            scenario["report_scope"] = "historical_only"
    write_json(root / "scenarios/catalog.json", catalog)

    objective = "解释当前 AgentSession → Agent → runAgentLoop 的代码实现，以及上下文、工具、事件、会话持久化与恢复。"
    manifest = json.loads((root / "manifest.json").read_text())
    manifest["objective"] = objective
    manifest["scope"]["report_focus"] = "current AgentSession implementation"
    manifest["presentation"] = {"primary_article": "report/index.md", "format": "explanatory blog",
                                "reference_guide": "report/reading-guide.md",
                                "approach": "Task-led narrative, terminology introduced in context, detailed evidence in linked references."}
    manifest["scope"]["excluded_from_report"] = ["packages/agent/src/harness", "new AgentHarness comparisons and migration"]
    manifest["review"]["report_test_totals"] = {"passed": 118, "failed": 1, "skipped": 21,
                                                "excluded_group_ids": ["X-007"], "note": "Scope projection of saved results; no new test run."}
    write_json(root / "manifest.json", manifest)
    brief = json.loads((root / "analysis-brief.json").read_text())
    brief["objective"] = objective
    brief["presentation"] = manifest["presentation"]
    brief["excluded_topics"].insert(0, "新 AgentHarness 的实现、对比与迁移")
    write_json(root / "analysis-brief.json", brief)


if __name__ == "__main__":
    refine(Path(__file__).resolve().parent.parent)
