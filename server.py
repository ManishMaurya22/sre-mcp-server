#!/usr/bin/env python3
# =============================================================================
# SRE MCP Server — Kubernetes Operations via Model Context Protocol
# Author: Manish Maurya (https://manishmaurya22.github.io/)
#
# Exposes Kubernetes SRE operations as MCP tools so AI assistants
# (Claude Desktop) can interact with your cluster in natural language.
#
# Tools exposed:
#   - get_pods               → List pods in a namespace with status
#   - get_crashlooping_pods  → Find all CrashLoopBackOff pods cluster-wide
#   - get_pod_logs           → Fetch logs from a specific pod
#   - scale_deployment       → Scale a deployment to N replicas
#   - get_node_health        → Node readiness and condition summary
#   - get_deployments        → List deployments with replica status
#   - get_events             → Recent warning events in a namespace
#   - get_resource_usage     → Top pods by CPU/memory (requires metrics-server)
# =============================================================================

import asyncio
import json
import logging

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sre-mcp-server")

# ── Kubernetes client setup ───────────────────────────────────────────────────
try:
    config.load_kube_config()
    logger.info("Loaded kubeconfig successfully")
except Exception as e:
    logger.warning(f"kubeconfig not found, trying in-cluster config: {e}")
    try:
        config.load_incluster_config()
        logger.info("Loaded in-cluster config successfully")
    except Exception as e2:
        logger.error(f"Could not load any Kubernetes config: {e2}")

v1      = client.CoreV1Api()
apps_v1 = client.AppsV1Api()

# ── MCP Server ────────────────────────────────────────────────────────────────
app = Server("sre-k8s-server")


