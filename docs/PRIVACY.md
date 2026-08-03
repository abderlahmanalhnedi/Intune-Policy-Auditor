# Privacy

Raw uploads are processed in memory and discarded after the request. Temporary directories are context-managed and automatically removed. Audit history and generated report copies default off. Active results are held only in a bounded process-memory session.

SQLite and imported pack metadata use `platformdirs`:

- Windows: `%LOCALAPPDATA%\IntunePolicyAuditor\`
- macOS: `~/Library/Application Support/IntunePolicyAuditor/`
- Linux: `~/.local/share/IntunePolicyAuditor/`

When history is explicitly enabled, only audit ID/time/mode and decision/count summary are stored with retention expiry—not raw input. Saved report copies require a separate opt-in. Settings can delete summaries/reports, temporary files, Graph token cache, or reset preferences.

MSAL tokens live under a separate `auth` directory and never enter browser storage. Language/mode/theme are non-sensitive browser-local preferences. Production tenant payloads and uploaded JSON are excluded from structured logs.

Local storage is not application-level encrypted; it relies on OS account/filesystem protection. Organizations should apply device encryption and access controls. Do not use the tool on an untrusted shared workstation.
