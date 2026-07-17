# Persistence Lifecycle

Transition between live state, durable state, restore, and recovery.

~~~mermaid
flowchart LR
  %% Persistence Lifecycle
  classDef observed fill:#E8F5E9,stroke:#2E7D32,color:#14261A,stroke-width:2px;
  classDef staticOnly fill:#F8FAFC,stroke:#64748B,color:#1E293B,stroke-width:1.5px;
  classDef inferred fill:#FFF7ED,stroke:#B45309,color:#431407,stroke-width:1.5px;
  classDef conflicted fill:#FEF2F2,stroke:#B91C1C,color:#450A0A,stroke-width:2.5px;
  classDef unknown fill:#F8FAFC,stroke:#94A3B8,color:#475569,stroke-width:1.5px;
  subgraph g_73a19c098361["Ungrouped"]
    direction LR
    n_2fb97928aabe["Compaction pipeline<br/>Compactor"]
    n_bd9215348ff0["Context assembly<br/>ContextBuilder"]
  end
  subgraph g_6867de3aa1a7["durable"]
    direction LR
    n_110ebbcc690b["Transcript JSONL<br/>SessionStore"]
  end
  subgraph g_736521b51165["live"]
    direction LR
    n_a0434817a984["Shared query loop<br/>AgentLoop"]
    n_9021d26f0f99["Turn/session exit<br/>ExitCondition"]
    n_8caa797d111a["Retry and recovery<br/>RecoveryPolicy"]
  end
  class n_a0434817a984,n_2fb97928aabe,n_bd9215348ff0,n_9021d26f0f99,n_8caa797d111a,n_110ebbcc690b staticOnly;
  n_2fb97928aabe -.->|"compacts"| n_bd9215348ff0
  n_9021d26f0f99 -.->|"persists"| n_110ebbcc690b
  n_a0434817a984 -.->|"exits_to"| n_9021d26f0f99
  n_a0434817a984 -.->|"persists"| n_110ebbcc690b
  n_8caa797d111a -.->|"falls_back_to"| n_2fb97928aabe
  n_110ebbcc690b -.->|"restores"| n_bd9215348ff0
  linkStyle 0 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 1 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 2 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 3 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 4 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 5 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
~~~
