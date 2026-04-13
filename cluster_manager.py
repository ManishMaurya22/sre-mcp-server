# =============================================================================
# cluster_manager.py — Multi-cluster context management
# Handles dynamic kubeconfig loading per cluster context
# =============================================================================

import logging
from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger("sre-mcp-server.cluster-manager")


class ClusterManager:
    """
    Manages connections to multiple Kubernetes clusters.
    Loads kubeconfig contexts dynamically so a single MCP server
    can operate across all clusters an SRE has access to.
    """

    def __init__(self):
        self._contexts = []
        self._current_context = None
        self._load_available_contexts()

    def _load_available_contexts(self):
        """Load all available kubeconfig contexts on startup."""
        try:
            contexts, active = config.list_kube_config_contexts()
            self._contexts = [c["name"] for c in (contexts or [])]
            self._current_context = active["name"] if active else None
            logger.info(f"Loaded {len(self._contexts)} cluster contexts: {self._contexts}")
        except Exception as e:
            logger.warning(f"Could not load kubeconfig contexts: {e}")
            self._contexts = []

    def list_clusters(self) -> list:
        """Return all available cluster contexts."""
        return self._contexts

    def get_clients(self, cluster: str = None):
        """
        Return (CoreV1Api, AppsV1Api) for the requested cluster.
        Falls back to current context if cluster is None.
        """
        target = cluster or self._current_context

        if target and target not in self._contexts and self._contexts:
            raise ValueError(
                f"Cluster '{target}' not found. "
                f"Available: {self._contexts}"
            )

        try:
            if target:
                config.load_kube_config(context=target)
                logger.info(f"Switched to cluster context: {target}")
            else:
                config.load_kube_config()
        except Exception:
            # Fallback to in-cluster config (when running inside K8s)
            config.load_incluster_config()

        return client.CoreV1Api(), client.AppsV1Api()


# Singleton — shared across all tool calls
cluster_manager = ClusterManager()
