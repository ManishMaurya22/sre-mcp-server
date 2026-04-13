# 🤖 SRE MCP Server — Enterprise Kubernetes via AI

> **Natural language Kubernetes operations** — powered by Model Context Protocol (MCP)  
> Built to scale from a single cluster to multi-cluster, multi-team enterprise environments.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-1.0+-EF7B4D)](https://modelcontextprotocol.io)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.29+-326CE5?logo=kubernetes&logoColor=white)](https://kubernetes.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 What Is This?

An **MCP (Model Context Protocol) server** that exposes Kubernetes SRE operations as tools an AI assistant can call.

```
You:    "Run the high error rate runbook for the production namespace"

Claude: [calls run_runbook → executes org-approved diagnosis sequence]
        Step 1: Checked deployments — nginx (3/3), api-service (1/3 ⚠️)
        Step 2: Found pod api-service-7f9d — 47 restarts, OOMKilled
        Step 3: Warning events — OOMKilled x3 in last 10 minutes
        Recommendation: Increase memory limit to 512Mi + scale to 5 replicas
```

---

## ✨ What's New in v2.0

| Feature | v1 | v2 |
|---|---|---|
| Clusters supported | 1 (hardcoded) | Many (dynamic context switching) |
| Write operations | Unrestricted | Policy-checked with guardrails |
| Audit trail | None | Full structured JSON log |
| Incident diagnosis | Ad-hoc | Encoded runbooks (standardized) |
| Operational consistency | Per-engineer | Org-wide enforced |

---

## 🛠️ Tools

### Read
| Tool | Description |
|---|---|
| `list_clusters` | All clusters in kubeconfig |
| `get_pods` | Pod status, restarts, container states |
| `get_crashlooping_pods` | CrashLoopBackOff pods across all namespaces |
| `get_pod_logs` | Logs including previous crashed container |
| `get_node_health` | Node readiness and pressure conditions |
| `get_deployments` | Desired vs ready vs available replicas |
| `get_events` | Warning events — key incident signal |
| `get_namespaces` | All namespaces |

### Write (Policy-checked + Audit-logged)
| Tool | Policy Enforced |
|---|---|
| `scale_deployment` | Max replicas · Blocked namespaces · Prod minimums |

### SRE Runbooks
| Tool | Description |
|---|---|
| `list_runbooks` | Available runbooks with triggers |
| `run_runbook` | Execute org-standard diagnosis sequence |

### Governance
| Tool | Description |
|---|---|
| `get_audit_log` | All recent operations with timestamps |

---

## 🏗️ Architecture

```
Claude Desktop (MCP Host)
       │
       │  MCP Protocol (stdio / JSON-RPC)
       ▼
┌─────────────────────────────────────┐
│         SRE MCP Server v2           │
│  server.py        ← entry point     │
│  cluster_manager  ← multi-cluster   │
│  policy.py        ← write guards    │
│  audit.py         ← JSON audit log  │
│  runbooks.py      ← SRE runbooks    │
└──────────────┬──────────────────────┘
               │  kubernetes Python SDK
               ▼
    ┌──────────────────────┐
    │  Kubernetes Clusters │
    │  (any kubeconfig     │
    │   context)           │
    └──────────────────────┘
```

---

## 🚀 Quick Start

```bash
git clone https://github.com/ManishMaurya22/sre-mcp-server
cd sre-mcp-server
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sre-k8s": {
      "command": "/Users/<YOUR_USERNAME>/sre-mcp-server/venv/bin/python",
      "args": ["/Users/<YOUR_USERNAME>/sre-mcp-server/server.py"]
    }
  }
}
```

See [docs/SETUP.md](docs/SETUP.md) for full setup guide.

---

## 🔐 Policy Configuration

```bash
export POLICY_MAX_REPLICAS=30
export POLICY_SCALE_BLOCKED_NS="kube-system,gatekeeper-system"
export POLICY_PROD_NAMESPACES="production,prod"
export POLICY_PROD_MIN_REPLICAS=2
```

```
You:    "Scale nginx to 0 in production"
Claude: ❌ Policy Denied — scaling to 0 not allowed in production (min: 2)
        Operation audit-logged.
```

---

## 📋 Encoded Runbooks

Available: `high_error_rate` · `node_pressure` · `deployment_rollback`

```
You: "Run the high_error_rate runbook for production"

Claude runs in order:
  1. get_deployments    → spot unhealthy deployments
  2. get_pods           → check restart counts
  3. get_events         → surface warning signals
  4. get_crashlooping_pods → cluster-wide check
  + surfaces remediation hints
```

---

## 🗂️ Structure

```
sre-mcp-server/
├── server.py              # Main MCP server
├── cluster_manager.py     # Multi-cluster context management
├── policy.py              # Write operation guardrails
├── audit.py               # Structured audit trail
├── runbooks.py            # Encoded SRE runbooks
├── requirements.txt
├── tools/k8s_tools.py
├── config/claude_desktop_config.example.json
├── docs/
│   ├── SETUP.md
│   └── INTERVIEW_GUIDE.md
└── .github/workflows/ci.yaml
```

---

## 🗺️ Roadmap

- [ ] Prometheus MCP — SLO burn rate queries
- [ ] PagerDuty MCP — incident acknowledgement
- [ ] ArgoCD MCP — GitOps sync and triggers
- [ ] Central MCP Gateway — auth + multi-team routing

---

## 📄 License

MIT — See [LICENSE](LICENSE)

---

*Built by [Manish Maurya](https://manishmaurya22.github.io/) — DevOps/SRE Leader | 16+ Years | Abu Dhabi, UAE* Website: https://manishmaurya22.github.io/
