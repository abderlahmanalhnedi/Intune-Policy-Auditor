import httpx
import pytest
import respx

from intune_auditor.graph.client import AsyncGraphClient
from intune_auditor.graph.operations import GRAPH_OPERATIONS, require_read_operation


def test_operation_allowlist_contains_no_write_permission_or_method() -> None:
    for operation in GRAPH_OPERATIONS.values():
        assert operation.method == "GET"
        assert all("ReadWrite" not in scope for scope in operation.delegated_scopes)
    with pytest.raises(ValueError, match="not_allowlisted"):
        require_read_operation("delete_everything")


@pytest.mark.asyncio
@respx.mock
async def test_graph_pagination_and_cache_are_bounded() -> None:
    route = respx.get(
        "https://graph.microsoft.com/v1.0/deviceManagement/deviceConfigurations"
    ).mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "value": [{"id": "one"}],
                    "@odata.nextLink": (
                        "https://graph.microsoft.com/v1.0/deviceManagement/"
                        "deviceConfigurations?$skiptoken=test"
                    ),
                },
            ),
            httpx.Response(200, json={"value": [{"id": "two"}]}),
        ]
    )
    client = AsyncGraphClient(lambda: "test-token")
    result = await client.fetch_collection("device_configurations")
    cached = await client.fetch_collection("device_configurations")
    assert [item["id"] for item in result.items] == ["one", "two"]
    assert cached.from_cache
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_retry_after_is_honored_without_live_graph() -> None:
    route = respx.get(
        "https://graph.microsoft.com/v1.0/deviceManagement/deviceCompliancePolicies"
    ).mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, json={"value": []}),
        ]
    )
    delays: list[float] = []

    async def no_sleep(delay: float) -> None:
        delays.append(delay)

    result = await AsyncGraphClient(lambda: "test-token", sleep=no_sleep).fetch_collection(
        "device_compliance_policies"
    )
    assert not result.partial
    assert delays == [0]
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_unsafe_next_link_becomes_partial_failure() -> None:
    respx.get("https://graph.microsoft.com/beta/deviceManagement/configurationPolicies").mock(
        return_value=httpx.Response(
            200,
            json={"value": [{"id": "safe"}], "@odata.nextLink": "https://evil.example/data"},
        )
    )
    result = await AsyncGraphClient(lambda: "test-token").fetch_collection(
        "configuration_policies_beta"
    )
    assert result.partial
    assert result.failures[0].reason == "unsafe_or_invalid_next_link"
