# =============================================================================
# audit.py — Audit trail for all MCP tool calls
# Every operation (read + write) is logged with timestamp, args, and result.
# Provides the compliance trail required for SOC2 / enterprise governance.
# =============================================================================

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("sre-mcp-server.audit")

# ── Audit log destination ─────────────────────────────────────────────────────
# Default: ~/.sre-mcp-server/audit.log
# Override with AUDIT_LOG_PATH env var

AUDIT_LOG_PATH = os.getenv(
    "AUDIT_LOG_PATH",
    str(Path.home() / ".sre-mcp-server" / "audit.log")
)


def _ensure_log_dir():
    Path(AUDIT_LOG_PATH).parent.mkdir(parents=True, exist_ok=True)


def audit_log(
    operation: str,
    arguments: dict,
    cluster: str,
    status: str,           # "allowed" | "denied" | "error"
    policy_reason: str = "",
    warnings: list = None,
    error: str = ""
):
    """
    Write a structured audit entry for every tool call.

    Format: one JSON object per line (easy to ship to Splunk / CloudWatch / S3)
    """
    _ensure_log_dir()

    entry = {
        "timestamp":     datetime.now(timezone.utc).isoformat(),
        "operation":     operation,
        "cluster":       cluster or "default",
        "namespace":     arguments.get("namespace", ""),
        "arguments":     {k: v for k, v in arguments.items() if k != "cluster"},
        "status":        status,
        "policy_reason": policy_reason,
        "warnings":      warnings or [],
        "error":         error,
    }

    line = json.dumps(entry)

    # Write to file
    try:
        with open(AUDIT_LOG_PATH, "a") as f:
            f.write(line + "\n")
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")

    # Also emit to structured logger so it appears in Claude Desktop logs
    if status == "denied":
        logger.warning(f"AUDIT DENIED  | {operation} | cluster={cluster} | {policy_reason}")
    elif status == "error":
        logger.error(f"AUDIT ERROR   | {operation} | cluster={cluster} | {error}")
    else:
        logger.info(f"AUDIT ALLOWED | {operation} | cluster={cluster} | ns={arguments.get('namespace', '')}")


def get_recent_audit(limit: int = 20) -> list:
    """Return the last N audit entries — exposed via get_audit_log tool."""
    try:
        with open(AUDIT_LOG_PATH, "r") as f:
            lines = f.readlines()
        entries = [json.loads(l) for l in lines[-limit:] if l.strip()]
        return list(reversed(entries))   # Most recent first
    except FileNotFoundError:
        return []
    except Exception as e:
        logger.error(f"Failed to read audit log: {e}")
        return []
