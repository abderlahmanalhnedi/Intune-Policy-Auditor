# Security

The service binds to `127.0.0.1` by default, validates trusted hosts/CORS, emits CSP and other security headers, bounds uploads/reports, and does not log payloads/tokens. Only JSON and JSON-only ZIP policy inputs are accepted. XML is handled only by the explicit SCT importer with entity/DTD defenses.

Reports escape HTML, protect CSV formula cells, sanitize filenames, and never execute uploaded content. JSON uses safe standard/Pydantic decoding; pickle/YAML/eval/exec and dynamic plug-in execution are absent.

Graph access is delegated, minimal, backend-only, and GET-allowlisted. No ReadWrite permission or mutation endpoint exists. Offline behavior is independent of authentication.

Keep dependencies current and run Bandit, Ruff, MyPy, pytest, npm audit, and the scheduled security workflow. Docker runs non-root with dropped capabilities/no-new-privileges and a read-only root filesystem.

Report vulnerabilities privately through the repository host's security-advisory function. Include a minimal synthetic reproduction, affected version, and impact. Never attach credentials, tokens, real policy exports, device identities, or tenant responses.
