#!/usr/bin/env python3
# =============================================================================
# SRE MCP Server — Enterprise-grade Kubernetes Operations
# Author: Manish Maurya (https://manishmaurya22.github.io/)
#
# v2.0 — Scales from single cluster to multi-cluster, multi-team
#
# What's new in v2:
#   - Multi-cluster context management (list_clusters, cluster= arg on all tools)
#   - Policy guardrails on write operations (max replicas, blocked namespaces)
#   - Audit trail for every operation (structured JSON log)
#   - Encoded SRE runbooks (standardized diagnosis sequences)
# =============================================================================

import asyncio
import json
import logging

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from kubernetes.client.rest import ApiException

from cluster_manager import cluster_manager
from policy import check_policy, WRITE_OPERATIONS
from audit import audit_log, get_recent_audit
from runbooks import list_runbooks, format_runbook, get_runbook

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger("sre-mcp-server")

app = Server("sre-k8s-server")

CLUSTER_ARG = {
    "cluster": {
        "type": "string",
        "description": "Cluster context name from kubeconfig (optional — defaults to current context)"
    }
}


@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="list_clusters",
            description="List all Kubernetes clusters available in kubeconfig",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_pods",
            description="List all pods in a namespace with phase, restarts, and container states",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {"type": "string", "description": "Kubernetes namespace"},
                    **CLUSTER_ARG
                },
                "required": ["namespace"]
            }
        ),
        Tool(
            name="get_crashlooping_pods",
            description="Find all CrashLoopBackOff pods across ALL namespaces",
            inputSchema={"type": "object", "properties": {**CLUSTER_ARG}}
        ),
        Tool(
            name="get_pod_logs",
            description="Fetch logs from a pod — supports previous=true for crashed containers",
            inputSchema={
                "type": "object",
                "properties": {
                    "pod_name":  {"type": "string"},
                    "namespace": {"type": "string"},
                    "lines":     {"type": "integer", "description": "Lines to return (default 50)"},
                    "previous":  {"type": "boolean", "description": "Get logs from previous crashed container"},
                    **CLUSTER_ARG
                },
                "required": ["pod_name", "namespace"]
            }
        ),
        Tool(
            name="get_node_health",
            description="Node readiness and pressure conditions for all nodes",
            inputSchema={"type": "object", "properties": {**CLUSTER_ARG}}
        ),
        Tool(
            name="get_deployments",
            description="List deployments with desired vs ready vs available replicas",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    **CLUSTER_ARG
                },
                "required": ["namespace"]
            }
        ),
        Tool(
            name="get_events",
            description="Recent Warning events in a namespace — key signal for incident diagnosis",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    "limit":     {"type": "integer", "description": "Max events (default 20)"},
                    **CLUSTER_ARG
                },
                "required": ["namespace"]
            }
        ),
        Tool(
            name="get_namespaces",
            description="List all namespaces in the cluster",
            inputSchema={"type": "object", "properties": {**CLUSTER_ARG}}
        ),
        Tool(
            name="scale_deployment",
            description=(
                "Scale a deployment to N replicas. "
                "Policy-checked: blocked namespaces, max replicas, prod minimums enforced. "
                "All scale operations are audit-logged."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "deployment": {"type": "string"},
                    "namespace":  {"type": "string"},
                    "replicas":   {"type": "integer"},
                    **CLUSTER_ARG
                },
                "required": ["deployment", "namespace", "replicas"]
            }
        ),
        Tool(
            name="list_runbooks",
            description="List all encoded SRE runbooks with their triggers",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="run_runbook",
            description=(
                "Execute a standardized SRE runbook. "
                "Runs the org-approved diagnosis sequence. "
                "Available: high_error_rate, node_pressure, deployment_rollback"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "runbook_name": {
                        "type": "string",
                        "description": "high_error_rate | node_pressure | deployment_rollback"
                    },
                    "namespace": {"type": "string"},
                    **CLUSTER_ARG
                },
                "required": ["runbook_name", "namespace"]
            }
        ),
        Tool(
            name="get_audit_log",
            description="View recent audit log — all MCP operations are logged here",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Number of entries (default 20)"}
                }
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    logger.info(f"Tool called: {name} | args: {arguments}")

    cluster   = arguments.get("cluster")
    namespace = arguments.get("namespace", "")

    # Policy check for write operations
    if name in WRITE_OPERATIONS:
        policy = check_policy(name, arguments)
        if not policy.allowed:
            audit_log(name, arguments, cluster, "denied", policy.reason)
            return [TextContent(
                type="text",
                text=f"❌ **Policy Denied**\n\n{policy.reason}\n\nThis operation has been audit-logged."
            )]

    try:
        v1, apps_v1 = cluster_manager.get_clients(cluster)

        if name == "list_clusters":
            clusters = cluster_manager.list_clusters()
            return [TextContent(type="text", text=json.dumps({"available_clusters": clusters}, indent=2))]

        elif name == "get_pods":
            pods   = v1.list_namespaced_pod(namespace)
            result = []
            for pod in pods.items:
                restarts = sum(cs.restart_count for cs in (pod.status.container_statuses or []))
                container_states = []
                for cs in (pod.status.container_statuses or []):
                    state = "unknown"
                    if cs.state.running:        state = "running"
                    elif cs.state.waiting:      state = f"waiting:{cs.state.waiting.reason}"
                    elif cs.state.terminated:   state = f"terminated:{cs.state.terminated.reason}"
                    container_states.append({"container": cs.name, "state": state})
                result.append({
                    "name": pod.metadata.name, "phase": pod.status.phase,
                    "ready": all(cs.ready for cs in (pod.status.container_statuses or [])),
                    "restarts": restarts, "node": pod.spec.node_name,
                    "container_states": container_states,
                    "age": str(pod.metadata.creation_timestamp)
                })
            audit_log(name, arguments, cluster, "allowed")
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

        elif name == "get_crashlooping_pods":
            pods         = v1.list_pod_for_all_namespaces()
            crashlooping = []
            for pod in pods.items:
                for cs in (pod.status.container_statuses or []):
                    if cs.state.waiting and cs.state.waiting.reason == "CrashLoopBackOff":
                        crashlooping.append({
                            "namespace": pod.metadata.namespace, "pod": pod.metadata.name,
                            "container": cs.name, "restarts": cs.restart_count, "node": pod.spec.node_name
                        })
            audit_log(name, arguments, cluster, "allowed")
            if not crashlooping:
                return [TextContent(type="text", text="✅ No CrashLoopBackOff pods found")]
            return [TextContent(type="text", text=json.dumps(crashlooping, indent=2))]

        elif name == "get_pod_logs":
            logs = v1.read_namespaced_pod_log(
                name=arguments["pod_name"], namespace=namespace,
                tail_lines=arguments.get("lines", 50),
                previous=arguments.get("previous", False)
            )
            audit_log(name, arguments, cluster, "allowed")
            return [TextContent(type="text", text=logs or "(no logs available)")]

        elif name == "scale_deployment":
            policy  = check_policy(name, arguments)
            current = apps_v1.read_namespaced_deployment(name=arguments["deployment"], namespace=namespace)
            current_replicas = current.spec.replicas
            apps_v1.patch_namespaced_deployment_scale(
                name=arguments["deployment"], namespace=namespace,
                body={"spec": {"replicas": arguments["replicas"]}}
            )
            audit_log(name, arguments, cluster, "allowed", warnings=policy.warnings)
            response = {
                "status": "success", "deployment": arguments["deployment"],
                "namespace": namespace, "cluster": cluster or "default",
                "previous_replicas": current_replicas, "new_replicas": arguments["replicas"],
                "warnings": policy.warnings, "audit": "operation logged"
            }
            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        elif name == "get_node_health":
            nodes  = v1.list_node()
            result = []
            for node in nodes.items:
                conditions = {c.type: c.status for c in node.status.conditions}
                capacity   = node.status.capacity or {}
                result.append({
                    "name": node.metadata.name,
                    "ready": conditions.get("Ready", "Unknown"),
                    "memory_pressure": conditions.get("MemoryPressure", "Unknown"),
                    "disk_pressure":   conditions.get("DiskPressure", "Unknown"),
                    "pid_pressure":    conditions.get("PIDPressure", "Unknown"),
                    "cpu_capacity":    capacity.get("cpu", "unknown"),
                    "memory_capacity": capacity.get("memory", "unknown"),
                    "kubelet_version": node.status.node_info.kubelet_version if node.status.node_info else "unknown",
                    "roles": [k.split("/")[-1] for k in (node.metadata.labels or {}) if k.startswith("node-role.kubernetes.io/")]
                })
            audit_log(name, arguments, cluster, "allowed")
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_deployments":
            deployments = apps_v1.list_namespaced_deployment(namespace)
            result = [{
                "name": d.metadata.name, "desired_replicas": d.spec.replicas,
                "ready_replicas": d.status.ready_replicas or 0,
                "available_replicas": d.status.available_replicas or 0,
                "healthy": (d.status.ready_replicas or 0) == (d.spec.replicas or 0),
                "image": d.spec.template.spec.containers[0].image if d.spec.template.spec.containers else "unknown"
            } for d in deployments.items]
            audit_log(name, arguments, cluster, "allowed")
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_events":
            events = v1.list_namespaced_event(namespace, field_selector="type=Warning")
            sorted_events = sorted(events.items, key=lambda x: x.last_timestamp or x.event_time or "", reverse=True)[:arguments.get("limit", 20)]
            result = [{"time": str(e.last_timestamp or e.event_time), "reason": e.reason,
                       "object": f"{e.involved_object.kind}/{e.involved_object.name}",
                       "message": e.message, "count": e.count} for e in sorted_events]
            audit_log(name, arguments, cluster, "allowed")
            if not result:
                return [TextContent(type="text", text="✅ No warning events found")]
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

        elif name == "get_namespaces":
            namespaces = v1.list_namespace()
            result = [{"name": ns.metadata.name, "status": ns.status.phase} for ns in namespaces.items]
            audit_log(name, arguments, cluster, "allowed")
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

        elif name == "list_runbooks":
            return [TextContent(type="text", text=json.dumps(list_runbooks(), indent=2))]

        elif name == "run_runbook":
            runbook_name = arguments["runbook_name"]
            rb           = get_runbook(runbook_name)
            if not rb:
                return [TextContent(type="text", text=f"Runbook '{runbook_name}' not found. Available: {[r['key'] for r in list_runbooks()]}")]

            results = [format_runbook(runbook_name), "\n---\n## Live Diagnosis Results\n"]
            for step in rb.steps:
                results.append(f"\n### {step.description}\n")
                step_args = {k: (namespace if v == "{namespace}" else v) for k, v in step.arguments_template.items()}
                if cluster:
                    step_args["cluster"] = cluster
                try:
                    step_result = await call_tool(step.tool, step_args)
                    results.append(step_result[0].text)
                except Exception as e:
                    results.append(f"⚠️ Step failed: {e}")
            audit_log(name, arguments, cluster, "allowed")
            return [TextContent(type="text", text="\n".join(results))]

        elif name == "get_audit_log":
            entries = get_recent_audit(arguments.get("limit", 20))
            if not entries:
                return [TextContent(type="text", text="No audit entries yet")]
            return [TextContent(type="text", text=json.dumps(entries, indent=2))]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except ApiException as e:
        error_msg = f"Kubernetes API error: {e.status} {e.reason}"
        audit_log(name, arguments, cluster, "error", error=error_msg)
        return [TextContent(type="text", text=error_msg)]
    except Exception as e:
        error_msg = f"Error in {name}: {str(e)}"
        audit_log(name, arguments, cluster, "error", error=error_msg)
        return [TextContent(type="text", text=error_msg)]


async def main():
    logger.info("Starting SRE MCP Server v2.0")
    logger.info(f"Available clusters: {cluster_manager.list_clusters()}")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
