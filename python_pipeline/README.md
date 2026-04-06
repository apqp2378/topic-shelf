# Python Pipeline

This pipeline is the core processing layer for Topic Shelf.

See also: `../docs/architecture.md`

It also includes a small smoke test for the core `raw -> normalized -> cards` path.

It takes either V3 URL-derived raw Reddit JSON or Devvit keep-style raw JSON and turns that input into structured downstream assets such as normalized records, cards, summaries, translations, topic labels, bundles, blog drafts, quality reviews, and publish-ready Markdown.

## Purpose

The pipeline is designed to work with:

1. **V3 URL-seeded raw JSON** generated from a small human-curated Reddit thread URL list
2. **Devvit keep raw JSON exports**

The downstream pipeline contract stays the same in both cases:

`raw JSON -> normalized -> cards -> optional stages`

## Input Location

Expected raw input folder:

- `python_pipeline/data/raw/`

Example raw input files:

- `python_pipeline/data/raw/raw_from_urls_claude_code_tips.json`
- `python_pipeline/data/raw/devvit_keep_2026-04-05.json`
- `python_pipeline/data/raw/devvit_keep_multi.json`

## Output Location

Primary output folders:

- `python_pipeline/data/normalized/`
- `python_pipeline/data/cards/`
- `python_pipeline/data/publish/`

## Core Scripts

- `validate_raw.py`  
  Checks JSON shape, required fields, keep status, and `top_comments`

- `normalize_devvit_raw.py`  
  Converts keep-style raw JSON into the internal normalized structure used by the pipeline

- `make_cards.py`  
  Converts normalized records into card objects

- `ingest_reddit_urls.py`  
  Reads a human-curated Reddit thread URL txt list and writes raw JSON that `run_pipeline.py` can read directly

- `run_pipeline.py`  
  Runs validation, normalization, and card generation in one command and can optionally enable later stages

## Basic Execution Flow

### Core raw pipeline flow

This flow works for both Devvit keep exports and V3 URL-derived raw JSON.

1. Validate raw JSON
2. Normalize raw JSON
3. Build cards

Or run everything at once with `run_pipeline.py`.

### Current practical path: V3 URL bridge flow

1. Put a small human-curated txt file of Reddit thread URLs into `python_pipeline/data/url_lists/`
2. Run `ingest_reddit_urls.py`
3. Feed the generated raw JSON into `run_pipeline.py`

Flow:

`txt URL list -> ingest_reddit_urls.py -> raw JSON -> run_pipeline.py`

### Optional path: Devvit keep export flow

1. Export the kept set as raw JSON from the Devvit review flow
2. Feed that raw JSON into `run_pipeline.py`

## Example Commands

### Basic raw pipeline

~~~bash
python python_pipeline/scripts/validate_raw.py python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/normalize_devvit_raw.py python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/make_cards.py python_pipeline/data/normalized/normalized_devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py python_pipeline/data/raw/devvit_keep_2026-04-05.json
~~~

### V3 URL bridge flow

~~~bash
python python_pipeline/scripts/ingest_reddit_urls.py python_pipeline/data/url_lists/claude_code_tips.txt
python python_pipeline/scripts/run_pipeline.py python_pipeline/data/raw/raw_from_urls_claude_code_tips.json
~~~

### Choosing a fetcher

The URL ingestion entrypoint supports a fetcher selector so the current public prototype and the future OAuth path can share the same command shape.

Default behavior stays the same:

- CLI default: `reddit_public`
- Env var fallback: `TOPIC_SHELF_FETCHER`

Examples:

~~~bash
python python_pipeline/scripts/ingest_reddit_urls.py --fetcher reddit_public python_pipeline/data/url_lists/claude_code_tips.txt
TOPIC_SHELF_FETCHER=reddit_oauth python python_pipeline/scripts/ingest_reddit_urls.py python_pipeline/data/url_lists/claude_code_tips.txt
~~~

Current fetchers:

- `reddit_public`: local prototype / smoke-test oriented fetcher that reads Reddit public JSON
- `reddit_oauth`: MVP OAuth fetcher for a pre-supplied bearer token

### OAuth prep layer

The repository now includes two small scaffolding modules for the future OAuth path:

- `pipeline/url_fetchers/token_provider.py` for loading and later caching bearer tokens
- `pipeline/url_fetchers/comment_expander.py` for shaping comment normalization and future `MoreComments` expansion

These modules are intentionally lightweight. They prepare the structure for a real OAuth fetcher, but they do not perform live token exchange or API approval flows yet.

To run the MVP OAuth path, provide a bearer token in:

- `TOPIC_SHELF_REDDIT_OAUTH_TOKEN`

Example:

~~~bash
TOPIC_SHELF_REDDIT_OAUTH_TOKEN=... python python_pipeline/scripts/ingest_reddit_urls.py --fetcher reddit_oauth python_pipeline/data/url_lists/claude_code_tips.txt
~~~

### Batch review scaffold

After cards are generated, create review sidecars for a completed batch:

~~~bash
python python_pipeline/scripts/init_batch_review.py claude_code_tips
python python_pipeline/scripts/init_batch_review.py python_pipeline/data/cards/cards_raw_from_urls_claude_code_tips.json
~~~

The review scaffold writes two human-editable files under `python_pipeline/data/reviews/`:

- `<stem>_review.md`
- `<stem>_decisions.json`

It does not modify raw, normalized, or cards outputs.

### Runtime config

The Reddit fetchers also read a small set of optional environment variables:

