# Evidence model

A Microsoft-alignment conclusion requires all of the following:

- exact normalized Intune setting ID (or an explicit reviewed alias);
- exact configured-value interpretation;
- matching platform and compatible user/device scope;
- selected Microsoft product, baseline, and version;
- applicable official evidence with verification date;
- deterministic comparison rule and no unresolved ambiguity.

Official Microsoft claims are restricted to verified Microsoft domains listed in `MICROSOFT_SOURCE_POLICY.md`. Apple behavior may use official Apple documentation but is never described as a Microsoft baseline.

Evidence confidence is separate from extraction confidence. Successfully extracting `true`, `false`, `allow`, `block`, or a name containing `disable` says nothing about whether that value is secure. Regex, category, display-name similarity, fuzzy matching, and AI cannot satisfy the evidence gate.

Each source records type, title, URL/domain, publication/verification date where known, optional hash, confidence, and official flag. Pack metadata records input hashes/importer/version. Every setting evaluation stores a stepwise trace.

Stale evidence raises a warning; it is not silently invalidated. Missing or ambiguous evidence returns `Not evaluable / Nicht bewertbar` and preserves reasons for remediation.
