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

- `python_pipeline/data/raw/raw_from_urls_my_threads.json`
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
python python_pipeline/scripts/ingest_reddit_urls.py python_pipeline/data/url_lists/my_threads.txt
python python_pipeline/scripts/run_pipeline.py python_pipeline/data/raw/raw_from_urls_my_threads.json
~~~

## Notes

- The current practical input path is the V3 URL bridge flow.
- Devvit remains an optional input path for manually reviewed keep exports.
- The stable center of the pipeline is the same in both cases: `raw JSON -> normalized -> cards`.