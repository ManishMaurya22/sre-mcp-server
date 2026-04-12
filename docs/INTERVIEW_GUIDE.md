# MCP Interview Guide

> Use this as a reference to explain your MCP work confidently in interviews.

---

## What is MCP? (30-second answer)

> "MCP — Model Context Protocol — is an open standard that lets AI models securely
> connect to external tools and data sources. Think of it like a USB-C standard
> but for AI integrations. Instead of every AI tool building custom integrations,
> MCP provides one protocol that any AI host can speak."

---

## What Did You Build?

> "I built a Kubernetes SRE MCP Server in Python that exposes cluster operations
> as tools an AI assistant can call. So instead of running five kubectl commands
> to diagnose a CrashLoopBackOff, I can ask Claude in natural language —
> 'what's crashlooping and why?' — and it calls my MCP tools live against the
> cluster, correlates the pod logs, and suggests a fix."

---

## Architecture (whiteboard this)

```
Claude Desktop (MCP Host)
       │
       │  MCP Protocol (stdio / JSON-RPC)
       │
sre-mcp-server (MCP Server)
       │
       │  kubernetes Python SDK
       │
Kubernetes Cluster (Docker Desktop / EKS / AKS)
  ├── production namespace
  │     ├── nginx (healthy)
  │     └── crasher (CrashLoopBackOff)
  └── staging namespace
        └── redis
```

---

## Tools You Exposed

| Tool | What It Does | SRE Use Case |
|---|---|---|
| `get_pods` | List pods with status + restarts | First step in any incident |
| `get_crashlooping_pods` | Find CrashLoopBackOff cluster-wide | Proactive incident detection |
| `get_pod_logs` | Fetch pod logs (including previous crashed container) | Root cause analysis |
| `scale_deployment` | Scale replicas up/down | Emergency response |
| `get_node_health` | Node readiness + pressure conditions | Infrastructure health |
| `get_deployments` | Desired vs ready replicas | Deployment health checks |
| `get_events` | Warning events in namespace | Early incident signals |
| `get_namespaces` | List all namespaces | Cluster overview |

---

## Real Incident Workflow (tell this as a story)

> "Imagine I get a PagerDuty alert at 2 AM — high error rate in production.
> Instead of SSH-ing in and running kubectl commands one by one, I open Claude
> Desktop and say:
>
> *'Check for crashlooping pods in production and show me the logs'*
>
> Claude calls get_crashlooping_pods → finds the broken pod → calls get_pod_logs
> → sees an OOMKilled error in the logs → I then say 'scale the deployment to
> 3 replicas' → Claude calls scale_deployment.
>
> The whole diagnosis that used to take 10 minutes of kubectl commands now takes
> 2 minutes of natural language conversation. That is Agentic SRE."

---

## Why MCP Over Custom Scripts?

| Approach | Problem |
|---|---|
| Shell scripts | Not conversational, no context across steps |
| Custom chatbot | Reinvents the wheel for every integration |
| MCP | Standard protocol — any AI host can use your server |

---

## What Would You Build Next?

Good follow-up answers:
- **Prometheus MCP** — query SLO burn rates, check error budgets
- **PagerDuty MCP** — acknowledge incidents, add timeline notes
- **ArgoCD MCP** — check sync status, trigger deployments
- **Runbook MCP** — search and execute SRE runbooks via AI
