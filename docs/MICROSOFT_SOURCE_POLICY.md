# Microsoft source policy

Verified on 2026-08-03. Microsoft-alignment data may use `learn.microsoft.com`, `microsoft.com`, `download.microsoft.com`, `graph.microsoft.com`, and relevant official Microsoft GitHub organizations. Search snippets, forums, blogs, copied spreadsheets, vendor marketing, and AI output are not authoritative.

The official [Intune security-baseline overview](https://learn.microsoft.com/en-us/intune/device-security/security-baselines/overview) identified Windows baseline 25H2, Defender for Endpoint 24H1, Microsoft 365 Apps 2512, Edge 139, and Windows 365 24H1 as the newest listed instances at verification time. The [official SCT download](https://www.microsoft.com/en-us/download/details.aspx?id=55319) was dated 2026-02-23 and offered Windows 11 v25H2, Edge v139, and Microsoft 365 Apps 2512 archives. Versions change; re-check before every production import.

No official pack ships with this repository. Seeing a version name is insufficient to create exact Intune IDs/value semantics, so production mappings were not fabricated. Official status is **not installed**.

For every source, capture the final URL/domain, title, product/version, published and verified dates, source/artifact SHA-256 where possible, and reviewer. Follow redirects and reject unofficial final domains. Prefer the precise baseline settings/CSP page over summaries. Graph endpoint and permission claims require their operation documentation.

Sources older than 180 days are flagged stale, not automatically invalid. Missing, moved, ambiguous, or version-incompatible evidence produces `Not evaluable`; it never falls back to an older recommendation silently.
