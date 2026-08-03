# Knowledge-pack maintenance

1. Identify the exact product/baseline instance from an official source.
2. Record the retrieval date, final URL/domain, publication/version details, and hashes of supplied artifacts.
3. Map only documented Intune canonical IDs and value semantics. Keep uncertain records in a review queue.
4. Add short original factual summaries rather than copied documentation.
5. Define applicability/comparison/impact only when sourced. Leave unsupported facts absent.
6. Recalculate settings/schema hashes and counts, validate with the CLI, and run trust tests.
7. Have a second reviewer confirm IDs, values, source and version. Mark verified only after review.
8. Activate explicitly. Retain prior immutable versions for reproducibility.

Run:

```bash
python -m intune_auditor.cli.main validate-pack PATH
```

Exit 0 is valid, 1 is structurally invalid, and 2 is a command/input failure. The SCT importer accepts user-supplied XML/ZIP and preserves ambiguous source records as pending review. It does not redistribute Microsoft archives.

Review freshness at least every 180 days and whenever Microsoft publishes a new instance. A stale pack remains usable for historical reproduction, but the UI warns and a new audit should deliberately select the intended version.
