"""Isolated, optional Microsoft Graph read-only integration."""

from intune_auditor.graph.client import AsyncGraphClient
from intune_auditor.graph.operations import GRAPH_OPERATIONS, GraphOperation

__all__ = ["GRAPH_OPERATIONS", "AsyncGraphClient", "GraphOperation"]
