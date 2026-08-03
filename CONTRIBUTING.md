# Contributing

Contributions must preserve the evidence-first and read-only invariants.

1. Create a focused branch; never commit secrets, tokens, tenant payloads, or Microsoft archives.
2. Run setup, then `./scripts/test.sh` and relevant Playwright tests.
3. Add synthetic fixtures and tests for behavior changes.
4. Regenerate `backend/openapi.json` and `frontend/src/api/schema.d.ts` after API changes.
5. Explain evidence provenance for any knowledge change. Microsoft judgments require exact official sources, identifiers, value semantics, and comparison rules.

Regex, keywords, fuzzy matching, AI, or display-name similarity may assist search only. They must never create alignment or severity. Graph additions require a documented read-only semantic review, minimal delegated read scope, explicit operation allowlisting, and mocked HTTP tests. No ReadWrite scope is acceptable.

Use Ruff formatting, strict MyPy/TypeScript, ESLint, Bandit, pytest, Vitest, and Playwright. Do not weaken tests to pass. Report security issues privately through the repository host's security-advisory mechanism; do not attach real tenant data.

This project is independent and is not affiliated with or endorsed by Microsoft.
