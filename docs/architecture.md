# Topic Shelf Architecture

## What Topic Shelf Is

Topic Shelf is a low-volume Reddit curation workflow. It helps collect a small set of promising threads, turn them into a stable internal format, and optionally generate downstream assets for review and publishing.

## Why There Are Two Input Paths

The repository has two ways to create raw input because the collection step can happen in two practical ways.

### Devvit keep export

This is the main entry path. A Devvit dashboard runs on Reddit, shows candidate posts, and lets a human mark keep or skip. The kept set can then be exported as raw JSON for the Python pipeline.

### V3 URL list ingestion

This is an alternate bridge path. Instead of starting inside Devvit, a human-curated text file of Reddit thread URLs is ingested and converted into raw JSON. After that point, it follows the same pipeline as a Devvit export.

## Core Processing Contract

The core contract is:

`raw JSON -> normalized -> cards`

This is the stable middle of the system. Input methods can vary, but once data is in raw JSON form, the downstream flow stays the same.

## Optional Downstream Stages

After cards are created, later stages can be enabled as needed:

- summary
- translation
- topics
- bundles
- blog drafts
- quality review
- publish markdown

These stages build on the same card-oriented output rather than changing the core contract.

## Design Principles

- preserve the downstream contract
- prefer additive stages
- keep input methods replaceable
- human-curated, low-volume workflow first

## Practical Mental Model

### Input layer

Either collect keep items in Devvit or ingest a small URL list. Both paths exist to create raw JSON.

### Core pipeline

Take raw JSON through normalization and card building. This is the part that should stay easiest to reason about.

### Optional enrichment and publishing layer

Run only the later stages you need after cards exist. These enrich or package the output, but they do not redefine the core pipeline.
