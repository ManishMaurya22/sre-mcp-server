# Setup Guide

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | >= 3.10 | `brew install python@3.11` |
| kubectl | >= 1.29 | `brew install kubectl` |
| Claude Desktop | Latest | [Download](https://claude.ai/download) |
| Docker Desktop | Latest | `brew install --cask docker` |

---

## 1. Local Kubernetes Cluster

Enable Kubernetes in Docker Desktop:

```
Docker Desktop → Settings → Kubernetes → Enable Kubernetes → Apply & Restart
```

Verify:
```bash
kubectl cluster-info
kubectl get nodes
```

Deploy test workloads:
```bash
kubectl create namespace production
kubectl create namespace staging

# Healthy app
kubectl create deployment nginx --image=nginx:1.25 --replicas=3 -n production

# Intentionally broken pod (for testing crashloop detection)
kubectl create deployment crasher \
  --image=busybox --replicas=2 -n production \
  -- /bin/sh -c "echo starting && sleep 5 && exit 1"
```

---

## 2. Python Environment

```bash
git clone https://github.com/ManishMaurya22/sre-mcp-server
cd sre-mcp-server

python3.11 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

Verify:
```bash
python -c "import mcp; print('mcp OK')"
python -c "from kubernetes import client; print('kubernetes OK')"
```

---

## 3. Test the Server

```bash
# Should hang silently — means it is waiting for MCP input (correct behaviour)
python server.py
# Ctrl+C to stop
```

---

## 4. Connect to Claude Desktop

Get your exact Python path:
```bash
which python
# e.g. /Users/manishmaurya/sre-mcp-server/venv/bin/python
```

Edit Claude Desktop config:
```bash
code ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

Add the `mcpServers` block (see `config/claude_desktop_config.example.json`):
```json
{
  "mcpServers": {
    "sre-k8s": {
      "command": "/Users/manishmaurya/sre-mcp-server/venv/bin/python",
      "args": ["/Users/manishmaurya/sre-mcp-server/server.py"]
    }
  }
}
```

Fully restart Claude Desktop:
```bash
pkill -f Claude && open -a Claude
```

---

## 5. Verify Connection

Check logs:
```bash
tail -f ~/Library/Logs/Claude/mcp-server-sre-k8s.log
```

You should see:
```
Server started and connected successfully
```

---

## 6. Try These Prompts in Claude Desktop

```
Show me all pods in the production namespace
```
```
Are there any crashlooping pods in my cluster? Show me their logs
```
```
Scale the nginx deployment to 5 replicas in production
```
```
What warning events are there in the production namespace?
```
```
What is the health of all my nodes?
```
