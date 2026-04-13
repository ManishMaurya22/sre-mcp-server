# =============================================================================
# policy.py — Policy guardrails for write operations
# Encodes org-wide reliability practices as code.
# Every write operation is validated here before execution.
# =============================================================================

import logging
import os
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("sre-mcp-server.policy")

# ── Policy result ─────────────────────────────────────────────────────────────

@dataclass
class PolicyResult:
    allowed: bool
    reason: str
    warnings: list = field(default_factory=list)


# ── Policy rules (loaded from env or defaults) ────────────────────────────────

POLICY = {
    # Hard ceiling on replicas — prevents runaway scaling
    "max_replicas": int(os.getenv("POLICY_MAX_REPLICAS", "50")),

    # Namespaces where scaling is completely blocked
    "scale_blocked_namespaces": os.getenv(
        "POLICY_SCALE_BLOCKED_NS", "kube-system,gatekeeper-system,cert-manager"
    ).split(","),

    # Namespaces classified as production — extra warnings applied
    "production_namespaces": os.getenv(
        "POLICY_PROD_NAMESPACES", "production,prod"
    ).split(","),

    # Minimum replicas allowed in production (prevent scaling to 0)
    "prod_min_replicas": int(os.getenv("POLICY_PROD_MIN_REPLICAS", "2")),
}


# ── Write operations that require policy checks ───────────────────────────────

WRITE_OPERATIONS = {"scale_deployment"}
READ_OPERATIONS  = {
    "get_pods", "get_crashlooping_pods", "get_pod_logs",
    "get_node_health", "get_deployments", "get_events",
    "get_namespaces", "list_clusters"
}


# ── Policy engine ─────────────────────────────────────────────────────────────

def check_policy(operation: str, arguments: dict) -> PolicyResult:
    """
    Validate an operation against org policy before execution.
    Returns PolicyResult(allowed=True/False, reason, warnings).
    """

    if operation not in WRITE_OPERATIONS:
        return PolicyResult(allowed=True, reason="read-only operation")

    warnings = []

    # ── scale_deployment checks ───────────────────────────────────────────
    if operation == "scale_deployment":
        namespace = arguments.get("namespace", "")
        replicas  = arguments.get("replicas", 0)
        deploy    = arguments.get("deployment", "")

        # Block scaling in system namespaces
        if namespace in POLICY["scale_blocked_namespaces"]:
            return PolicyResult(
                allowed=False,
                reason=f"Scaling is blocked in namespace '{namespace}'. "
                       f"Blocked namespaces: {POLICY['scale_blocked_namespaces']}"
            )

        # Hard cap on replicas
        if replicas > POLICY["max_replicas"]:
            return PolicyResult(
                allowed=False,
                reason=f"Requested replicas ({replicas}) exceeds org policy "
                       f"maximum of {POLICY['max_replicas']}. "
                       f"Raise a platform ticket to increase the limit."
            )

        # Prevent scaling to 0 in production
        if namespace in POLICY["production_namespaces"] and replicas == 0:
            return PolicyResult(
                allowed=False,
                reason=f"Scaling to 0 replicas is not allowed in production "
                       f"namespace '{namespace}'. Minimum is "
                       f"{POLICY['prod_min_replicas']}."
            )

        # Warn if scaling below minimum in production
        if (namespace in POLICY["production_namespaces"] and
                replicas < POLICY["prod_min_replicas"]):
            warnings.append(
                f"⚠️  Scaling below recommended minimum of "
                f"{POLICY['prod_min_replicas']} replicas in production"
            )

        # Warn on large scale-up
        if replicas >= 20:
            warnings.append(
                f"⚠️  Scaling to {replicas} replicas — "
                f"verify this is intentional and not a runbook error"
            )

        # Warn on production changes
        if namespace in POLICY["production_namespaces"]:
            warnings.append(
                f"⚠️  Production change — scaling '{deploy}' "
                f"in '{namespace}' to {replicas} replicas"
            )

        return PolicyResult(
            allowed=True,
            reason="policy checks passed",
            warnings=warnings
        )

    return PolicyResult(allowed=True, reason="no policy defined for operation")
