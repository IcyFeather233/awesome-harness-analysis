#!/usr/bin/env python3
"""Attach attributed external reading and pinned-source checks to the analysis."""
from pathlib import Path
import json


def enrich(root: Path) -> None:
    def load_lines(name):
        return {r['id']:r for r in (json.loads(line) for line in (root/name).read_text().splitlines() if line)}
    def save_lines(name,records):
        (root/name).write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in records.values()))
    sources=json.loads((root/'evidence/external-sources.json').read_text())
    external={r['id']:r for r in sources['sources']}
    evidence=load_lines('evidence/observations.jsonl')
    claims=load_lines('evidence/claims.jsonl')
    commit=sources['target_commit']
    records=[
        ('S-025','packages/agent/src/types.ts',350,368,'AgentToolResult 把模型内容 content 与日志/界面 details 分开定义。',['C-027']),
        ('S-026','packages/ai/src/api/openai-completions.ts',1026,1088,'已检查的 OpenAI Completions 与 Anthropic 消息构造路径从 tool result 的 content 组织文本/图像，没有自动展开 details。',['C-027']),
        ('S-027','packages/coding-agent/src/core/agent-session.ts',2490,2568,'AgentSession.reload 先发 shutdown，再刷新设置、provider registry 与资源，重建 runner/tool registry，最后在绑定存在时发 session_start。',['C-028','C-004']),
        ('S-028','packages/coding-agent/src/core/settings-manager.ts',773,786,'默认 reserveTokens=16384，keepRecentTokens=20000；两者由不同 getter 提供。',['C-029']),
        ('S-029','packages/coding-agent/src/core/compaction/compaction.ts',176,437,'shouldCompact 使用窗口减 reserveTokens；findCutPoint 按 keepRecentTokens 向后估算保留量并选择合法切点，toolResult 不作为切点。',['C-029']),
        ('S-030','packages/coding-agent/src/core/tools/index.ts',83,112,'内置 ToolName/allToolNames 定义七个工具名称；SDK 默认 active set 取 read/bash/edit/write。',['C-004']),
        ('S-031','packages/ai/src/utils/retry.ts',1,102,'isRetryableAssistantError 要求 stopReason=error 且有 errorMessage；先排除配额/账单限制，再匹配临时服务或传输错误文本，不调用模型判断。',['C-009','C-020']),
        ('S-032','packages/coding-agent/src/core/settings-manager.ts',795,819,'产品层自动重试默认开启，maxRetries 默认 3，baseDelayMs 默认 2000；实际退避由 AgentSession._prepareRetry 计算。',['C-009']),
        ('S-033','packages/coding-agent/src/modes/interactive/interactive-mode.ts',2765,2813,'运行中的普通文本按 Enter 提交时显式传 streamingBehavior=steer；Alt+Enter 对应 followUp。AgentSession 按参数分流，不由 LLM 按语义分类。',['C-001','C-002']),
        ('S-034','packages/coding-agent/src/core/tools/bash.ts',395,427,'内置 bash 将非零退出码或执行超时转为异常；工具执行器捕获后生成错误 toolResult，供后续模型决策，不直接进入 AgentSession 的 assistant error 重试分类。',['C-002','C-020']),
        ('S-035','packages/coding-agent/src/core/compaction/compaction.ts',441,825,'默认压缩先按切点准备旧历史与可能存在的长任务前缀，再由模型生成结构化摘要；split turn 将历史摘要与前缀摘要合并，末尾附上代码提取的文件操作路径。',['C-029']),
        ('S-036','packages/coding-agent/src/modes/interactive/interactive-mode.ts',3990,4088,'终端将压缩期间的普通输入暂存在 compactionQueuedMessages；压缩结束后，无待重试时第一条普通输入作为 prompt，余下按类型入队，有待重试时按 steering/follow-up 类型转交。',['C-024']),
    ]
    for eid,path,start,end,summary,supports in records:
        evidence[eid]={'id':eid,'record_type':'evidence','kind':'S','summary':summary,
            'source':{'locator':f'{path}:{start}-{end}','path':path,'start_line':start,'end_line':end,
                      'url':f'https://github.com/earendil-works/pi/blob/{commit}/{path}#L{start}'},
            'supports_claims':supports,'contradicts_claims':[],
            'conditions':{'commit':commit,'review':'retry-mechanism-clarification' if eid in {'S-031','S-032'} else 'external-reading-source-check'},'confidence':'high'}
    evidence['S-026']['notes']='另见 packages/ai/src/api/anthropic-messages.ts:1054-1087；AgentLoop 把 details 保留在应用消息中，TUI tool-execution.ts:290-305 将其交给 resultRenderer。此记录未声称 details 是安全隔离区。'
    evidence['S-030']['notes']='默认 active set 定位：packages/coding-agent/src/core/sdk.ts:245-253；注册定义与启用集合分别计数。'
    evidence['S-033']['conditions']['review']='queue-selection-clarification'
    evidence['S-033']['notes']='交叉定位：interactive-mode.ts:3669-3701 的 handleFollowUp；core/keybindings.ts:103-106 的默认 Alt+Enter；packages/tui/src/keybindings.ts:119 的默认 Enter；agent-session.ts:1120-1138 的参数分流；rpc-mode.ts:418-424 的 steer/follow_up。空闲时 Alt+Enter 走普通提交，extensions 可提前处理输入。'
    evidence['S-034']['conditions']['review']='tool-versus-provider-failure-clarification'
    evidence['S-034']['conditions']['path']='default bash tool; overall run not cancelled; no extension override'
    evidence['S-034']['notes']='交叉定位：packages/agent/src/agent-loop.ts:669-710 将 execute 异常包装为 isError=true；agent-session.ts:1038-1051 检查的是最后 assistant message；utils/retry.ts:96-102 要求 stopReason=error。命令内部的重试和模型后来提出的新命令属于不同层。'
    evidence['S-035']['conditions'].update({'review':'compaction-boundary-clarification','path':'default summarization; no extension replacement','validation':'static source check'})
    evidence['S-035']['notes']='交叉定位：compaction.ts:240-437 的字符估算、合法切点和交互起点；633-714 的 previousSummary 与两组消息准备；split turn 的 turn 按用户侧输入划分，区别于低层响应轮次。摘要内容保真度未经本轮新实验验证。'
    evidence['S-036']['conditions'].update({'review':'compaction-input-queue-clarification','path':'interactive TUI ordinary input; successful compaction example','validation':'static source check'})
    evidence['S-036']['notes']='交叉定位：interactive-mode.ts:2783-2793、3669-3701 的提交拦截；3059-3095 的 compaction_end 回调。扩展命令有单独处理。AgentSession 的 agent.hasQueuedMessages() 检查属于另一层队列；本轮未新增 TUI 运行验证。'
    evidence['S-021']['notes']='交叉定位：agent-session.ts:1153-1163 在加入本次用户消息前检查；默认 prepareNextTurn 刷新模型/工具/上下文，不在每个工具批次之后执行相同压缩检查。_runAutoCompaction 返回恢复标记或 hasQueuedMessages，由外层流程继续运行；阈值预防不能消除检查间隙增长造成的 overflow。'
    documentary=[
        ('D-011','B-01','Mario 的设计回顾强调对模型上下文和交互过程的控制，并说明分离工具返回内容与界面数据。',['C-003','C-027']),
        ('D-012','B-03','Mario 用浏览器脚本和按需读取说明展示 CLI 组合方式；这是具体案例与设计立场。',['C-013']),
    ]
    for eid,bid,summary,supports in documentary:
        item=external[bid]
        evidence[eid]={'id':eid,'record_type':'evidence','kind':'D','summary':summary,
            'source':{'locator':item['url'],'url':item['url']},'supports_claims':supports,'contradicts_claims':[],
            'conditions':{'published_on':item['published_on'],'source_role':'target author’s own essay'},
            'confidence':'high','notes':'记录作者当时的立场；目标版本行为由相应 S/R/X 记录支持。'}
    interpretations=[
        ('I-001','B-02','Armin 的使用经验把扩展状态、热重载和会话分支联系为可持续修改工具的工作流。',['C-004','C-008']),
        ('I-002','B-05','Haochuan 从交互角度区分 steering 与 follow-up；本报告将其理解为两个消费时机，而非两个立即中断工具的接口。',['C-002']),
        ('I-003','B-10','Scott 的实践区分运行故障与已结束但答错；这为解释事件完成和任务验收的边界提供了使用者视角。',['C-014']),
    ]
    for eid,bid,summary,supports in interpretations:
        item=external[bid]
        evidence[eid]={'id':eid,'record_type':'evidence','kind':'I','summary':summary,
            'source':{'locator':item['url'],'url':item['url']},'supports_claims':supports,'contradicts_claims':[],
            'conditions':{'source_role':'attributed external interpretation','target_commit':commit},
            'confidence':'medium','notes':'用于说明机制的用途或阅读角度，不替代目标版本源码、运行记录或作者意图证据。'}
    new_claims=[
        ('C-027','工具返回值区分 content 和 details。当前所检查的两个 provider 序列化路径使用 content 构造模型结果，details 仍可供应用消息、持久化和 UI 使用。',['S-025','S-026','D-011'],['tools_extensions','context_assembly','observability'],'给 content/details 放入不同标记，比较真实 request envelope 与 session/UI；当前为源码检查，未新增该运行实验。'),
        ('C-028','AgentSession.reload() 刷新配置、provider 与资源并重建 extension runner/tool registry；本方法继续使用当前 sessionManager，session_start 通知受 bindings 条件控制。',['S-027'],['tools_extensions','orchestration','sessions_persistence'],'在隔离 fixture 中记录 reload 前后的 runner、active tools、session id 与事件顺序；本轮未新增动态验证。'),
        ('C-029','reserveTokens 与 keepRecentTokens 控制不同阶段：默认 16384 用于压缩触发阈值，默认 20000 用于估算保留片段；切点选择还受消息类型约束。',['S-028','S-029'],['compaction','context_assembly'],'分别改变两个配置，比较 shouldCompact 判定和 firstKeptEntryIndex；本轮按源码追踪，未声称精确 token 或质量保证。'),
    ]
    for cid,statement,eids,modules,test in new_claims:
        claims[cid]={'id':cid,'record_type':'claim','statement':statement,'scope':'v0.80.7 current AgentSession path',
            'importance':'medium','status':'supported','evidence_ids':eids,'counterevidence_ids':[],
            'confidence':'medium','conditions':{'commit':commit,'validation':'static source check'},
            'coverage_refs':modules,'falsification_test':test}
    for record in evidence.values():
        if record['id'] in {r[0] for r in records}|{r[0] for r in documentary}|{r[0] for r in interpretations}:
            for cid in record['supports_claims']:
                if record['id'] not in claims[cid]['evidence_ids']:
                    claims[cid]['evidence_ids'].append(record['id'])
    save_lines('evidence/claims.jsonl',claims)
    save_lines('evidence/observations.jsonl',evidence)
    manifest=json.loads((root/'manifest.json').read_text())
    manifest['external_reading']={'retrieved_on':'2026-10-21','catalog':'evidence/external-sources.json',
        'source_count':len(external),'relevant_sections_reviewed':15,'partial_retrieval':1,
        'target_commit_unchanged':commit,'new_runtime_experiments':0,
        'integration':'Attributed views in mechanism chapters; source-checked corrections and a separate literature guide.'}
    manifest['last_reviewed_at']='2026-10-21'
    (root/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    coverage=json.loads((root/'evidence/coverage.json').read_text())
    for module,paths in {
        'tools_extensions':['packages/agent/src/types.ts','packages/coding-agent/src/core/agent-session.ts'],
        'context_assembly':['packages/ai/src/api/openai-completions.ts','packages/ai/src/api/anthropic-messages.ts'],
        'compaction':['packages/coding-agent/src/core/settings-manager.ts','packages/coding-agent/src/core/compaction/compaction.ts'],
    }.items():
        coverage['modules'][module]['files']=list(dict.fromkeys(coverage['modules'][module]['files']+paths))
    coverage['global']['external_reading_catalog']='evidence/external-sources.json'
    (root/'evidence/coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2)+'\n')
    from enrich_model_input import enrich as enrich_model_input
    enrich_model_input(root)


if __name__=='__main__':
    enrich(Path(__file__).resolve().parent.parent)
