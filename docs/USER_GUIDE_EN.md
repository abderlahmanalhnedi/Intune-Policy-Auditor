# User guide (English)

## Intune in plain language

Microsoft Intune lets an organization describe settings for managed users/devices. A policy export describes intended configuration and targeting; it does not prove devices received it. Multiple assigned policies may configure the same setting.

## Run an audit

Start the application, choose **New audit**, upload JSON/ZIP or use Demo, review the detected policy/setting counts, and select an active pack or explicit limited analysis. You may add accepted deviations, validated organization requirements, and target/pilot context. Requirements are retained for traceability but do not create findings yet. Files stay local in Offline Mode and raw bytes are not retained.

Dashboard is the decision overview. Policies explains each document/settings/assignments. Findings answers what was found, current/selected values, impact, action, pilot, rollback, confidence, sources, and trace. The **Not evaluable** filter adds available/missing evidence and a suggested resolution. Conflicts distinguishes duplicates and overlap confidence. Knowledge Packs shows version/hash/freshness/provenance. Reports downloads nine traceable formats.

`Not evaluable` means required evidence is missing; it does not mean safe or unsafe. `More restrictive` is not automatically better. `Accepted deviation` means an approved value-specific exception is currently valid; check raw status and expiry.

Use Guided Mode for question-based explanations and Expert Mode for IDs/paths/trace. Language/theme changes never rerun analysis.

Before changing Intune, verify assignments/filters, affected populations, licensing/applicability, runtime deployment, business impact, pilot and rollback with authorized administrators. The auditor never performs the change.
