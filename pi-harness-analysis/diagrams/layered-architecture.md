# Layered Architecture

Responsibilities grouped by their architectural layer.

~~~mermaid
flowchart TB
  %% Layered Architecture
  classDef observed fill:#E8F5E9,stroke:#2E7D32,color:#14261A,stroke-width:2px;
  classDef staticOnly fill:#F8FAFC,stroke:#64748B,color:#1E293B,stroke-width:1.5px;
  classDef inferred fill:#FFF7ED,stroke:#B45309,color:#431407,stroke-width:1.5px;
  classDef conflicted fill:#FEF2F2,stroke:#B91C1C,color:#450A0A,stroke-width:2.5px;
  classDef unknown fill:#F8FAFC,stroke:#94A3B8,color:#475569,stroke-width:1.5px;
  subgraph g_28bc19020736["context-capability"]
    direction TB
    n_3af45ee25e84["Context assembly<br/>ContextBuilder"]
    n_eae4eb8662ed["DefaultResourceLoader<br/>ContextTransformer"]
    n_26809c922930["Unified tool registry<br/>ToolRegistry"]
  end
  subgraph g_4f094061e6a1["execution"]
    direction TB
    n_66d060a3ce72["Local bash backend<br/>ExecutionBackend"]
    n_a17ca7733626["External container / VM<br/>Sandbox"]
    n_c223520f774e["read tool<br/>Tool"]
    n_94fdf21bba59["cwd workspace<br/>Workspace"]
  end
  subgraph g_8723ff5ff3ee["governance"]
    direction TB
    n_9b238fc5ebe1["Extension hooks<br/>Hook"]
    n_1606289c70f4["Optional extension gate<br/>PermissionGate"]
    n_bfbbd360512f["Project trust<br/>PolicyRule"]
  end
  subgraph g_215bf50cac07["infrastructure"]
    direction TB
    n_fefc5c1c7ccb["pi-ai Models / ModelRegistry<br/>ModelAdapter"]
    n_6327a3e9cdd9["Provider request<br/>ModelCall"]
  end
  subgraph g_2f995d99d5f5["interface"]
    direction TB
    n_822e4631e8d0["main()<br/>Entrypoint"]
    n_d82b55feeebb["pi CLI / JSON / RPC / TUI<br/>Interface"]
  end
  subgraph g_956f59a87276["observability"]
    direction TB
    n_95a05335b894["Agent events + JSON/RPC<br/>TelemetrySink"]
  end
  subgraph g_2c174a8c5967["orchestration"]
    direction TB
    n_825e7b7c4e51["Coding Agent AgentSession<br/>AgentLoop"]
    n_546fb0dae98a["New AgentHarness<br/>AgentLoop"]
    n_1f48ee0d4fd8["runAgentLoop<br/>AgentLoop"]
    n_2fb97928aabe["Coding Agent compaction<br/>Compactor"]
    n_9021d26f0f99["agent_end / agent_settled<br/>ExitCondition"]
    n_c1d0b90b4198["Retry / overflow recovery<br/>RecoveryPolicy"]
    n_cb9c10e1a22e["AgentSessionRuntime<br/>Router"]
  end
  subgraph g_9aa3032ea548["state"]
    direction TB
    n_6fad310cfe27["Live active session<br/>Session"]
    n_110ebbcc690b["Session JSONL v3<br/>SessionStore"]
  end
  class n_825e7b7c4e51,n_546fb0dae98a,n_1f48ee0d4fd8,n_2fb97928aabe,n_3af45ee25e84,n_822e4631e8d0,n_9021d26f0f99,n_9b238fc5ebe1,n_d82b55feeebb,n_fefc5c1c7ccb,n_6327a3e9cdd9,n_c1d0b90b4198,n_cb9c10e1a22e,n_6fad310cfe27,n_110ebbcc690b,n_95a05335b894,n_c223520f774e,n_26809c922930,n_94fdf21bba59 observed;
  class n_eae4eb8662ed,n_66d060a3ce72,n_1606289c70f4,n_bfbbd360512f,n_a17ca7733626 staticOnly;
  n_546fb0dae98a -->|"direct loop"| n_1f48ee0d4fd8
  n_825e7b7c4e51 -->|"prompt/continue"| n_1f48ee0d4fd8
  n_66d060a3ce72 -.->|"local shell"| n_94fdf21bba59
  n_d82b55feeebb -->|"invoke"| n_822e4631e8d0
  n_2fb97928aabe -->|"compaction entry"| n_110ebbcc690b
  n_3af45ee25e84 -->|"system/messages/tools"| n_6327a3e9cdd9
  n_a17ca7733626 -.->|"optional routed backend"| n_66d060a3ce72
  n_9b238fc5ebe1 -->|"tool_call policy"| n_1606289c70f4
  n_1f48ee0d4fd8 -->|"convert before request"| n_3af45ee25e84
  n_1f48ee0d4fd8 -->|"dispatch"| n_c223520f774e
  n_822e4631e8d0 -->|"create runtime"| n_cb9c10e1a22e
  n_fefc5c1c7ccb -->|"auth + dispatch"| n_6327a3e9cdd9
  n_1606289c70f4 -.->|"allow/block"| n_c223520f774e
  n_bfbbd360512f -.->|"load project resources"| n_eae4eb8662ed
  n_eae4eb8662ed -.->|"resources"| n_3af45ee25e84
  n_6fad310cfe27 -->|"append JSONL"| n_110ebbcc690b
  n_cb9c10e1a22e -->|"own/rebind"| n_825e7b7c4e51
  n_26809c922930 -->|"active tool"| n_c223520f774e
  linkStyle 0 stroke:#2E7D32,stroke-width:2px;
  linkStyle 1 stroke:#2E7D32,stroke-width:2px;
  linkStyle 2 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 3 stroke:#2E7D32,stroke-width:2px;
  linkStyle 4 stroke:#2E7D32,stroke-width:2px;
  linkStyle 5 stroke:#2E7D32,stroke-width:2px;
  linkStyle 6 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 7 stroke:#2E7D32,stroke-width:2px;
  linkStyle 8 stroke:#2E7D32,stroke-width:2px;
  linkStyle 9 stroke:#2E7D32,stroke-width:2px;
  linkStyle 10 stroke:#2E7D32,stroke-width:2px;
  linkStyle 11 stroke:#2E7D32,stroke-width:2px;
  linkStyle 12 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 13 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 14 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 15 stroke:#2E7D32,stroke-width:2px;
  linkStyle 16 stroke:#2E7D32,stroke-width:2px;
  linkStyle 17 stroke:#2E7D32,stroke-width:2px;
~~~
