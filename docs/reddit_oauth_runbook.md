# Reddit URL Ingestion Runbook

This runbook describes the current operational reality for Reddit URL ingestion in Topic Shelf.

## When To Use Each Fetcher

- `reddit_public`: use this for the default local prototype path, smoke tests, and any setup where you do not have a pre-supplied OAuth token.
- `reddit_oauth`: use this MVP path only when you already have a bearer token available in the environment and you want the authenticated Reddit fetch path.

## Current OAuth Scope

`reddit_oauth` is intentionally small and bounded:

- it uses a pre-supplied bearer token from the environment
- it fetches thread JSON with the standard library only
- it parses the post, initial comments, and one bounded `MoreComments` expansion pass
- it preserves the existing raw record contract

Not implemented yet:

- token refresh
- approval / secret exchange flow
- deep recursive `MoreComments` pagination
- a broad Reddit API client abstraction

## Required Environment Variables

Core variables:

- `TOPIC_SHELF_FETCHER` for the default fetcher selection when `--fetcher` is omitted
- `TOPIC_SHELF_REDDIT_OAUTH_TOKEN` for the OAuth bearer token

Runtime config variables:

- `TOPIC_SHELF_REDDIT_REQUEST_TIMEOUT_SECONDS`
- `TOPIC_SHELF_REDDIT_MAX_RETRY_ATTEMPTS`
- `TOPIC_SHELF_REDDIT_RETRY_BACKOFF_SECONDS`
- `TOPIC_SHELF_REDDIT_TOP_COMMENT_LIMIT`
- `TOPIC_SHELF_REDDIT_MORECOMMENTS_ENABLED`
- `TOPIC_SHELF_REDDIT_MORECOMMENTS_MAX_CHILD_IDS`
- `TOPIC_SHELF_REDDIT_MORECOMMENTS_MAX_BATCHES`

## Doctor Script

Use `python_pipeline/scripts/check_reddit_ingestion_setup.py` before a real ingestion run.

It validates:

- fetcher selection
- config parsing
- OAuth token presence when `reddit_oauth` is selected
- URL list readiness when a path is provided
- output path readiness

It does not fetch data or touch Reddit.

## Common Failure Modes

- Missing token: the doctor will report a blocking error if `reddit_oauth` is selected and `TOPIC_SHELF_REDDIT_OAUTH_TOKEN` is absent.
- Invalid config: invalid values for runtime config variables fail fast during setup validation.
- Missing URL list: a provided `--url-list` path must exist.
- `401`: the bearer token is missing, invalid, or not approved for the thread.
- `403`: the token may be valid but not approved for the thread.
- `404`: the thread or `morechildren` request target was not found.
- `429`: Reddit rate limiting was hit; the fetcher keeps the failure explicit and records a rate-limit snapshot.
- transient `5xx`: the fetcher retries a small bounded number of times before failing.

## Why The Metadata Matters

OAuth-ingested raw records carry additive metadata so operators can see the settings used for a run without changing the downstream contract.

Useful fields include:

- `fetch_mode`
- `comment_fetch_mode`
- `comment_fetch_count`
- `comment_cap`
- `morechildren_enabled`
- `morechildren_request_limit`
- `request_timeout_seconds`
- `retry_policy`
- `ratelimit_snapshot`

These fields are safe to ignore downstream, but they make setup and incident review much easier.

## Safe Commands

Public path:

~~~bash
python python_pipeline/scripts/check_reddit_ingestion_setup.py --fetcher reddit_public --url-list python_pipeline/data/url_lists/claude_code_tips.txt
python python_pipeline/scripts/ingest_reddit_urls.py --fetcher reddit_public python_pipeline/data/url_lists/claude_code_tips.txt
~~~

OAuth path:

~~~bash
TOPIC_SHELF_REDDIT_OAUTH_TOKEN=... python python_pipeline/scripts/check_reddit_ingestion_setup.py --fetcher reddit_oauth --url-list python_pipeline/data/url_lists/claude_code_tips.txt
TOPIC_SHELF_REDDIT_OAUTH_TOKEN=... python python_pipeline/scripts/ingest_reddit_urls.py --fetcher reddit_oauth python_pipeline/data/url_lists/claude_code_tips.txt
~~~

## Operational Notes

- Keep `reddit_public` as the default unless you explicitly want the OAuth MVP path.
- Prefer the doctor script before ingestion when you are changing environment variables or switching fetchers.
- Treat this as a bounded, small-scale URL-seeded ingestion workflow, not a general-purpose Reddit crawler.
