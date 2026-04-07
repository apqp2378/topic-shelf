# Batch Quality Checklist

Use this checklist after a URL-list batch moves through the V3 flow:

`URL list -> raw -> normalized -> cards -> review sidecars -> publish_candidates -> blog_draft_seeds`

## 1. Ingestion
- [ ] URL list exists under `python_pipeline/data/url_lists/`
- [ ] `check_reddit_ingestion_setup.py` passes with `reddit_public`
- [ ] `ingest_reddit_urls.py` succeeds with no unexpected failures
- [ ] Input URL count matches the intended batch size
- [ ] Raw JSON is written under `python_pipeline/data/raw/`

## 2. Cards
- [ ] `run_pipeline.py` validates the raw JSON
- [ ] Normalized JSON is written under `python_pipeline/data/normalized/`
- [ ] Cards JSON is written under `python_pipeline/data/cards/`
- [ ] Card count matches the raw keep count
- [ ] Card titles and source URLs look usable for review

## 3. Review Sidecars
- [ ] `init_batch_review.py` creates `*_review.md` and `*_decisions.json`
- [ ] Review notes stay in sidecar files, not inside cards JSON
- [ ] Decisions are clear enough to explain publish vs hold
- [ ] The batch has at least one sensible publish candidate, if the topic supports it

## 4. Publish Candidates
- [ ] `export_publish_candidates.py` succeeds
- [ ] Export JSON and markdown are both written
- [ ] Candidate count matches the reviewed decisions
- [ ] Candidate entries preserve source URL, title, subreddit, and review note

## 5. Blog Draft Seeds
- [ ] `export_blog_draft_seeds.py` succeeds
- [ ] Draft seeds are written only for publish candidates
- [ ] Draft seed filenames are stable and readable
- [ ] Draft seeds are useful starting points for writing, not final copy

## 6. Fetcher Sanity
- [ ] `reddit_public` still works for the batch
- [ ] Failures look like content issues, not setup issues
- [ ] No OAuth token is required for validation

## 7. Batch Readout
- [ ] Note the counts for input URLs, successful ingestion, cards, publish candidates, and blog seeds
- [ ] Record any quality concerns in one sentence
- [ ] Decide whether `reddit_public` still looks good enough for the next 1 to 2 batches

## Canonical Example
- Use `python_pipeline/data/url_lists/claude_code_tips.txt` as the canonical example URL-list file.
- Do not reintroduce `my_threads.txt`.

## Operating Rules
- Production batches should usually be narrow, practical, and tips-oriented so they can plausibly produce publish candidates.
- Baseline batches can be broader or news-oriented when the goal is coverage, monitoring, or negative signal collection.
- A small batch size, roughly 3 to 10 URLs, is preferred for validation runs.
- Review decisions should stay in sidecar files, and holds are acceptable when the batch is genuinely low-yield.
