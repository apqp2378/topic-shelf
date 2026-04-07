## 한국어 요약
Topic Shelf는 Reddit 글을 선별해
`raw JSON -> normalized -> cards` 구조로 변환하는 개인 큐레이션 시스템입니다.
현재는 Python pipeline 중심으로 운영하고 있으며,
사람이 고른 Reddit URL 목록을 V3 URL bridge로 처리하는 흐름을 주력으로 사용합니다.
Devvit은 선택적으로 후보 글을 keep/skip으로 검토하고,
keep로 표시한 결과를 raw JSON으로 export하는 입력 경로입니다.

# Topic Shelf

Topic Shelf is a small Reddit curation system centered on a Python processing pipeline.
It takes either a human-curated Reddit URL list or an optional Devvit keep export,
then turns that input into raw JSON, normalized records, cards, and optional downstream publishing assets.

## What This Repo Contains

- `Python pipeline`: the core processing layer that takes raw input through normalization, card building, and optional later stages
- `V3 URL bridge`: the current practical input path that turns a human-curated Reddit URL list into raw JSON
- `Devvit candidate picker`: an optional in-Reddit review dashboard where I mark candidate threads as keep/skip and export the kept set as raw JSON

## Core Flow

`URL list OR Devvit keep export -> raw JSON -> normalized -> cards -> optional stages`

## Repository Structure

- `src/`: Devvit web app source
- `public/`: Devvit static assets
- `tools/`: Devvit support scripts
- `python_pipeline/`: Python processing pipeline, scripts, tests, and pipeline data folders
- `data/`: sample root-level data used by the repo

## Fastest Ways To Use This Repo

### Path A: V3 URL list flow

1. Put a small human-curated Reddit URL list into `python_pipeline/data/url_lists/`.
2. Use `python_pipeline/data/url_lists/claude_code_tips.txt` as the canonical example file when you need a concrete path in docs or tests.
3. Run the URL ingestion step to create raw JSON.
4. Run the Python pipeline on that raw JSON.
5. Generate a batch review scaffold and export publish candidates from the completed review sidecar.
6. Export blog draft seeds from the publish-candidate handoff and edit those drafts manually.

### Path B: Devvit keep export flow

1. Start the Devvit app locally.
2. Review candidates in the dashboard and mark keep/skip.
3. Export the keep set as raw JSON.
4. Run the Python pipeline on that raw JSON.

## Batch Selection

- Production batches are narrow, practical, tips-oriented URL lists that are likely to produce publish candidates and blog draft seeds.
- Baseline batches can be broader or news-oriented when the goal is coverage, monitoring, or a low-yield comparison set.
- A small batch size, roughly 3 to 10 URLs, is the safest default for validation runs.
- Success means the batch moves cleanly through `raw JSON -> normalized -> cards -> review sidecars -> publish_candidates -> blog_draft_seeds`.
- Keep using `reddit_public` for near-term validation while it is passing preflight and ingest cleanly.
- The RSS helper stage can generate `auto_*.txt` URL lists, but it does not replace the manual URL-list workflow.
- Use `python_pipeline/data/url_lists/claude_code_tips.txt` as the canonical example URL-list file.
- Do not reintroduce `my_threads.txt`.

## Where To Read Next

- `python_pipeline/README.md`
- `docs/architecture.md`
- `docs/reddit_oauth_runbook.md`
- `docs/reddit_api_approval_prep.md`
- `python_pipeline/scripts/init_batch_review.py`
- `python_pipeline/scripts/export_publish_candidates.py`
- `python_pipeline/scripts/export_blog_draft_seeds.py`
