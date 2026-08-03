# Test strategy

Synthetic fixtures only; no live Graph or tenant data enters tests.

Backend unit/integration/security tests cover identifiers, all comparator families, evidence/severity/trust gates, deviations, applicability, coverage/decisions, assignment/conflict cases, ZIP/CSV/HTML safety, pack/SCT validation, cache keys, API/CLI/privacy, PDF/report paths, and mocked Graph pagination/retry/partial failures. Strict Ruff/MyPy/Bandit and compileall run in CI across Python 3.11–3.13.

Frontend Vitest/Testing Library covers translation parity, state badges, metric unavailable semantics, modes/themes, filters, table pagination/empty states, query errors/loading, and keyboard navigation. Playwright Chromium covers production start, demo and local audits, single/multiple JSON, ZIP, malformed input, pack selection, deviations, primary routes, downloads, German/English, Guided/Expert, light/dark, not-evaluable/conflicts, and 1024×768.

Run from root:

```bash
./scripts/test.sh
cd backend && .venv/bin/pytest --cov=intune_auditor --cov-report=term-missing
cd frontend && npm run test -- --run
cd frontend && npx playwright install chromium && npm run test:e2e
python scripts/smoke.py
```

Validation must report exact pass/fail counts and warnings. Do not delete/weaken tests. A live tenant is excluded; Graph HTTP is mocked. Windows/macOS/Ubuntu production smoke runs in GitHub Actions.
