# ADR 001: Podcast Signal SSOT

## Status

Accepted

## Context

The web product should not be a static summary page. Daily automation must produce auditable finance intelligence that the website can read without re-deriving business logic in React.

## Decision

Use Postgres tables as the system of record:

- `episodes`: raw analyzed podcast episode output.
- `job_runs` and `job_items`: automation observability for each scanner run and source.
- `daily_signals`: finance signal SSOT derived from analyzed episodes.
- `consensus_daily` and `stock_mentions`: read models derived from `episodes` and `daily_signals`.

The daily podcast scanner is responsible for updating website data. Telegram reporting is opt-in and reserved for manual/on-demand workflows.

## Consequences

- The website reads `daily_signals` and automation status directly from Neon.
- Data quality can be audited from `job_runs` and `job_items`.
- Future scoring improvements belong in the backend derivation layer, not in frontend components.
- If a new database is empty, the scanner creates required tables before writing data.

## Trade-offs

- This keeps the system simple and inspectable, but the first version of confidence scoring is heuristic.
- Market price snapshots are best-effort and nullable; signal creation must not fail because a price provider is unavailable.
