# =============================================================================
# prometheus.py — Prometheus query client
# Handles instant and range queries against local or in-cluster Prometheus
# =============================================================================

import os
import logging
import requests
from datetime import datetime, timezone

logger = logging.getLogger("sre-mcp-server.prometheus")

# Override with env var for in-cluster or remote Prometheus
PROMETHEUS_URL = os.getenv(
    "PROMETHEUS_URL",
    "http://localhost:9090"
)


def query_prometheus_api(
    query: str,
    duration: str = None,
    step: str = None
) -> dict:
    """
    Execute a PromQL query.
    - Instant query if no duration provided
    - Range query if duration + step provided
    """
    try:
        if duration and step:
            # Range query — returns time series
            end   = datetime.now(timezone.utc).timestamp()
            start = end - _duration_to_seconds(duration)
            resp  = requests.get(
                f"{PROMETHEUS_URL}/api/v1/query_range",
                params={"query": query, "start": start, "end": end, "step": step},
                timeout=10
            )
        else:
            # Instant query — returns current value
            resp = requests.get(
                f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": query},
                timeout=10
            )

        resp.raise_for_status()
        return resp.json()

    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "error":  f"Cannot connect to Prometheus at {PROMETHEUS_URL}. "
                      f"Run: kubectl port-forward svc/prometheus-kube-prometheus-prometheus "
                      f"-n monitoring 9090:9090"
        }
    except requests.exceptions.Timeout:
        return {"status": "error", "error": "Prometheus query timed out"}
    except Exception as e:
        logger.error(f"Prometheus query failed: {e}")
        return {"status": "error", "error": str(e)}


def _duration_to_seconds(duration: str) -> float:
    """Convert duration string (1h, 30m, 5m) to seconds."""
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    unit  = duration[-1]
    value = float(duration[:-1])
    return value * units.get(unit, 60)
