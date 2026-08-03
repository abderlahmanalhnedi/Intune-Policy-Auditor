# Limitations

- Only the synthetic demonstration pack is installed. There are no official Microsoft recommendations in the repository.
- Parser coverage is conservative and cannot understand every Intune export variant or nested vendor payload. Unknowns stay visible.
- Offline exports show intent, not delivery/success/error state, and might omit assignments/filter definitions.
- Conflict overlap for different groups/unknown filters is probabilistic without directory membership.
- Applicability depends on sourced pack rules and supplied target facts; absent OS/edition/license/device context stays unknown.
- Tenant Mode has safe auth/retrieval plumbing but no complete stable Graph-to-audit adapters and no live-tenant validation.
- Organization-requirement files are strictly validated and retained in audit configuration, but their free-text requirements do not yet alter deterministic findings or decisions.
- SCT XML import cannot infer Intune canonical IDs; records remain pending review.
- Active full audit results are bounded to 20 in process memory; optional SQLite history stores summaries, not full result restoration/navigation.
- SQLite/token cache rely on operating-system protection rather than application-level encryption.
- Optional AI summary is not implemented. Core usefulness does not require it.
- Container files and Compose configuration are implemented and statically parsed, but no Docker engine was available for a local image-build/runtime test.
- No security/compliance tool can guarantee safety or replace authorized professional review, pilot, rollback, and change control.
- Dependency and Microsoft service behavior can change after the 2026-08-03 verification date.