- `TOPIC_SHELF_REDDIT_REQUEST_TIMEOUT_SECONDS` default `20.0`
- `TOPIC_SHELF_REDDIT_MAX_RETRY_ATTEMPTS` default `3`
- `TOPIC_SHELF_REDDIT_RETRY_BACKOFF_SECONDS` default `0.25`
- `TOPIC_SHELF_REDDIT_TOP_COMMENT_LIMIT` default `5`
- `TOPIC_SHELF_REDDIT_MORECOMMENTS_ENABLED` default `true`
- `TOPIC_SHELF_REDDIT_MORECOMMENTS_MAX_CHILD_IDS` default `5`
- `TOPIC_SHELF_REDDIT_MORECOMMENTS_MAX_BATCHES` default `1`

These settings are intentionally small and local. They keep the default public path working while making the OAuth MVP easier to operate.

Example commands:

~~~bash
# Default public prototype
python python_pipeline/scripts/ingest_reddit_urls.py --fetcher reddit_public python_pipeline/data/url_lists/claude_code_tips.txt

# MVP OAuth path with a bearer token
TOPIC_SHELF_REDDIT_OAUTH_TOKEN=... python python_pipeline/scripts/ingest_reddit_urls.py --fetcher reddit_oauth python_pipeline/data/url_lists/claude_code_tips.txt

# Disable bounded MoreComments expansion for OAuth
TOPIC_SHELF_REDDIT_OAUTH_TOKEN=... TOPIC_SHELF_REDDIT_MORECOMMENTS_ENABLED=false python python_pipeline/scripts/ingest_reddit_urls.py --fetcher reddit_oauth python_pipeline/data/url_lists/claude_code_tips.txt

# Raise the shared top-comment cap
TOPIC_SHELF_REDDIT_TOP_COMMENT_LIMIT=8 python python_pipeline/scripts/ingest_reddit_urls.py --fetcher reddit_public python_pipeline/data/url_lists/claude_code_tips.txt
~~~

This MVP path:

- uses an already-supplied bearer token
- fetches the initial thread payload with the standard library only
- parses the post and initial top-level comments
- performs one bounded `MoreComments` expansion pass when expandable ids are present
- keeps the current `top_comments` raw field and shared comment cap
- attaches additive metadata such as `fetch_mode`, `comment_fetch_mode`, `comment_fetch_count`, `comment_fetch_depth`, `ratelimit_snapshot`, and `expandable_comment_ids`
- detects initial `MoreComments` placeholders, requests a small bounded follow-up batch, and preserves the requested ids in metadata
- records additive runtime metadata such as `comment_cap`, `morechildren_enabled`, `morechildren_request_limit`, `request_timeout_seconds`, and `retry_policy`

### Shared parser layout

`reddit_public` and `reddit_oauth` now share a small internal parser module for common Reddit payload parsing.

Ownership stays split on purpose:

- `pipeline/url_fetchers/reddit_parser.py`: raw Reddit post and thread parsing helpers
- `pipeline/url_fetchers/comment_expander.py`: shared comment normalization and cap helpers
- `reddit_public.py` and `reddit_oauth.py`: fetcher-specific network transport, retry, and rate-limit handling

The runtime config behavior and additive metadata behavior are unchanged by this refactor.

### Preflight doctor

Use the doctor script to validate setup before running ingestion. It checks fetcher selection, runtime config, token presence for OAuth, URL list readiness, and output directory readiness. It does not fetch data.

Examples:

~~~bash
# Public path
python python_pipeline/scripts/check_reddit_ingestion_setup.py --fetcher reddit_public --url-list python_pipeline/data/url_lists/claude_code_tips.txt

# OAuth path
TOPIC_SHELF_REDDIT_OAUTH_TOKEN=... python python_pipeline/scripts/check_reddit_ingestion_setup.py --fetcher reddit_oauth --url-list python_pipeline/data/url_lists/claude_code_tips.txt

# Check a specific URL list file
python python_pipeline/scripts/check_reddit_ingestion_setup.py --url-list python_pipeline/data/url_lists/claude_code_tips.txt
~~~

Blocking errors are things that would prevent a successful ingestion run, such as an invalid fetcher, missing OAuth token, invalid config, or a missing URL list file. Warnings are non-blocking setup notes, such as not providing a URL list for inspection.

The doctor script uses the same fetcher resolution and config loading as ingestion, but it never performs any network fetches.

Not implemented yet:

- token refresh
- approval workflow
- secret exchange
- deep comment pagination
- recursive `MoreComments` expansion beyond one batch
- a broad Reddit API client abstraction

### Raw retention and purge

Generated raw ingestion files can be cleaned up with the purge helper:

~~~bash
python python_pipeline/scripts/purge_old_raw.py --older-than-days 7 --dry-run
python python_pipeline/scripts/purge_old_raw.py --older-than-days 7 --apply
python python_pipeline/scripts/purge_old_raw.py --older-than-hours 24 --apply
~~~

The purge helper only targets generated URL-ingestion outputs that match `raw_from_urls_*.json` under `python_pipeline/data/raw/`.

It does not delete arbitrary raw files, fixtures, or sample inputs.

## Notes

- The current practical input path is the V3 URL bridge flow.
- Devvit remains an optional input path for manually reviewed keep exports.
- The stable center of the pipeline is the same in both cases: `raw JSON -> normalized -> cards`.
- The public URL fetcher is intentionally still the local prototype path until the OAuth flow is implemented.
- `reddit_public` remains the default current path unless `--fetcher reddit_oauth` or `TOPIC_SHELF_FETCHER=reddit_oauth` is selected.
- Use `python_pipeline/data/url_lists/claude_code_tips.txt` as the canonical example URL-list file in docs and tests.
- The local URL-list files under `python_pipeline/data/url_lists/` that are meant only for personal churn are ignored intentionally.
- During stabilization, prefer fixture-backed tests and stubbed fetchers over live network fetches.
