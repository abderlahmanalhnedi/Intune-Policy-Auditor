# Knowledge-pack format

A pack directory contains `manifest.json` and the manifest-named settings file (normally `settings.json`). JSON Schemas are under `knowledge-packs/schema`.

The manifest identifies schema/pack/vendor/product/baseline/version/platform/source, publication/import/verification dates, SHA-256 hashes, application version, status, counts, notes, and provenance. `data_sha256` hashes the exact settings-file bytes; `schema_sha256` hashes the bundled setting schema.

A setting supplies a canonical ID, platform/scope, localized name/category/description, baseline value, typed allowed/semantic mappings, comparison rule, sourced applicability, impact in both directions, optional sourced restart/sign-in/connectivity behavior, reviewed aliases, evidence sources, and an optional less-restrictive severity.

Validation rejects unsupported schema versions, hashes/count mismatches, duplicate IDs, aliases/collisions, missing versions/platform/evidence, nonofficial domains for Microsoft claims, duplicate ordered values, invalid canonical values/rules, and Critical impact without exact official evidence. ZIP import additionally rejects traversal, symlinks, nested archives, executable members, excessive size/count/ratio, and extra layouts.

Pack status is `synthetic`, `verified`, `pending_review`, or `invalid`. `pending_review` content cannot become exact merely by import. Pack IDs are stable; revisions use an updated baseline version and data hash.
