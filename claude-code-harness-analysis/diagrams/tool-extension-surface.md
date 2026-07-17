# Tool And Extension Surface

Capability registration, authorization, execution, and result return.

~~~mermaid
flowchart LR
  %% Tool And Extension Surface
  classDef observed fill:#E8F5E9,stroke:#2E7D32,color:#14261A,stroke-width:2px;
  classDef staticOnly fill:#F8FAFC,stroke:#64748B,color:#1E293B,stroke-width:1.5px;
  classDef inferred fill:#FFF7ED,stroke:#B45309,color:#431407,stroke-width:1.5px;
  classDef conflicted fill:#FEF2F2,stroke:#B91C1C,color:#450A0A,stroke-width:2.5px;
  classDef unknown fill:#F8FAFC,stroke:#94A3B8,color:#475569,stroke-width:1.5px;
  subgraph g_ade1aa6e611e["AgentLoop"]
    direction LR
    n_a0434817a984["Shared query loop<br/>AgentLoop"]
  end
  subgraph g_37d724b4dbb0["ContextBuilder"]
    direction LR
    n_bd9215348ff0["Context assembly<br/>ContextBuilder"]
  end
  subgraph g_923b6bf63120["ExecutionBackend"]
    direction LR
    n_81a313ce89fa["Shell/process backend<br/>ExecutionBackend"]
  end
  subgraph g_16114fbee91b["Hook"]
    direction LR
    n_9b238fc5ebe1["Hooks<br/>Hook"]
  end
  subgraph g_2d691fe4fbf9["MCPServer"]
    direction LR
    n_f511c0b08c07["MCP tools<br/>MCPServer"]
  end
  subgraph g_2733a08bfa2a["ModelCall"]
    direction LR
    n_6327a3e9cdd9["Messages stream<br/>ModelCall"]
  end
  subgraph g_9f550e15f8a8["PermissionGate"]
    direction LR
    n_c3d9dc875a4e["Permission gate<br/>PermissionGate"]
  end
  subgraph g_f6c8fab0b9b5["Plugin"]
    direction LR
    n_cfe23a1db507["Plugins<br/>Plugin"]
  end
  subgraph g_90e78799ca82["PolicyRule"]
    direction LR
    n_f0e74a923b0d["Policy and modes<br/>PolicyRule"]
  end
  subgraph g_983cf61d2a4a["Sandbox"]
    direction LR
    n_443a63655f36["Sandbox runtime<br/>Sandbox"]
  end
  subgraph g_46c11a07b793["TelemetrySink"]
    direction LR
    n_ac3388b1dba8["Events and traces<br/>TelemetrySink"]
  end
  subgraph g_114eddf27d5f["Tool"]
    direction LR
    n_2e2b09fcdb36["AgentTool<br/>Tool"]
    n_86fc78b36f0b["Built-in tools<br/>Tool"]
  end
  subgraph g_8d5792bedb85["ToolRegistry"]
    direction LR
    n_26809c922930["Capability pool<br/>ToolRegistry"]
  end
  class n_a0434817a984,n_bd9215348ff0,n_81a313ce89fa,n_9b238fc5ebe1,n_f511c0b08c07,n_6327a3e9cdd9,n_c3d9dc875a4e,n_cfe23a1db507,n_f0e74a923b0d,n_443a63655f36,n_ac3388b1dba8,n_2e2b09fcdb36,n_86fc78b36f0b,n_26809c922930 staticOnly;
  n_86fc78b36f0b -.->|"tool_result"| n_bd9215348ff0
  n_86fc78b36f0b -.->|"executes"| n_81a313ce89fa
  n_bd9215348ff0 -.->|"calls"| n_6327a3e9cdd9
  n_bd9215348ff0 -.->|"follow-up"| n_a0434817a984
  n_9b238fc5ebe1 -.->|"separate audit path"| n_81a313ce89fa
  n_f511c0b08c07 -.->|"registers"| n_26809c922930
  n_c3d9dc875a4e -.->|"authorizes"| n_86fc78b36f0b
  n_cfe23a1db507 -.->|"registers"| n_f511c0b08c07
  n_f0e74a923b0d -.->|"authorizes"| n_c3d9dc875a4e
  n_a0434817a984 -.->|"calls"| n_2e2b09fcdb36
  n_a0434817a984 -.->|"emits_trace"| n_ac3388b1dba8
  n_443a63655f36 -.->|"optional wrapper"| n_81a313ce89fa
  n_26809c922930 -.->|"registers"| n_86fc78b36f0b
  n_26809c922930 -.->|"visible schemas"| n_6327a3e9cdd9
  linkStyle 0 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 1 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 2 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 3 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 4 stroke:#B45309,stroke-width:1.5px,stroke-dasharray:2 4;
  linkStyle 5 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 6 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 7 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 8 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 9 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 10 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 11 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 12 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
  linkStyle 13 stroke:#64748B,stroke-width:1.5px,stroke-dasharray:6 4;
~~~
