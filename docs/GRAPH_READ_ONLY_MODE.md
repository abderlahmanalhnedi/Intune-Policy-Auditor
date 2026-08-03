# Microsoft Graph read-only mode

Tenant Mode is optional and does not affect Offline Mode. Current implementation status is a safe tested skeleton: device-code authentication, token lifecycle, allowlisted collection retrieval, and API/UI status exist; stable adapters into full tenant audits and live-tenant validation remain incomplete.

The backend requests delegated `DeviceManagementConfiguration.Read.All` only. Tokens remain in the MSAL backend cache with owner-only mode where the OS supports it. React receives the device-code prompt/status, never access/refresh tokens. Sign-out clears accounts, pending flows, and the cache file.

Verified operations use GET only:

- v1.0 device configurations and compliance policies;
- beta configuration policies and assignment filters, isolated and visibly labeled beta.

Official operation sources are linked in `graph/operations.py`: [device configurations](https://learn.microsoft.com/en-us/graph/api/intune-deviceconfig-deviceconfiguration-list?view=graph-rest-1.0), [configuration policies beta](https://learn.microsoft.com/en-us/graph/api/intune-deviceconfigv2-devicemanagementconfigurationpolicy-list?view=graph-rest-beta), [assignment filters beta](https://learn.microsoft.com/en-us/graph/api/intune-policyset-deviceandappmanagementassignmentfilter-list?view=graph-rest-beta), and [compliance policies](https://learn.microsoft.com/en-us/graph/api/intune-deviceconfig-devicecompliancepolicy-list?view=graph-rest-1.0). Assignment collection adapters are not yet allowlisted.

The client enforces HTTPS Graph next links, page limits/cycle detection, timeouts, Retry-After/exponential retry, correlation IDs, five-minute cache TTL, cancellation through async task cancellation, and partial-page failures. It never exposes raw beta objects to audit models. No POST report operation is currently allowlisted.

Configuration uses `INTUNE_AUDITOR_TENANT_ID` and `INTUNE_AUDITOR_CLIENT_ID` for a public-client registration. Do not add a client secret. Before production use, validate tenant consent, conditional access, sovereign-cloud requirements, endpoint shapes, and retention with the organization.
