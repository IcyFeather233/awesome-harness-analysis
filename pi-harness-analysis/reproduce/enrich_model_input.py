"""Record the API-to-model boundary without treating external templates as Pi code."""
import json
from pathlib import Path


def enrich(root: Path) -> None:
    def load(name):
        return {row['id']: row for row in map(json.loads, (root / name).read_text().splitlines())}

    evidence = load('evidence/observations.jsonl')
    claims = load('evidence/claims.jsonl')
    commit = '818d67457cdd6b60bce6b121d16b23141c252dd8'
    records = [
        ('S-037', 'S', 'https://github.com/earendil-works/pi/blob/' + commit + '/packages/ai/src/api/openai-completions.ts#L878',
         'Pi 的 OpenAI Completions 适配器将 systemPrompt 按兼容配置转为 system/developer 消息，将工具 name/description/parameters 放入独立 tools 字段。',
         {'commit': commit, 'scope': 'Pi openai-completions adapter; not all compat dispatch branches'},
         '另见 agent-loop.ts:287-304 的 Context 组装；openai-completions.ts:588-595、1101-1117 的工具序列化。未对所有模型配置执行请求捕获。'),
        ('S-038', 'S', 'https://huggingface.co/Qwen/Qwen3.8-27B/blob/main/chat_template.jinja',
         '查阅的 Qwen3.8-27B 模板将工具 schema 与调用格式说明写入 system 段，再接应用 system 文本；用 im_start/im_end 分隔消息，工具调用使用 XML 风格，tool 结果包装为 user 段的 tool_response。',
         {'scope': 'External Qwen3.8-27B template, main as reviewed 2026-10-21', 'runtime_validation': False},
         '相关源码段：44-85、101-169。思考开关和 effort 改变指令及生成前缀。不是 Pi 固定提交内的实现，也不是 Qwen 云端请求抓包。'),
        ('S-039', 'S', 'https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash/blob/main/encoding/encoding_dsv4.py',
         'DeepSeek V4 Flash 参考编码器将 system 内容与工具 schema 写入输入前部，用专有角色标记组织序列；DSML 表达工具调用，工具结果预处理为 user 内容中的 tool_result，再解析生成内容回结构化消息。',
         {'scope': 'External DeepSeek-V4-Flash public reference encoder, main as reviewed 2026-10-21', 'runtime_validation': False},
         '相关源码段：38-86、203-359、364-521、573-676；另见同仓库 encoding/README.md。编码器 tools 挂在消息上，其输入结构不等于 HTTP API 字段布局。'),
        ('D-013', 'D', 'https://huggingface.co/docs/transformers/main/en/chat_templating',
         'Transformers 官方文档说明聊天消息由模型对应模板转换为带控制标记的序列，再分词为 token 输入；不同模型可以使用不同对话格式。',
         {'scope': 'General text-chat encoding documentation', 'reviewed_on': '2026-10-21'},
         '生成机制另见 https://huggingface.co/docs/transformers/main/en/llm_tutorial；外部执行工具的 API 示例见 https://api-docs.deepseek.com/guides/tool_calls/。'),
    ]
    for eid, kind, url, summary, conditions, notes in records:
        evidence[eid] = {'id': eid, 'record_type': 'evidence', 'kind': kind,
                         'summary': summary, 'source': {'locator': url, 'url': url},
                         'supports_claims': ['C-030'], 'contradicts_claims': [],
                         'conditions': conditions, 'confidence': 'high', 'notes': notes}
    claims['C-030'] = {
        'id': 'C-030', 'record_type': 'claim',
        'statement': 'Pi 的请求适配与服务端的模型输入编码是不同阶段：前者组织 API 字段，后者可按模型模板将角色、内容和工具说明编码为 token 序列。所查 Qwen3.8-27B 与 DeepSeek V4 Flash 公开源码展示了不同的角色标记和工具调用格式。',
        'scope': 'Pinned Pi openai-completions adapter plus separately dated external template examples',
        'importance': 'medium', 'status': 'supported',
        'evidence_ids': ['S-001', 'S-037', 'S-038', 'S-039', 'D-013'], 'counterevidence_ids': [],
        'confidence': 'high',
        'conditions': {'validation': 'static source and documentation reading only',
                       'pi_commit': commit, 'external_reviewed_on': '2026-10-21',
                       'external_source_catalog': 'evidence/model-input-sources.json'},
        'coverage_refs': ['model_abstraction', 'context_assembly'],
        'falsification_test': 'Capture a configured Pi request and compare a server-rendered prompt against a fixed model template and tokenizer. This end-to-end model integration was not run in this update.'
    }
    for name, records_by_id in [('evidence/observations.jsonl', evidence), ('evidence/claims.jsonl', claims)]:
        (root / name).write_text(''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in records_by_id.values()))
    manifest_path = root / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['model_input_review'] = {
        'reviewed_on': '2026-10-21', 'source_catalog': 'evidence/model-input-sources.json',
        'chapter': 'report/18-model-input-encoding.md', 'new_runtime_experiments': 0,
        'scope': 'Pi request adapter and separately reviewed external model input formats'
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
