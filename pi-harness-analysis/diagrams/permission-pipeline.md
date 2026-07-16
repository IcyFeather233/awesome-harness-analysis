# Permission Pipeline

Policy decisions and trust boundaries before side effects.

~~~mermaid
flowchart LR
  %% Permission Pipeline
  classDef observed fill:#E8F5E9,stroke:#2E7D32,color:#14261A,stroke-width:2px;
  classDef staticOnly fill:#F8FAFC,stroke:#64748B,color:#1E293B,stroke-width:1.5px;
  classDef inferred fill:#FFF7ED,stroke:#B45309,color:#431407,stroke-width:1.5px;
  classDef conflicted fill:#FEF2F2,stroke:#B91C1C,color:#450A0A,stroke-width:2.5px;
  classDef unknown fill:#F8FAFC,stroke:#94A3B8,color:#475569,stroke-width:1.5px;
  subgraph g_562e8626af22["external"]
    direction LR
    n_a17ca7733626["External container / VM<br/>Sandbox"]
  end
  subgraph g_2f012c904bef["host"]
    direction LR
    n_66d060a3ce72["Local bash backend<br/>ExecutionBackend"]
    n_94fdf21bba59["cwd workspace<br/>Workspace"]
  end
  subgraph g_49c26ae2b967["process"]
    direction LR
    n_825e7b7c4e51["Coding Agent AgentSession<br/>AgentLoop"]
    n_546fb0dae98a["New AgentHarness<br/>AgentLoop"]
    n_1f48ee0d4fd8["runAgentLoop<br/>AgentLoop"]
    n_9b238fc5ebe1["Extension hooks<br/>Hook"]
    n_1606289c70f4["Optional extension gate<br/>PermissionGate"]
    n_cb9c10e1a22e["AgentSessionRuntime<br/>Router"]
    n_95a05335b894["Agent events + JSON/RPC<br/>TelemetrySink"]
    n_c223520f774e["read tool<br/>Tool"]
  end
  class n_825e7b7c4e51,n_546fb0dae98a,n_1f48ee0d4fd8,n_9b238fc5ebe1,n_cb9c10e1a22e,n_95a05335b894,n_c223520f774e,n_94fdf21bba59 observed;
  class n_66d060a3ce72,n_1606289c70f4,n_a17ca7733626 staticOnly;
  n_546fb0dae98a -->|"direct loop"| n_1f48ee0d4fd8
  n_825e7b7c4e51 -->|"prompt/continue"| n_1f48ee0d4fd8
  n_66d060a3ce72 -.->|"local shell"| n_94fdf21bba59
  n_a17ca7733626 -.->|"optional routed backend"| n_66d060a3ce72
  n_9b238fc5ebe1 -->|"tool_call policy"| n_1606289c70f4
  n_1f48ee0d4fd8 -->|"lifecycle events"| n_95a05335b894
  n_1f48ee0d4fd8 -->|"dispatch"| n_c223520f774e
  n_1606289c70f4 -.->|"allow/block"| n_c223520f774e
  n_c223520f774e -->|"fixture.txt"| n_94fdf21bba59
  n_cb9c10e1a22e -->|"own/rebind"| n_825e7b7c4e51
  linkStyle 0 stroke:#2E7D32,stroke-width:2px;
  linkStyle 1 stroke:#2E7D32,stroke-width:2px;
  linkStyle 2 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 3 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 4 stroke:#2E7D32,stroke-width:2px;
  linkStyle 5 stroke:#2E7D32,stroke-width:2px;
  linkStyle 6 stroke:#2E7D32,stroke-width:2px;
  linkStyle 7 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 8 stroke:#2E7D32,stroke-width:2px;
  linkStyle 9 stroke:#2E7D32,stroke-width:2px;
~~~
