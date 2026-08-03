# Threat model

## Assets and trust boundaries

Assets are local policy intent, optional tenant responses/tokens, accepted deviations, knowledge integrity, and audit conclusions. Boundaries are file upload, pack/SCT import, Graph, report download, SQLite/data directories, browser/backend, dependencies, and operator interpretation.

## Threats and controls

- **Malicious/malformed JSON:** byte/aggregate limits, NUL rejection, typed parsing, diagnostics, no unsafe deserialization.
- **ZIP bomb/traversal/symlink/nesting/executable:** count/expanded-size/ratio/depth/suffix/path/mode checks before extraction; in-memory policy ZIPs.
- **Report/HTML injection:** Jinja autoescape, explicit escaping, no untrusted HTML rendering, CSP, safe filenames.
- **CSV formula injection:** leading formula/control characters are prefixed safely.
- **Graph token theft:** backend-only MSAL cache, restrictive mode, no logs/React/localStorage, explicit deletion, localhost binding.
- **Tenant-data retention:** raw policy/Graph payloads are not persisted by default; summary/report persistence is opt-in and deletable.
- **AI leakage/judgment:** AI is absent from the active path, off by default, and cannot create/change findings by design.
- **Stale/tampered baseline:** data/schema/source hashes, provenance, validation, freshness warnings, explicit versions.
- **False positive:** exact evidence/value/comparison gates, severity caps, raw trace, no fuzzy judgments.
- **False negative:** unknown content remains visible/not evaluable; coverage dimensions expose gaps.
- **Misleading confidence:** extraction, semantic, evidence, applicability, and conflict confidence remain separate.
- **Dependency compromise:** lockfile, isolated environments, npm/pip audits, CI and review; no remote fonts/templates.
- **Local server exposure:** loopback default, trusted host/CORS/CSP; Docker publishes loopback only.

Residual risks include compromised local accounts, malicious but valid documents causing resource pressure within limits, dependency zero-days, incomplete parsers, wrong official source mappings, and operator overreliance. Professional review and tenant change-control remain required.
