# Decision model

Each setting follows ordered gates: typed observation; exact canonical ID or explicit alias; selected active pack/version; platform; scope; sourced applicability; source existence; exact value semantics; explicit comparison; value-specific organizational deviation; evidence attachment; raw/effective alignment; severity gate; explanation and trace.

Failure does not fall through to a guess. Unknown ID/value/source/comparison/applicability becomes `not_evaluable` with one or more machine reasons. A sourced mismatch can become `not_applicable`; sourced unsupported content becomes `unsupported`.

## Alignment

`aligned`, `more_restrictive`, `less_restrictive`, `different`, `accepted_deviation`, `expired_deviation`, `not_in_selected_baseline`, `not_applicable`, `unsupported`, `not_evaluable`.

More restrictive is not automatically better. It can increase security while breaking authentication, applications, support, network access, or performance. An accepted deviation changes effective status only; raw status and approval metadata remain visible.

## Severity gates

Severity comes from the exact knowledge setting and finding type, never from identifier words. Critical/High requires exact official evidence; synthetic or nonofficial packs are capped at Medium. Not-evaluable is informational uncertainty, not safety. Runtime errors and expired deviations have explicit types.

## Overall decision

The engine chooses among aligned, aligned-with-deviations, changes-required-before-pilot, pilot-recommended, manual-review-required, insufficient-evidence, and runtime-remediation-required. Runtime errors outrank intent alignment; confirmed conflicts and high findings block; uncertainty produces review rather than a false pass. Every decision includes blocking/warning lists, next action, evidence summary, failed gates, and trace.
