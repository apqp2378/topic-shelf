# Reddit API Approval Prep

This project is currently best described as a personal, small-scale, URL-seeded ingestion workflow.

It is not intended as:

- bulk export tooling
- broad scraping infrastructure
- model-training ingestion

## Current Safety Posture

The current implementation keeps scope narrow:

- bounded fetch scope
- additive metadata on raw records
- purge support for generated raw ingestion outputs
- setup validation via the doctor script
- limited one-pass `MoreComments` expansion
- default `reddit_public` path remains available

## Already In Place

- `reddit_public` for the local prototype path
- `reddit_oauth` MVP using a pre-supplied bearer token
- shared parser for common Reddit payload fields
- shared comment normalization and cap helpers
- runtime config for timeout, retries, comment cap, and MoreComments controls
- additive metadata on raw records
- preflight / doctor validation
- raw purge helper for generated URL-ingestion output

## Still Needed For Production-Ready OAuth

- token refresh
- approval / secret exchange flow
- stronger OAuth error handling and observability
- deeper recursive `MoreComments` pagination if that is still desired
- clearer operator metrics or telemetry if the workflow grows
- a final decision on whether OAuth should remain a narrow ingestion path or become a broader client

## How To Think About The Current State

The current OAuth path is a constrained ingestion bridge:

- it validates setup
- it fetches only what is needed for the current raw contract
- it keeps the downstream `raw JSON -> normalized -> cards` flow unchanged

That makes it suitable for experimentation and controlled use, but not yet for a broad, production-scale Reddit integration.
