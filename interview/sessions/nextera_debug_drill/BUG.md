# Spoiler — only after you’ve debugged

**Failing test:** `test_daily_totals_groups_by_site_and_utc_date`

**Root cause:** `daily_totals` sorts by `(total, site, day)` instead of `(site, day)`.
Aggregation is fine; output order doesn’t match the contract.

**Fix:** `rows.sort(key=lambda r: (r[0], r[1]))`

**Owner follow-ups to practice saying out loud:**
- Config for timezone policy (always UTC vs site-local)
- Typed models / pydantic instead of raw tuples
- Structured logging + metrics on ingest volume
- CI: pytest + ruff; Docker image; deploy to ECS/Fargate
- Idempotent ingest if readings can be replayed
