# Topic Shelf

Topic Shelf is a personal Reddit curation pipeline.

It has two main parts:

1. **Devvit candidate picker dashboard**
2. **Python post-processing pipeline**

End-to-end flow:

`Reddit candidates -> human keep/skip review -> raw JSON -> normalized -> cards -> summary / translation / topics -> bundles -> blog drafts -> quality reviews -> publish markdown`

## Project Overview

This repository is not just a Devvit dashboard.

It combines:

- a **Devvit moderation-style candidate picker** for collecting and reviewing Reddit posts
- a **Python pipeline** for turning selected raw exports into reusable structured assets

The Devvit side is the entry point.  
The Python side is the processing pipeline.

## Repository Structure

- `src/`, `public/`, `tools/`: Devvit app source
- `python_pipeline/`: raw-to-normalized/cards/post-processing pipeline
- `data/raw/`: sample raw export data
- `python_pipeline/data/`: pipeline input/output folders

## Setup

1. Install dependencies with `npm install`
2. Update `devvit.json` if you want a different development subreddit than `your_test_subreddit`
3. Log in with `npm run login`
4. Start the app with `npm run dev`
5. From the subreddit menu, use `Open candidate picker dashboard` to create the dashboard post

## Commands

### Devvit

- `npm run dev`: Start local Devvit playtest mode
- `npm run build`: Build client and server bundles
- `npm run type-check`: Run TypeScript project references
- `npm run lint`: Run ESLint
- `npm run test -- my-file-name`: Run a specific Vitest file

### Python pipeline

See `python_pipeline/README.md` for detailed pipeline usage.

Typical flow:

- generate or export raw JSON
- run the Python pipeline
- inspect normalized/cards/bundles/blog draft outputs

## Devvit Pages

- `CandidateListPage`: Main moderation queue with status filter, score/latest/comment sorting, quick status actions, manual refresh, and detail navigation
- `CandidateDetailPage`: Full candidate review view with metadata, reason tags, top comments, status controls, and moderator review note editing
- `ExportPage`: Shows the current `keep` set and provides plain-text, Markdown, and raw JSON export paths for downstream processing

## Scheduler

- `refresh-candidates` runs every 2 hours via `/internal/scheduler/refresh-candidates`
- The refresh fetches 30 recent posts plus top 5 comments per post from the installed subreddit
- Candidate content, metrics, score, and reason tags are refreshed
- Human-entered `status` and `review_note` are preserved and never overwritten
- Recommended status is shown alongside moderator status in list and detail views
- Export endpoints include:
  - `/api/export/keep-links`
  - `/api/export/keep-markdown`
  - `/api/export/keep-raw-json`

## Python Pipeline

The Python pipeline reads keep-style raw JSON and produces downstream assets such as:

- normalized records
- cards
- summaries
- translations
- topic classification
- bundles
- blog drafts
- quality reviews
- publish markdown

It can also accept a small human-curated Reddit URL list through the V3 URL bridge and convert it into raw JSON for the same downstream flow.

For execution details, use:

- `python_pipeline/README.md`

## Run Checklist

### Devvit

- `devvit.json` points at your test subreddit
- The app is installed in that subreddit
- The moderator dashboard post opens successfully
- Candidate refresh returns recent subreddit posts
- Status and review note updates persist across refreshes
- Export copy actions return the expected `keep` links

### Python pipeline

- raw JSON is generated or exported successfully
- normalized output is created
- cards output is created
- optional stages run only when explicitly enabled