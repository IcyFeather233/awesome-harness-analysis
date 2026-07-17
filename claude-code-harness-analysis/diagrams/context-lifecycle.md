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
  subgraph g_bdc5a739b21f["Ungrouped"]
    direction LR
    n_110ebbcc690b["Transcript JSONL<br/>SessionStore"]
  end
  subgraph g_6f6b02695648["per-turn"]
    direction LR
    n_bd9215348ff0["Context assembly<br/>ContextBuilder"]
    n_d9b8a40d18ab["Runtime attachments<br/>ContextTransformer"]
    n_6327a3e9cdd9["Messages stream<br/>ModelCall"]
  end
  subgraph g_a9e6a757bfb9["startup/lazy"]
    direction LR
    n_3dc2f841a9b3["CLAUDE.md + rules<br/>PromptSource"]
    n_31daf978586a["Skills<br/>Skill"]
  end
  subgraph g_01b70bda3c0a["startup/reload"]
    direction LR
    n_c0e68bae1418["System prompt<br/>PromptSource"]
  end
  subgraph g_f66085208601["threshold/overflow/manual"]
    direction LR
    n_2fb97928aabe["Compaction pipeline<br/>Compactor"]
  end
  subgraph g_bc1971348603["tool-call"]
    direction LR
    n_86fc78b36f0b["Built-in tools<br/>Tool"]
  end
  class n_2fb97928aabe,n_bd9215348ff0,n_d9b8a40d18ab,n_6327a3e9cdd9,n_3dc2f841a9b3,n_c0e68bae1418,n_110ebbcc690b,n_31daf978586a,n_86fc78b36f0b staticOnly;
  n_d9b8a40d18ab -.->|"injects"| n_bd9215348ff0
  n_86fc78b36f0b -.->|"tool_result"| n_bd9215348ff0
  n_3dc2f841a9b3 -.->|"injects"| n_bd9215348ff0
  n_2fb97928aabe -.->|"compacts"| n_bd9215348ff0
  n_bd9215348ff0 -.->|"calls"| n_2fb97928aabe
  n_bd9215348ff0 -.->|"calls"| n_6327a3e9cdd9
  n_110ebbcc690b -.->|"restores"| n_bd9215348ff0
  n_31daf978586a -.->|"injects"| n_bd9215348ff0
  n_c0e68bae1418 -.->|"injects"| n_bd9215348ff0
  linkStyle 0 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 1 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 2 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 3 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 4 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 5 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 6 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 7 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 8 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
~~~
