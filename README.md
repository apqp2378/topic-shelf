# Topic Shelf

Topic Shelf is a small Reddit curation system. It combines a Devvit candidate picker for collecting keep-worthy threads with a Python post-processing pipeline that turns those kept items into normalized records, cards, and optional downstream publishing assets.

## What This Repo Contains

- `Devvit candidate picker`: the in-Reddit review dashboard used to collect and export keep-style raw JSON
- `V3 URL bridge`: a small alternate input path that turns a human-curated Reddit URL list into raw JSON
- `Python pipeline`: the core processing layer that takes raw input through normalization, card building, and optional later stages

## Core Flow

`Devvit keep export OR URL list -> raw JSON -> normalized -> cards -> optional stages`

## Repository Structure

- `src/`: Devvit web app source
- `public/`: Devvit static assets
- `tools/`: Devvit support scripts
- `python_pipeline/`: Python processing pipeline, scripts, tests, and pipeline data folders
- `data/`: sample root-level data used by the repo

## Fastest Ways To Use This Repo

### Path A: Devvit keep export flow

1. Start the Devvit app locally.
2. Review candidates in the dashboard and mark keep/skip.
3. Export the keep set as raw JSON.
4. Run the Python pipeline on that raw JSON.

### Path B: V3 URL list flow

1. Put a small human-curated Reddit URL list into `python_pipeline/data/url_lists/`.
2. Run the URL ingestion step to create raw JSON.
3. Run the Python pipeline on that raw JSON.

## Where To Read Next

- `python_pipeline/README.md`
- `docs/architecture.md`
