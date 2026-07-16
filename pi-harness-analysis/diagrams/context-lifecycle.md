# Context Lifecycle

Sources and transformations that construct model context.

~~~mermaid
flowchart LR
  %% Context Lifecycle
  classDef observed fill:#E8F5E9,stroke:#2E7D32,color:#14261A,stroke-width:2px;
  classDef staticOnly fill:#F8FAFC,stroke:#64748B,color:#1E293B,stroke-width:1.5px;
  classDef inferred fill:#FFF7ED,stroke:#B45309,color:#431407,stroke-width:1.5px;
  classDef conflicted fill:#FEF2F2,stroke:#B91C1C,color:#450A0A,stroke-width:2.5px;
  classDef unknown fill:#F8FAFC,stroke:#94A3B8,color:#475569,stroke-width:1.5px;
  subgraph g_6f6b02695648["per-turn"]
    direction LR
    n_3af45ee25e84["Context assembly<br/>ContextBuilder"]
    n_6327a3e9cdd9["Provider request<br/>ModelCall"]
  end
  subgraph g_822f47c32c4b["runtime"]
    direction LR
    n_6fad310cfe27["Live active session<br/>Session"]
    n_110ebbcc690b["Session JSONL v3<br/>SessionStore"]
  end
  subgraph g_a9e6a757bfb9["startup/lazy"]
    direction LR
    n_31daf978586a["Skills<br/>Skill"]
  end
  subgraph g_01b70bda3c0a["startup/reload"]
    direction LR
    n_eae4eb8662ed["DefaultResourceLoader<br/>ContextTransformer"]
    n_4a8a89dbc119["AGENTS/CLAUDE + SYSTEM<br/>PromptSource"]
  end
  subgraph g_f66085208601["threshold/overflow/manual"]
    direction LR
    n_2fb97928aabe["Coding Agent compaction<br/>Compactor"]
  end
  subgraph g_bc1971348603["tool-call"]
    direction LR
    n_c223520f774e["read tool<br/>Tool"]
  end
  class n_2fb97928aabe,n_3af45ee25e84,n_6327a3e9cdd9,n_6fad310cfe27,n_110ebbcc690b,n_c223520f774e observed;
  class n_eae4eb8662ed,n_4a8a89dbc119,n_31daf978586a staticOnly;
  n_2fb97928aabe -->|"summary boundary"| n_6fad310cfe27
  n_2fb97928aabe -->|"compaction entry"| n_110ebbcc690b
  n_3af45ee25e84 -->|"system/messages/tools"| n_6327a3e9cdd9
  n_4a8a89dbc119 -.->|"project instructions"| n_3af45ee25e84
  n_c223520f774e -->|"toolResult"| n_3af45ee25e84
  n_eae4eb8662ed -.->|"resources"| n_3af45ee25e84
  n_6fad310cfe27 -->|"active branch"| n_3af45ee25e84
  n_6fad310cfe27 -->|"append JSONL"| n_110ebbcc690b
  n_110ebbcc690b -->|"active branch"| n_6fad310cfe27
  n_31daf978586a -.->|"metadata/invocation"| n_3af45ee25e84
  linkStyle 0 stroke:#2E7D32,stroke-width:2px;
  linkStyle 1 stroke:#2E7D32,stroke-width:2px;
  linkStyle 2 stroke:#2E7D32,stroke-width:2px;
  linkStyle 3 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 4 stroke:#2E7D32,stroke-width:2px;
  linkStyle 5 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 6 stroke:#2E7D32,stroke-width:2px;
  linkStyle 7 stroke:#2E7D32,stroke-width:2px;
  linkStyle 8 stroke:#2E7D32,stroke-width:2px;
  linkStyle 9 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
~~~
