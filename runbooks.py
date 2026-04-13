# =============================================================================
# runbooks.py — Standardized SRE runbooks encoded as composable steps
# These are the org-approved diagnosis sequences.
# The AI follows these instead of improvising — ensuring consistency
# across teams and on-call engineers.
# =============================================================================

from dataclasses import dataclass
from typing import List


@dataclass
class RunbookStep:
    tool: str
    description: str
    arguments_template: dict   # {key: "{arg}" } — filled at runtime


@dataclass
class Runbook:
    name: str
    description: str
    trigger: str               # When to use this runbook
    steps: List[RunbookStep]
    remediation_hints: List[str]


# ── Runbook library ───────────────────────────────────────────────────────────

RUNBOOKS = {

    "high_error_rate": Runbook(
        name="High Error Rate",
        description="Org-standard diagnosis for elevated HTTP 5xx error rate",
        trigger="When error rate alert fires or SLO burn rate is elevated",
        steps=[
            RunbookStep(
                tool="get_deployments",
                description="1. Check for unhealthy deployments first",
                arguments_template={"namespace": "{namespace}"}
            ),
            RunbookStep(
                tool="get_pods",
                description="2. Check pod health and restart counts",
                arguments_template={"namespace": "{namespace}"}
            ),
            RunbookStep(
                tool="get_events",
                description="3. Check for warning events that explain the issue",
                arguments_template={"namespace": "{namespace}", "limit": 20}
            ),
            RunbookStep(
                tool="get_crashlooping_pods",
                description="4. Check for crashlooping pods cluster-wide",
                arguments_template={}
            ),
        ],
        remediation_hints=[
            "If OOMKilled → increase memory limits or check for memory leak",
            "If ImagePullBackOff → check image tag exists and registry credentials",
            "If CrashLoopBackOff → check logs from previous container with get_pod_logs(previous=true)",
            "If deployment replicas mismatch → check node capacity with get_node_health",
            "If config error → check recent ArgoCD sync or kubectl rollout history",
        ]
    ),

    "node_pressure": Runbook(
        name="Node Pressure",
        description="Org-standard diagnosis for node memory/disk/CPU pressure",
        trigger="When NodeNotReady or node pressure alert fires",
        steps=[
            RunbookStep(
                tool="get_node_health",
                description="1. Check all node conditions",
                arguments_template={}
            ),
            RunbookStep(
                tool="get_pods",
                description="2. Check which pods are on the affected node",
                arguments_template={"namespace": "{namespace}"}
            ),
            RunbookStep(
                tool="get_events",
                description="3. Check for eviction events",
                arguments_template={"namespace": "default", "limit": 30}
            ),
        ],
        remediation_hints=[
            "MemoryPressure → identify highest memory pods, consider scaling down or evicting",
            "DiskPressure → check PVC usage, clear old logs or expand storage",
            "PIDPressure → check for pid-leaking processes, may need node replacement",
            "NotReady → cordon node (kubectl cordon <node>) then drain and investigate",
        ]
    ),

    "deployment_rollback": Runbook(
        name="Deployment Rollback",
        description="Org-standard rollback procedure after bad deployment",
        trigger="When a new deployment causes increased errors or latency",
        steps=[
            RunbookStep(
                tool="get_deployments",
                description="1. Identify the bad deployment",
                arguments_template={"namespace": "{namespace}"}
            ),
            RunbookStep(
                tool="get_events",
                description="2. Check events for deployment errors",
                arguments_template={"namespace": "{namespace}"}
            ),
            RunbookStep(
                tool="get_pods",
                description="3. Check pod status post-deployment",
                arguments_template={"namespace": "{namespace}"}
            ),
        ],
        remediation_hints=[
            "Rollback via ArgoCD: sync to previous revision in ArgoCD UI",
            "Rollback via kubectl: kubectl rollout undo deployment/<name> -n <namespace>",
            "Emergency scale-down to 0 then back up forces pod recreation",
            "Check image tag — :latest can cause non-deterministic rollouts",
            "After rollback, verify error rate drops before closing incident",
        ]
    ),

}


def get_runbook(name: str) -> Runbook:
    """Retrieve a runbook by key."""
    return RUNBOOKS.get(name)


def list_runbooks() -> list:
    """List all available runbooks with their triggers."""
    return [
        {
            "name":        rb.name,
            "key":         key,
            "description": rb.description,
            "trigger":     rb.trigger,
            "steps":       len(rb.steps),
        }
        for key, rb in RUNBOOKS.items()
    ]


def format_runbook(name: str) -> str:
    """Format a runbook as readable text for AI consumption."""
    rb = get_runbook(name)
    if not rb:
        available = list(RUNBOOKS.keys())
        return f"Runbook '{name}' not found. Available: {available}"

    lines = [
        f"# Runbook: {rb.name}",
        f"**Trigger:** {rb.trigger}",
        f"**Description:** {rb.description}",
        "",
        "## Diagnosis Steps (execute in order)",
    ]
    for step in rb.steps:
        lines.append(f"- {step.description} → tool: `{step.tool}`")

    lines += ["", "## Remediation Hints"]
    for hint in rb.remediation_hints:
        lines.append(f"- {hint}")

    return "\n".join(lines)
