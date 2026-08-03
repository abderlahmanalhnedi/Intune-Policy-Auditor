# Product requirements

The product serves beginners and expert endpoint administrators who need to understand policy intent, targeting, evidence quality, possible conflict, and change risk without granting write authority.

## Functional requirements

- Local JSON/multi-file/ZIP audit and synthetic demonstration.
- Exact, versioned pack selection and transparent provenance.
- Typed parsing with technical paths and diagnostics.
- Nuanced raw/effective alignment and explicit not-evaluable reasons.
- Time-bounded accepted deviations.
- Assignment risk and confirmed/probable/possible conflict analysis.
- Sourced applicability; missing context remains unknown.
- Separate runtime evidence and policy intent.
- Dashboard, inventories, details, reports, i18n, modes, themes, responsive layout.
- Optional read-only Graph boundary with minimal delegated permissions.
- CLI/web service parity, local privacy controls, cross-platform launchers.

## Quality attributes

Evidence and correctness outrank setting count. The target is practical use with 500 policies/10,000 settings, stable pagination, no recalculation on display filtering, bounded file/report processing, strict local binding, accessibility at 1024×768, and deterministic cache keys.

## Non-goals

The product is not remediation, deployment, certification, vulnerability scanning, a universal compliance framework, or proof that assigned policy reached devices. It does not infer unknown Microsoft behavior and does not use AI to create findings.

## Acceptance

The minimum slice starts in one local process, runs the six-policy synthetic audit, demonstrates all core states and conflict classes, exposes evidence/trace, exports reports, and produces no frontend/backend exception. Automated validation is defined in `TEST_STRATEGY.md`.
