# Architecture

## Shape

Intune Policy Auditor is a local monorepo. In production, one Uvicorn/FastAPI process serves both `/api/v1` and the compiled React SPA at `127.0.0.1:8765`.

```text
JSON/ZIP or optional Graph GET
          │
          ▼
secure input boundary ──► typed parser diagnostics
          │
          ▼
Pydantic policy observations
          │
          ├──► exact knowledge-pack resolution
          ├──► applicability and deviation gates
          ├──► deterministic comparison and trace
          ├──► assignment/conflict analysis
          └──► coverage and overall decision
                         │
                         ▼
           FastAPI contracts / reports / CLI
                         │
                         ▼
                  React presentation
```

## Boundaries

- `security` rejects unsafe names, sizes, archives, HTML, and CSV cells before parsing/reporting.
- `parsing` converts supported external shapes into typed domain observations. It does not judge security.
- `knowledge` validates immutable manifests/settings, hashes, aliases, evidence, and provenance.
- `evaluation`, `applicability`, `deviations`, `assignments`, and `conflicts` contain deterministic business rules.
- `application.AuditService` is the shared web/CLI use case. Raw uploads never enter persistence.
- `reporting` renders only typed audit results with escaping and report-size bounds.
- `graph` is optional and isolated. Beta responses never enter the audit model directly.
- `persistence` stores local preferences and opt-in summaries using SQLAlchemy/Alembic/SQLite.

## State and concurrency

Active audit results live in a locked, bounded in-memory LRU (20 audits). SQLite uses WAL, foreign keys, busy timeout, and a platformdirs path. Report and history persistence require explicit settings. Temporary directories use context-managed cleanup.

## Contracts

Pydantic v2 is authoritative. FastAPI produces `backend/openapi.json`; `openapi-typescript` generates the React contract. The frontend must not manually recreate API schemas. Schema/application versions are centralized in `version.py`.

## Decisions

- Source modules are cohesive rather than mirroring a large placeholder tree.
- No DI framework, agent framework, external database, cloud service, or legacy compatibility layer is used.
- The synthetic pack makes the vertical slice deterministic without presenting invented Microsoft content.
- Optional Graph functionality fails independently; Offline Mode has no authentication dependency.
