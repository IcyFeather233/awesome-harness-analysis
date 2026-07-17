# Subagent Topology

Delegation, inheritance, isolation, and result aggregation.

~~~mermaid
flowchart TB
  %% Subagent Topology
  classDef observed fill:#E8F5E9,stroke:#2E7D32,color:#14261A,stroke-width:2px;
  classDef staticOnly fill:#F8FAFC,stroke:#64748B,color:#1E293B,stroke-width:1.5px;
  classDef inferred fill:#FFF7ED,stroke:#B45309,color:#431407,stroke-width:1.5px;
  classDef conflicted fill:#FEF2F2,stroke:#B91C1C,color:#450A0A,stroke-width:2.5px;
  classDef unknown fill:#F8FAFC,stroke:#94A3B8,color:#475569,stroke-width:1.5px;
  subgraph g_eecfcaab42ab["Primary"]
    direction TB
    n_a0434817a984["Shared query loop<br/>AgentLoop"]
  end
  subgraph g_0146b2da27ba["Ungrouped"]
    direction TB
    n_eeb4b33d30fe["Team mailbox<br/>Artifact"]
    n_bd9215348ff0["Context assembly<br/>ContextBuilder"]
    n_c3d9dc875a4e["Permission gate<br/>PermissionGate"]
    n_8caa797d111a["Retry and recovery<br/>RecoveryPolicy"]
    n_11dec12887d9["Tool execution router<br/>Router"]
    n_6fad310cfe27["Live session<br/>Session"]
    n_a4140d217a0c["Agent worktree<br/>Workspace"]
    n_94fdf21bba59["Current workspace<br/>Workspace"]
  end
  subgraph g_62b364fe6a4d["worker"]
    direction TB
    n_deaa5a1626b3["Agent child<br/>Subagent"]
    n_824bfa49fd13["Swarm teammate<br/>Subagent"]
  end
  class n_a0434817a984,n_eeb4b33d30fe,n_bd9215348ff0,n_c3d9dc875a4e,n_8caa797d111a,n_11dec12887d9,n_6fad310cfe27,n_deaa5a1626b3,n_824bfa49fd13,n_a4140d217a0c,n_94fdf21bba59 staticOnly;
  n_bd9215348ff0 -.->|"follow-up"| n_a0434817a984
  n_eeb4b33d30fe -.->|"unread attachment"| n_824bfa49fd13
  n_a0434817a984 -.->|"calls"| n_8caa797d111a
  n_6fad310cfe27 -.->|"calls"| n_a0434817a984
  n_6fad310cfe27 -.->|"delegates"| n_824bfa49fd13
  n_deaa5a1626b3 -.->|"recursive query"| n_a0434817a984
  n_deaa5a1626b3 -.->|"isolates_context_from"| n_a0434817a984
  n_deaa5a1626b3 -.->|"result/notification"| n_a0434817a984
  n_deaa5a1626b3 -.->|"default"| n_94fdf21bba59
  n_deaa5a1626b3 -.->|"writes"| n_a4140d217a0c
  n_824bfa49fd13 -.->|"writes"| n_eeb4b33d30fe
  n_11dec12887d9 -.->|"calls"| n_c3d9dc875a4e
  linkStyle 0 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 1 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 2 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 3 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 4 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 5 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 6 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 7 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 8 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 9 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 10 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 11 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
~~~
