"""Explicit allowlist of verified read-only Microsoft Graph operations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GraphOperation:
    name: str
    method: str
    path: str
    api_version: str
    delegated_scopes: tuple[str, ...]
    documentation_url: str


READ_CONFIGURATION_SCOPE = "DeviceManagementConfiguration.Read.All"

GRAPH_OPERATIONS: dict[str, GraphOperation] = {
    "device_configurations": GraphOperation(
        name="device_configurations",
        method="GET",
        path="/v1.0/deviceManagement/deviceConfigurations",
        api_version="v1.0",
        delegated_scopes=(READ_CONFIGURATION_SCOPE,),
        documentation_url=(
            "https://learn.microsoft.com/en-us/graph/api/intune-deviceconfig-"
            "deviceconfiguration-list?view=graph-rest-1.0"
        ),
    ),
    "device_compliance_policies": GraphOperation(
        name="device_compliance_policies",
        method="GET",
        path="/v1.0/deviceManagement/deviceCompliancePolicies",
        api_version="v1.0",
        delegated_scopes=(READ_CONFIGURATION_SCOPE,),
        documentation_url=(
            "https://learn.microsoft.com/en-us/graph/api/intune-deviceconfig-"
            "devicecompliancepolicy-list?view=graph-rest-1.0"
        ),
    ),
    "configuration_policies_beta": GraphOperation(
        name="configuration_policies_beta",
        method="GET",
        path="/beta/deviceManagement/configurationPolicies",
        api_version="beta",
        delegated_scopes=(READ_CONFIGURATION_SCOPE,),
        documentation_url=(
            "https://learn.microsoft.com/en-us/graph/api/intune-deviceconfigv2-"
            "devicemanagementconfigurationpolicy-list?view=graph-rest-beta"
        ),
    ),
    "assignment_filters_beta": GraphOperation(
        name="assignment_filters_beta",
        method="GET",
        path="/beta/deviceManagement/assignmentFilters",
        api_version="beta",
        delegated_scopes=(READ_CONFIGURATION_SCOPE,),
        documentation_url=(
            "https://learn.microsoft.com/en-us/graph/api/intune-policyset-"
            "deviceandappmanagementassignmentfilter-list?view=graph-rest-beta"
        ),
    ),
}


def require_read_operation(name: str) -> GraphOperation:
    operation = GRAPH_OPERATIONS.get(name)
    if operation is None:
        raise ValueError("graph_operation_not_allowlisted")
    if operation.method != "GET":
        raise ValueError("graph_operation_is_not_read_only")
    if any("ReadWrite" in scope for scope in operation.delegated_scopes):
        raise ValueError("graph_readwrite_scope_forbidden")
    return operation
