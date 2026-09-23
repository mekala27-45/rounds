# Decisions

- 2026-09-23: Use the actual seeded Synthea generator, with source/version checksums, instead of manually plausible dashboard data.
- 2026-09-23: Retain the sample population and report the full-population run as outstanding.
- 2026-09-23: Publish aggregate browser tables. Keep patient rows behind server-side access control.
- 2026-09-23: Use the available Sites/D1 runtime to deliver a working audited service. Record the departure from Fly/Neon explicitly.
- 2026-09-23: Use admission-time features for the sample readmission model. Exclude LOS and discharge disposition as inputs and label the changed prediction time.
- 2026-09-23: Reverse the initial same-day condition availability assumption. Day-precision conditions must precede the admission day.
- 2026-09-23: Insert temporal buffers because patient-specific shifts can otherwise reorder train and validation dates across people.
- 2026-09-23: Keep the prespecified interpretable model in shadow when held-out gates fail; do not pick a replacement by looking at the test result.
- 2026-09-23: Reverse the assumption that UCI can support temporal transport validation. It lacks dates; use a separate patient-disjoint benchmark.
- 2026-09-23: Keep the CMS hospital-wide series unavailable rather than substitute a condition-specific national rate.
- 2026-09-23: Label billed claims and hospitalization as two utilization-related proxies, neither a direct measure of clinical need.
- 2026-09-23: Treat the exact-description NLP result as a lexical sanity check, not independent clinical validation.
- 2026-09-23: Keep raw identities, salts, notes, source CSVs and UCI patient records out of public assets. Scan the built client for deployed patient pseudonyms.
