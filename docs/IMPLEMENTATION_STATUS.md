# Implementation Status

## Current phase

Phase 7 — polish and release validation — is complete for the production-ready Offline Mode vertical slice. Phase 6 remains deliberately partial: the read-only Graph boundary is implemented and mocked, while stable tenant payload adapters and consented live-tenant validation are outstanding. No release, commit, push, or tag has been created.

## Completed work

- Built the greenfield FastAPI/Pydantic v2/SQLAlchemy/Alembic/SQLite backend and strict React/TypeScript/Vite frontend as a local monorepo.
- Serve the compiled SPA and versioned `/api/v1` API from one Uvicorn process on `127.0.0.1:8765`.
- Implemented bounded JSON/multiple-file/JSON-only ZIP ingestion, strict duplicate/non-finite/depth-safe JSON decoding, deterministic normalization, typed parser diagnostics, preview counts, unknown-setting preservation, and secure filename/archive/report handling.
- Added the hash-bound `synthetic.test-baseline`, six explicitly marked synthetic policies, accepted/expired deviations, every required nuanced alignment state, confirmed/probable/possible conflicts, broad-assignment warnings, and synthetic runtime failure evidence.
- Implemented evidence, evidence-type/vendor, severity, platform/scope, applicability, exact-value, deviation, assignment, conflict, coverage, and overall-decision gates with deterministic traces. Pack validation rejects alias/canonical collisions, false exact-value counts, invalid canonical baselines, and comparison parameters that disagree with the baseline.
- Implemented explicit comparison rules for boolean/integer/decimal/string/enum/choice/list/set/range/object/not-configured/unknown values and every specified comparison mode. No keyword, regex, fuzzy, category, or AI signal can create a Microsoft judgment.
- Added Knowledge Pack import/validate/activate/deactivate/remove/provenance/report workflows and a conservative, archive-safe SCT importer whose ambiguous mappings remain `pending_review`.
- Added the three-step wizard with preflight parsing, limited analysis, accepted deviations, validated organization requirements, physical/VDI/shared/pilot context, and a final privacy/permission/scope summary.
- Added responsive Dashboard, Policies, Policy Detail, Findings, Finding Detail, Conflicts, Knowledge Packs, Reports, Tenant, Settings, Help, and About routes with German/English, Guided/Expert, and System/Light/Dark controls.
- Added evidence quality, policy health, exact/assignment/runtime metrics, not-evaluable reasons, assignment/filter details, conflict reasoning, runtime fields, deviation raw/effective state, source links/dates, pilot/rollback guidance, and accessible sortable/paginated tables.
- Added nine report formats: Executive HTML, Technical HTML, PDF, Markdown, machine JSON, three CSV variants, and knowledge-provenance JSON. Every format includes traceability metadata and limitations, including metadata-only rows for empty CSV results.
- Added local privacy preferences, opt-in summary history/retention, opt-in report copies, explicit local-data/temp/token/settings cleanup, bounded active-audit memory, and separately stored MSAL cache.
- Added backend-only device-code auth, delegated read-only scope, GET allowlist, v1/beta isolation, pagination, retry/backoff, timeout, cancellation-compatible async calls, partial failures, TTL caching, correlation IDs, scope/API/data-age status, sign-out, and token-cache deletion.
- Added Typer audit/pack-validation/SCT CLI commands, technical PDF output, macOS/Linux and Windows lifecycle scripts/launchers, optional non-root Compose packaging, GitHub Actions, bilingual operator documentation, threat model, and architecture/evidence/decision/pack documentation.
- Generated frontend API types from the FastAPI OpenAPI schema and kept cache keys independent of presentation language while covering all trust inputs.
- Updated Python dependency floors and the lockfile after a live advisory scan; pip-audit and npm audit now report no known vulnerabilities.

## Currently implemented vertical slice

On the current macOS device, the setup/build/test scripts directly discover the isolated repository toolchain and complete without global Python/Node changes; the start script serves the production build as one loopback process and stops cleanly. Demo or offline JSON/multiple-JSON/ZIP audit works; pack/limited selection and context are honored; Dashboard/Policies/Findings/Conflicts/Knowledge Packs/Reports work; evidence, deviations, duplicates/conflicts, uncertainty, sources, and deterministic traces are inspectable; all nine formats download; language/view/theme changes do not rerun analysis; malformed input is rejected without an application exception.

