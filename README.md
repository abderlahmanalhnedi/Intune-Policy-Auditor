# Intune Policy Auditor

Intune Policy Auditor is a local, read-only web application for understanding exported Microsoft Intune policies. It extracts settings and assignments, compares only exact known identifiers and value semantics against a selected versioned knowledge pack, explains conflicts, and produces traceable reports.

The included `synthetic.test-baseline` is demonstration content. It is not a Microsoft baseline and contains no production recommendation.

> This project is independent and is not affiliated with or endorsed by Microsoft. It is not Microsoft-certified, does not guarantee a secure configuration, and does not replace professional review.

## What it does

- Audits one or more local JSON exports or a bounded ZIP archive.
- Keeps unknown settings visible as **Not evaluable / Nicht bewertbar**.
- Distinguishes aligned, weaker, more restrictive, different, accepted/expired deviation, unsupported, not-applicable, and not-evaluable states.
- Separates policy intent from optional runtime evidence.
- Analyzes duplicate settings, assignment overlap, filters, and rollout risk.
- Shows exact evidence, pack version/hash, verification date, decision trace, and limitations.
- Exports Executive HTML, Technical HTML, Markdown, machine-readable JSON, PDF, findings CSV, conflicts CSV, not-evaluable CSV, and provenance JSON.
- Provides German and English, Guided and Expert views, and light/dark/system themes.

It never changes Intune, Entra, users, groups, devices, assignments, or tenant configuration. There is no Graph write operation or ReadWrite permission in the codebase.

## Quick start

Requirements: Python 3.11–3.13 and Node.js 24 LTS. Administrator rights are not required.

macOS or Linux:

```bash
./scripts/setup.sh
./scripts/build.sh
./scripts/start.sh
```

Windows PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup.ps1
.\scripts\build.ps1
.\scripts\start.ps1
```

Open <http://127.0.0.1:8765>. The start script checks setup/build state, starts one FastAPI process, waits for health, opens the browser, and stops on Ctrl+C. It does not reinstall dependencies.

Desktop launchers are also provided: `Start-IntunePolicyAuditor.command`, `.ps1`, and `.cmd`.

## First audit

1. Select **New audit / Neue Prüfung**.
2. Choose JSON files or a ZIP, or start the synthetic demonstration.
3. Select an active knowledge pack. Only the synthetic pack ships installed.
4. Optionally supply `organization/accepted-deviations.example.json`, `organization/requirements.example.json`, and target/pilot context. Requirements are validated and retained as context; they do not create recommendations in the current release.
5. Confirm the detected policy/setting counts, then inspect Dashboard, Policies, Findings, Conflicts, Knowledge Packs, and Reports. You may explicitly continue without a pack; all Microsoft comparisons then remain **Not evaluable**.

Supported input is intentionally conservative: JSON policy exports and ZIP archives containing JSON only. Archive paths, counts, sizes, nesting, compression ratio, executable members, and malformed content are rejected. Parser support covers common settings-catalog, endpoint-security, baseline, device-configuration, compliance, administrative-template, and assignment shapes; unsupported shapes remain diagnostic, not guessed.

## Evidence and Microsoft alignment

A judgment requires an exact normalized setting ID or explicit pack alias, known value semantics, matching platform/scope, an applicable selected pack/version, official exact evidence for Microsoft claims, and a deterministic comparison. Names, keywords, regexes, extraction confidence, and AI cannot create a Microsoft recommendation or severity.

The Microsoft source catalog was checked on 2026-08-03, but no official production pack is bundled because exact Intune identifier/value mappings were not imported and independently validated. See [Microsoft source policy](docs/MICROSOFT_SOURCE_POLICY.md) and [evidence model](docs/EVIDENCE_MODEL.md).

## Privacy and Tenant Mode

Offline Mode sends nothing to Microsoft. Raw uploads are processed in memory and not retained. Audit history and report copies are off by default. SQLite stores preferences and explicitly enabled summary history under the platform-specific application-data directory.

Tenant Mode is optional and partially implemented: backend-only MSAL device-code authentication and an allowlisted read-only Graph retrieval layer exist, with mocked tests. No live tenant validation or stable Graph-to-audit adapter is claimed. Access tokens never reach React or localStorage. See [Graph read-only mode](docs/GRAPH_READ_ONLY_MODE.md) and [privacy](docs/PRIVACY.md).

## Knowledge packs and deviations

Knowledge packs are versioned JSON with manifest/data/schema hashes, provenance, freshness, exact comparison rules, and official-source gates. The UI and CLI can validate packs; the UI can import, activate, deactivate, remove local imported packs, and export validation reports. The SCT importer preserves ambiguous XML records for manual review and never invents Intune IDs.

```bash
cd backend
.venv/bin/python -m intune_auditor.cli.main validate-pack ../knowledge-packs/synthetic/test-baseline
.venv/bin/python -m intune_auditor.cli.main import-sct --input INPUT --output OUTPUT \
  --product PRODUCT --version VERSION --source-reference OFFICIAL_URL
```

Accepted deviations are value-specific, owned, approved, ticketed, and time-bounded. Expired deviations are findings; they do not silently suppress raw alignment.

## CLI

```bash
cd backend
.venv/bin/python -m intune_auditor.cli.main audit ../samples/policies \
  --deviations ../organization/accepted-deviations.example.json \
  --language en --format json --output ../tmp/audit.json \
  --exact-only --fail-on never
```

`--fail-on` accepts `critical`, `high`, `confirmed-conflict`, or `never`. Exit code 3 means the selected threshold was reached; input/command failures return 2.

## Docker (optional)

Docker is not required. To run the non-root, capability-dropped container with a local data volume:

```bash
docker compose up --build
```

Only `127.0.0.1:8765` is published by Compose. The image includes a health check and read-only root filesystem.

## Development and tests

```bash
./scripts/dev.sh       # Vite + FastAPI during development
./scripts/test.sh      # backend and frontend quality checks
make test
```

Individual validation commands and expected tools are in [TEST_STRATEGY.md](docs/TEST_STRATEGY.md). CI covers Python 3.11–3.13, Node 24, Chromium E2E, dependency/source security, and Windows/macOS/Ubuntu smoke tests.

## Documentation

- User guides: [English](docs/USER_GUIDE_EN.md) · [Deutsch](docs/USER_GUIDE_DE.md)
- Administrator guides: [English](docs/ADMIN_GUIDE_EN.md) · [Deutsch](docs/ADMIN_GUIDE_DE.md)
- Technical: [Architecture](docs/ARCHITECTURE.md), [decision model](docs/DECISION_MODEL.md), [knowledge-pack format](docs/KNOWLEDGE_PACK_FORMAT.md), [threat model](docs/THREAT_MODEL.md)
- Project truth: [implementation status](docs/IMPLEMENTATION_STATUS.md), [limitations](docs/LIMITATIONS.md), [roadmap](docs/ROADMAP.md)

See [CONTRIBUTING.md](CONTRIBUTING.md) and [LICENSE-NOTICE.md](LICENSE-NOTICE.md) before redistribution or contribution.