@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="get_pods",
            description="Get all pods in a namespace with their status, restart count and node",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {
                        "type": "string",
                        "description": "Kubernetes namespace (e.g. production, staging)"
                    }
                },
                "required": ["namespace"]
            }
        ),
        Tool(
            name="get_crashlooping_pods",
            description="Find all CrashLoopBackOff pods across ALL namespaces",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_pod_logs",
            description="Get the last N log lines from a specific pod container",
            inputSchema={
                "type": "object",
                "properties": {
                    "pod_name":  {"type": "string", "description": "Name of the pod"},
                    "namespace": {"type": "string", "description": "Namespace the pod is in"},
                    "lines":     {"type": "integer", "description": "Number of log lines to return (default: 50)"},
                    "previous":  {"type": "boolean", "description": "Get logs from previous (crashed) container"}
                },
                "required": ["pod_name", "namespace"]
            }
        ),
        Tool(
            name="scale_deployment",
            description="Scale a Kubernetes deployment to a specified number of replicas",
            inputSchema={
                "type": "object",
                "properties": {
                    "deployment": {"type": "string", "description": "Name of the deployment"},
                    "namespace":  {"type": "string", "description": "Namespace"},
                    "replicas":   {"type": "integer", "description": "Desired replica count"}
                },
                "required": ["deployment", "namespace", "replicas"]
            }
        ),
        Tool(
            name="get_node_health",
            description="Get health and readiness status of all cluster nodes",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_deployments",
            description="List all deployments in a namespace with desired vs available replicas",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {"type": "string", "description": "Namespace to list deployments from"}
                },
                "required": ["namespace"]
            }
        ),
        Tool(
            name="get_events",
            description="Get recent Warning events in a namespace — useful for diagnosing issues",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {"type": "string", "description": "Namespace to get events from"},
                    "limit":     {"type": "integer", "description": "Max number of events (default: 20)"}
                },
                "required": ["namespace"]
            }
        ),
        Tool(
            name="get_namespaces",
            description="List all namespaces in the cluster with their status",
            inputSchema={"type": "object", "properties": {}}
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    logger.info(f"Tool called: {name} with args: {arguments}")

    try:
        # ── get_pods ─────────────────────────────────────────────────────────
        if name == "get_pods":
            pods = v1.list_namespaced_pod(arguments["namespace"])
            result = []
            for pod in pods.items:
                restarts = sum(
                    cs.restart_count
                    for cs in (pod.status.container_statuses or [])
                )
                container_states = []
                for cs in (pod.status.container_statuses or []):
                    state = "unknown"
                    if cs.state.running:
                        state = "running"
                    elif cs.state.waiting:
                        state = f"waiting:{cs.state.waiting.reason}"
                    elif cs.state.terminated:
                        state = f"terminated:{cs.state.terminated.reason}"
                    container_states.append({"container": cs.name, "state": state})

                result.append({
                    "name":             pod.metadata.name,
                    "phase":            pod.status.phase,
                    "ready":            all(cs.ready for cs in (pod.status.container_statuses or [])),
                    "restarts":         restarts,
                    "node":             pod.spec.node_name,
                    "container_states": container_states,
                    "age":              str(pod.metadata.creation_timestamp)
                })
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

        # ── get_crashlooping_pods ─────────────────────────────────────────────
        elif name == "get_crashlooping_pods":
            pods = v1.list_pod_for_all_namespaces()
            crashlooping = []
            for pod in pods.items:
                for cs in (pod.status.container_statuses or []):
                    if cs.state.waiting and cs.state.waiting.reason == "CrashLoopBackOff":
                        crashlooping.append({
                            "namespace": pod.metadata.namespace,
                            "pod":       pod.metadata.name,
                            "container": cs.name,
                            "restarts":  cs.restart_count,
                            "node":      pod.spec.node_name
                        })
            if not crashlooping:
                return [TextContent(type="text", text="✅ No CrashLoopBackOff pods found in any namespace")]
            return [TextContent(type="text", text=json.dumps(crashlooping, indent=2))]

        # ── get_pod_logs ──────────────────────────────────────────────────────
        elif name == "get_pod_logs":
            logs = v1.read_namespaced_pod_log(
                name=arguments["pod_name"],
                namespace=arguments["namespace"],
                tail_lines=arguments.get("lines", 50),
                previous=arguments.get("previous", False)
            )
            return [TextContent(type="text", text=logs or "(no logs available)")]

        # ── scale_deployment ──────────────────────────────────────────────────
        elif name == "scale_deployment":
            # Get current replica count first
            current = apps_v1.read_namespaced_deployment(
                name=arguments["deployment"],
                namespace=arguments["namespace"]
            )
            current_replicas = current.spec.replicas

            # Apply scale
            body = {"spec": {"replicas": arguments["replicas"]}}
            apps_v1.patch_namespaced_deployment_scale(
                name=arguments["deployment"],
                namespace=arguments["namespace"],
                body=body
            )
            return [TextContent(
                type="text",
                text=json.dumps({
                    "status":   "success",
                    "deployment": arguments["deployment"],
                    "namespace":  arguments["namespace"],
                    "previous_replicas": current_replicas,
                    "new_replicas":      arguments["replicas"],
                    "message": f"Scaled {arguments['deployment']} from {current_replicas} → {arguments['replicas']} replicas"
                }, indent=2)
            )]

        # ── get_node_health ───────────────────────────────────────────────────
        elif name == "get_node_health":
            nodes = v1.list_node()
            result = []
            for node in nodes.items:
                conditions = {c.type: c.status for c in node.status.conditions}
                capacity   = node.status.capacity or {}
                result.append({
                    "name":             node.metadata.name,
                    "ready":            conditions.get("Ready", "Unknown"),
                    "memory_pressure":  conditions.get("MemoryPressure", "Unknown"),
                    "disk_pressure":    conditions.get("DiskPressure", "Unknown"),
                    "pid_pressure":     conditions.get("PIDPressure", "Unknown"),
                    "cpu_capacity":     capacity.get("cpu", "unknown"),
                    "memory_capacity":  capacity.get("memory", "unknown"),
                    "kubelet_version":  node.status.node_info.kubelet_version if node.status.node_info else "unknown",
                    "roles":            [
                        k.split("/")[-1]
                        for k in (node.metadata.labels or {})
                        if k.startswith("node-role.kubernetes.io/")
                    ]
                })
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        # ── get_deployments ───────────────────────────────────────────────────
        elif name == "get_deployments":
            deployments = apps_v1.list_namespaced_deployment(arguments["namespace"])
            result = []
            for d in deployments.items:
                result.append({
                    "name":                d.metadata.name,
                    "desired_replicas":    d.spec.replicas,
                    "ready_replicas":      d.status.ready_replicas or 0,
                    "available_replicas":  d.status.available_replicas or 0,
                    "updated_replicas":    d.status.updated_replicas or 0,
                    "healthy":             (d.status.ready_replicas or 0) == (d.spec.replicas or 0),
                    "image":               d.spec.template.spec.containers[0].image if d.spec.template.spec.containers else "unknown"
                })
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        # ── get_events ────────────────────────────────────────────────────────
        elif name == "get_events":
            events = v1.list_namespaced_event(
                arguments["namespace"],
                field_selector="type=Warning"
            )
            result = []
            for e in sorted(events.items, key=lambda x: x.last_timestamp or x.event_time or "", reverse=True)[:arguments.get("limit", 20)]:
                result.append({
                    "time":    str(e.last_timestamp or e.event_time),
                    "reason":  e.reason,
                    "object":  f"{e.involved_object.kind}/{e.involved_object.name}",
                    "message": e.message,
                    "count":   e.count
                })
            if not result:
                return [TextContent(type="text", text="✅ No warning events found")]
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

        # ── get_namespaces ────────────────────────────────────────────────────
        elif name == "get_namespaces":
            namespaces = v1.list_namespace()
            result = [
                {
                    "name":   ns.metadata.name,
                    "status": ns.status.phase,
                    "age":    str(ns.metadata.creation_timestamp)
                }
                for ns in namespaces.items
            ]
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except ApiException as e:
        error_msg = f"Kubernetes API error: {e.status} {e.reason} — {e.body}"
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]
    except Exception as e:
        error_msg = f"Error executing {name}: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]


# ── Entry point ───────────────────────────────────────────────────────────────
async def main():
    logger.info("Starting SRE MCP Server...")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