The final 500-policy/10,000-unique-setting smoke completed in 0.306 seconds for preview and 0.576 seconds for audit, producing 10,000 visible not-evaluable findings and an `insufficient_evidence` decision.

## Tests already passing

- Backend compileall, Ruff format/check, strict MyPy across 65 source files, and Bandit: passing.
- Backend pytest: 146 tests passing with 81% statement/branch-aware coverage across 3,532 statements and 912 branches.
- Frontend ESLint and strict TypeScript: passing.
- Frontend Vitest/Testing Library: 5 files, 11 tests passing.
- Playwright Chromium: 3 workflows passing at production URL, including the 1024×768 layout.
- Direct setup/build/test/start lifecycle and one-process production smoke: passing; route splitting keeps every emitted JavaScript chunk below 500 kB.
- Synthetic pack validation and required CLI audit: passing.
- npm audit and Python pip-audit: no known vulnerabilities.
- All seven PowerShell files parse successfully; all shell files pass `bash -n`; Compose and workflow YAML parse successfully.

## Unresolved errors

- No application source-code or validation failure is currently known.
- FastAPI's TestClient import emits one upstream Starlette deprecation warning recommending the future `httpx2` test integration; all tests pass under current fixed dependency versions.
- Docker is not installed on the development device, so the image build, health check, read-only root filesystem, and Compose runtime could not be executed locally. The Dockerfile/Compose files are implemented and statically validated.
- GitHub-hosted Windows/macOS/Ubuntu workflows were created but cannot execute before the uncommitted workspace is published; local macOS execution and Windows PowerShell syntax were validated.

## Intentionally deferred features

- A production Microsoft pack. Current official source/version catalogs were verified, but no exact setting-ID/value pack is fabricated; official status remains **not installed**.
- Stable v1/beta Graph-to-audit adapters, real runtime/noncompliance/conflict report ingestion, and validation against a consented test tenant.
- Deterministic decision semantics for free-text organization requirements. Files are schema-validated and retained as context only.
- Full audit-result restoration/history navigation; SQLite opt-in history currently stores privacy-minimized summaries.
- Optional AI Summary payload redaction/preview/provider/output validation. Its Settings location and non-authoritative contract are designed only.

## Next exact task

Create and contract-test one narrow stable Graph adapter against anonymized, organization-approved response shapes, then validate the read-only flow in a consented test tenant. In parallel, curate the first official pack only from independently reviewed exact IDs, values, versioned official evidence, and artifact hashes.

## Important architecture decisions

- Core services exchange typed Pydantic models; raw external dictionaries end at parser/Graph adapter boundaries.
- Unknown, ambiguous, unversioned, unsourced, or non-deterministically comparable content remains `Not evaluable / Nicht bewertbar`.
- The synthetic pack can prove engine behavior but cannot create an official Microsoft claim or Critical severity.
- Raw uploads are not persisted. Active results use a locked 20-entry memory LRU; SQLite stores settings and explicitly enabled summaries only.
- Offline Mode has no Graph or AI dependency. Graph tokens remain backend-only and no ReadWrite permission or mutation operation exists.
- Imported archives are processed in memory with path, name, symlink, executable-mode, encryption, nesting, count, expanded-size, ratio, and duplicate-member defenses.
- Reports render typed results with HTML escaping, CSV formula protection, safe filenames, bounded size, source/version/hash metadata, and an independent-project disclaimer.
- Frontend runtime schemas are generated from OpenAPI; locale/theme/view are the only browser-local preferences.
- Production is one loopback process; Docker is optional and Compose publishes only `127.0.0.1:8765`.

## Commands required to continue

```bash
cd /Users/abdul.alhnedi/Developer/Intune-Policy-Auditor
./scripts/setup.sh
./scripts/build.sh
./scripts/start.sh
```

Full validation:

```bash
./scripts/test.sh
cd backend && .venv/bin/python -m pytest --cov=src --cov-report=term-missing
cd ../frontend && npm run test:e2e
cd .. && backend/.venv/bin/python scripts/smoke.py
```
