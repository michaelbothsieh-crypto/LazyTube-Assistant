# GitHub Actions Optimization

## Current Daily Scanner Contract

`podcast-scanner.yml` is both scheduled and manually reusable through `workflow_dispatch`.

Daily mode is an incremental website data refresh:

1. Restore `processed_podcasts.json`.
2. Read website RSS sources from `data/website_kols.json`.
3. Inspect only the newest RSS entries (`PODCAST_MAX_DAILY_FEED_ITEMS`, default `12`).
4. Skip an episode if `(kol_id, guid)` already exists in `episodes`.
5. Use Redis podcast analysis cache before downloading audio or calling NotebookLM.
6. Write `episodes`, `daily_signals`, `stock_mentions`, `consensus_daily`, `job_runs`, and `job_items`.
7. Persist processed state.

## Duplicate Protection

The scanner has three layers:

- State file: `processed_podcasts.json` tracks `rss_url + guid`.
- Database SSOT: `episodes` has `UNIQUE (kol_id, guid)`.
- Preflight skip: daily mode checks DB before cache/download/NLM.

If GitHub state restore fails, the DB preflight still prevents repeated NotebookLM work for already stored episodes.

## Speed Levers

- `PODCAST_MAX_DAILY_FEED_ITEMS`: lower for fast daily refresh, raise for backfill.
- `MAX_EPISODES_PER_RUN`: hard cap in code for daily processing per source.
- Redis podcast cache: avoids audio download and NotebookLM when analysis already exists.
- DB preflight skip: avoids all work when the episode is already in the SSOT.

## Reuse Pattern

Use `podcast-scanner.yml` for website data refresh only. Use `podcast-on-demand.yml` for manual Telegram-facing analysis.

Recommended future extraction:

- Composite action for checkout + Python setup + pip cache + install.
- Reusable workflow for `restore state -> run scanner -> persist state`.
- Matrix backfill workflow for one RSS source per job when historical processing is needed.

## Backfill

For backfill, run a separate workflow or manual dispatch with a larger `PODCAST_MAX_DAILY_FEED_ITEMS`. Do not overload the daily scheduled job with historical catch-up.
