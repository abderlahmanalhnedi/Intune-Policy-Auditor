# Design system

The interface uses Fluent UI foundations plus local CSS variables and Lucide icons. It avoids Microsoft logos and remote fonts.

- Brand: deep navy surfaces, indigo actions, cyan supporting accents.
- Semantic colors: green success, amber review, red danger, violet accepted deviation, gray uncertainty. Color is never the only signal; every state has text/icon/border.
- Typography: system font stack; monospace only for IDs, hashes, values, and codes.
- Spacing follows a 4/8/12/16/24/32/48 scale. Panels use consistent radii, borders, and restrained shadows.
- All interactive controls target at least 40–44 px, show `:focus-visible`, and remain keyboard operable.
- Tables have captions, column headers, a focusable scroll region, bounded pagination, and empty states.
- Charts include hidden textual alternatives.
- The sidebar collapses below 760 px and is Escape-dismissable. At 1024 px, content and navigation remain visible without requiring a large display.
- Guided Mode emphasizes questions/actions; Expert Mode reveals raw IDs, paths, and trace. Mode changes presentation only.
- System/light/dark themes use the same semantics. Reduced-motion preferences disable nonessential motion.

All visible strings belong in the paired German/English i18n resources. New keys require parity tests.
