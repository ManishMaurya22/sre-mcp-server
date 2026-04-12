# =============================================================================
# Tool definitions — exported for documentation and testing
# =============================================================================

TOOLS = [
    {
        "name": "get_pods",
        "description": "List all pods in a namespace with phase, restarts, and container states",
        "example_prompt": "Show me all pods in the production namespace"
    },
    {
        "name": "get_crashlooping_pods",
        "description": "Find all CrashLoopBackOff pods across all namespaces",
        "example_prompt": "Are there any crashlooping pods in my cluster?"
    },
    {
        "name": "get_pod_logs",
        "description": "Fetch the last N log lines from a pod (supports --previous for crashed containers)",
        "example_prompt": "Get the last 100 logs from pod nginx-abc123 in production"
    },
    {
        "name": "scale_deployment",
        "description": "Scale a deployment to a desired replica count",
        "example_prompt": "Scale the nginx deployment to 5 replicas in production"
    },
    {
        "name": "get_node_health",
        "description": "Check readiness and pressure conditions for all nodes",
        "example_prompt": "What is the health of all nodes in my cluster?"
    },
    {
        "name": "get_deployments",
        "description": "List deployments with desired vs ready vs available replicas",
        "example_prompt": "Show me all deployments in staging and which ones are unhealthy"
    },
    {
        "name": "get_events",
        "description": "Fetch recent Warning events in a namespace for incident diagnosis",
        "example_prompt": "Show me all warning events in the production namespace"
    },
    {
        "name": "get_namespaces",
        "description": "List all namespaces in the cluster",
        "example_prompt": "What namespaces exist in this cluster?"
    },
]
