# 🤖 SRE MCP Server — Kubernetes via AI

> **Natural language Kubernetes operations** — powered by Model Context Protocol (MCP)  
> Connect Claude Desktop to your cluster and manage it in plain English.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-1.0+-EF7B4D)](https://modelcontextprotocol.io)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.29+-326CE5?logo=kubernetes&logoColor=white)](https://kubernetes.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 What Is This?

An **MCP (Model Context Protocol) server** that exposes Kubernetes SRE operations as tools an AI assistant can call. Instead of running kubectl commands one by one, you have a natural language conversation with your cluster.

```
You:    "Are there any crashlooping pods? Show me their logs."

Claude: [calls get_crashlooping_pods]
        Found: crasher-7d9f8b-xkp2q in production (47 restarts)

        [calls get_pod_logs]
        Error: OOMKilled — container exceeded memory limit of 128Mi

        Recommendation: Increase memory limit to at least 256Mi
        or check for a memory leak in the application.
```

---

## 🛠️ Available Tools

| Tool | Description | Example Prompt |
|---|---|---|
| `get_pods` | List pods with status, restarts, node | *"Show me all pods in production"* |
| `get_crashlooping_pods` | Find CrashLoopBackOff pods cluster-wide | *"Any crashlooping pods?"* |
| `get_pod_logs` | Fetch logs (including previous crashed container) | *"Get logs from pod xyz in production"* |
| `scale_deployment` | Scale replicas up/down | *"Scale nginx to 5 replicas"* |
| `get_node_health` | Node readiness and pressure conditions | *"Are all nodes healthy?"* |
| `get_deployments` | Desired vs ready vs available replicas | *"Which deployments are unhealthy?"* |
| `get_events` | Recent Warning events in a namespace | *"Any warning events in staging?"* |
| `get_namespaces` | List all namespaces | *"What namespaces exist?"* |

---

## 🏗️ Architecture

```
Claude Desktop (MCP Host)
       │
       │  MCP Protocol (stdio / JSON-RPC)
       ▼
sre-mcp-server  ◄── server.py
       │
       │  kubernetes Python SDK
       ▼
Kubernetes Cluster
  ├── production namespace
  ├── staging namespace
  └── monitoring namespace
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- kubectl configured (`kubectl get nodes` works)
- Claude Desktop installed

### 1. Clone & Install

```bash
git clone https://github.com/ManishMaurya22/sre-mcp-server
cd sre-mcp-server

python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Test the Server

```bash
python server.py
# Hangs silently = working correctly (waiting for MCP input)
# Ctrl+C to stop
```

### 3. Connect to Claude Desktop

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

Get your exact Python path with:
```bash
which python
```

Restart Claude Desktop fully (`Cmd+Q`, then reopen).

### 4. Try It

Open Claude Desktop and type:
```
Are there any crashlooping pods in my cluster?
```

---

## 📁 Repository Structure

```
sre-mcp-server/
├── server.py                          # Main MCP server — all tool implementations
├── requirements.txt                   # Python dependencies
├── .gitignore
├── tools/
│   └── k8s_tools.py                   # Tool definitions and metadata
├── config/
│   └── claude_desktop_config.example.json  # Claude Desktop config template
├── docs/
│   ├── SETUP.md                       # Detailed setup guide
│   └── INTERVIEW_GUIDE.md             # How to explain MCP in interviews
└── .github/
    └── workflows/
        └── ci.yaml                    # GitHub Actions — lint & import checks
```

---

## 💡 Example Conversations

**Incident Response:**
```
"Check production for any issues — pods, events, deployments"
```

**Diagnosis:**
```
"Get the last 100 logs from the crashlooping pod including the previous container"
```

**Emergency Scaling:**
```
"Scale the api-service deployment to 10 replicas in production"
```

**Health Check:**
```
"Give me a full health summary — nodes, deployments, and any warning events"
```

---

## 🗺️ Roadmap

- [ ] Prometheus MCP — query SLO burn rates and metrics
- [ ] PagerDuty MCP — acknowledge incidents and add notes
- [ ] ArgoCD MCP — GitOps sync status and deployment triggers
- [ ] Runbook MCP — AI-driven runbook execution

---

## 📄 License

MIT — See [LICENSE](LICENSE)

---

*Built by [Manish Maurya](https://manishmaurya22.github.io/) — DevOps/SRE Leader | 16+ Years | Abu Dhabi, UAE*
