# Administrator guide (English)

Install Python 3.11–3.13 and Node 24 LTS, then use the setup/build/start commands in README. Normal use needs no elevated rights. Production is one loopback process; `.env` supports host/port/log level, privacy defaults, public-client tenant/client IDs, and data/frontend overrides.

Use OS disk encryption and account controls. Back up only explicitly retained SQLite/reports/imported packs. Raw uploads are not backup candidates. Cleanup controls are under Settings; deleting local audit data removes summaries/report copies, while pack removal is explicit on Knowledge Packs.

For Tenant Mode, register a public/native client for device code, configure tenant/client ID, and consent only `DeviceManagementConfiguration.Read.All`. Never configure a client secret or ReadWrite permission. Review beta warnings and `GRAPH_READ_ONLY_MODE.md`; live use remains an organizational validation responsibility.

Validate/import packs through UI/CLI and require two-person evidence review. Keep old immutable versions for reproducibility. Never mark ambiguous SCT records verified.

Operational checks: `/api/v1/health`, `/api/v1/version`, local log output, free disk in application-data path, pack validation/freshness, retention settings, and dependency/security CI. Use `scripts/smoke.py` after production builds.

Docker is optional and publishes loopback only. If changing bind address, treat it as advanced exposure: add network access controls, TLS/reverse proxy, host/CORS review, and organizational authorization first.
