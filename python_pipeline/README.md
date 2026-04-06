# Python Minimal Pipeline 0.1

This pipeline is the smallest Python handoff for the Devvit keep raw JSON export.
It validates Devvit raw JSON, converts it into a normalized internal format, and
builds minimal card JSON for later expansion.

## Input location

- Expected raw input folder: `python_pipeline/data/raw/`
- Example input file:
  `python_pipeline/data/raw/devvit_keep_2026-04-05.json`

## Output location

- Normalized output folder: `python_pipeline/data/normalized/`
- Cards output folder: `python_pipeline/data/cards/`

## Scripts

- `validate_raw.py`: Checks JSON shape, required fields, keep status, and `top_comments`
- `normalize_devvit_raw.py`: Converts Devvit raw JSON into the internal normalized structure
- `make_cards.py`: Converts normalized records into small card objects
- `ingest_reddit_urls.py`: Fetches a human-curated Reddit thread URL txt list and writes raw JSON that `run_pipeline.py` can read directly
- `run_pipeline.py`: Runs validation, normalization, and card generation in one command and prints stage counts
- `run_pipeline.py --enable-summary`: Adds the optional heuristic summary stage and writes a second card export
- `run_pipeline.py --enable-summary --summary-provider openai`: Uses the optional summary provider adapter with safe fallback
- `run_pipeline.py --enable-translation`: Adds the optional translation scaffold and writes a third card export
- `run_pipeline.py --enable-topic-classification`: Adds the optional topic classification scaffold and writes a fourth card export
- `run_pipeline.py --enable-bundles`: Adds the optional bundle scaffold and writes a separate bundle export
- `run_pipeline.py --enable-blog-drafts`: Adds the optional blog draft scaffold and writes a separate draft export
- `run_pipeline.py --enable-blog-drafts --blog-draft-provider openai`: Uses the optional blog draft provider adapter with safe fallback
- `run_pipeline.py --enable-quality-review`: Adds the optional quality review scaffold and writes a separate review export
- `run_pipeline.py --enable-publish-export`: Adds the optional publish export scaffold and writes a separate Markdown export

## Example commands

```bash
python python_pipeline/scripts/validate_raw.py python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/normalize_devvit_raw.py python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/make_cards.py python_pipeline/data/normalized/normalized_devvit_keep_2026-04-05.json
python python_pipeline/scripts/ingest_reddit_urls.py python_pipeline/data/url_lists/my_threads.txt
python python_pipeline/scripts/run_pipeline.py python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py --enable-summary python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py --enable-summary --summary-provider openai python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py --enable-translation python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py --enable-summary --enable-translation python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py --enable-topic-classification python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py --enable-summary --enable-topic-classification python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py --enable-translation --enable-topic-classification python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py --enable-summary --enable-translation --enable-topic-classification python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py --enable-bundles python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py --enable-summary --enable-bundles python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py --enable-translation --enable-bundles python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py --enable-topic-classification --enable-bundles python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py --enable-summary --enable-translation --enable-topic-classification --enable-bundles python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py --enable-blog-drafts python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py --enable-summary --enable-blog-drafts python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py --enable-translation --enable-blog-drafts python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py --enable-topic-classification --enable-blog-drafts python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py --enable-bundles --enable-blog-drafts python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py --enable-summary --enable-translation --enable-topic-classification --enable-bundles --enable-blog-drafts python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py --enable-quality-review python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py --enable-summary --enable-translation --enable-topic-classification --enable-bundles --enable-blog-drafts --enable-quality-review python_pipeline/data/raw/devvit_keep_2026-04-05.json
```

## Execution order

1. Validate the raw JSON
2. Normalize the raw JSON
3. Build cards from the normalized JSON

Or run everything at once with `run_pipeline.py`.

For the V3 URL-list-based ingestion bridge, the flow is:

1. Put a human-curated txt file of Reddit thread URLs in `python_pipeline/data/url_lists/`
2. Run `ingest_reddit_urls.py`
3. Feed the generated raw JSON into `run_pipeline.py`

Example:

```bash
python python_pipeline/scripts/ingest_reddit_urls.py python_pipeline/data/url_lists/my_threads.txt
python python_pipeline/scripts/run_pipeline.py python_pipeline/data/raw/raw_from_urls_my_threads.json
```

This bridge is not a replacement for Devvit collection or a future Reddit Data API collector.
It is a URL-seeded bridge that produces raw JSON in the same keep-export shape expected by the
existing pipeline. If Data API access is approved later, the fetcher layer can be swapped without
changing the downstream raw schema, validator contract, or `run_pipeline.py` usage.
The raw `post_url` field preserves the original input URL, while canonical URLs are used internally
for fetch and dedupe logic.

`run_pipeline.py` prints a compact handoff summary:

- raw input count
- keep count
- validated count
- dropped count
- normalized count
- cards count
- summary input count
- summary success count
- summary empty count
- summary fallback count
- summary provider failure count
- translation input count
- translation success count
- translation empty field count
- translation card failure count
- topic classification input count
- topic success count
- topic fallback count
- topic empty text count
- topic card failure count
- bundle input count
- bundle count
- weekly bundle count
- topic bundle count
- mixed bundle count
- provider failure count
- blog draft bundle input count
- blog draft card input count
- blog draft count
- blog fallback draft count
- blog provider failure count
- quality review card input count
- quality review bundle input count
- quality review blog draft input count
- quality review count
- quality review pass count
- quality review warning count
- quality review fail count
- quality provider failure count

If validation issues are found, the pipeline still writes the normalized and cards outputs for the valid subset, then exits with status code `1`.

When `--enable-summary` is set, the pipeline keeps the existing `cards.json` output unchanged and also writes `cards_with_summary_*.json`.
When `--enable-translation` is set, the pipeline writes `cards_with_translation_*.json` using `cards.json` or `cards_with_summary.json` as the source, depending on whether summary is enabled.
When `--enable-topic-classification` is set, the pipeline writes `cards_with_topics_*.json` using the latest available card export as input.
When `--enable-bundles` is set, the pipeline writes `bundles_*.json` using the latest available card export as input.
When `--enable-blog-drafts` is set, the pipeline writes `blog_drafts_*.json` using bundles when available, otherwise it falls back to the latest available cards.
When `--blog-draft-provider openai` is set, the provider reads `OPENAI_API_KEY` and optionally `BLOG_DRAFT_OPENAI_MODEL`. If the key is missing or the request fails, the pipeline falls back to the existing rule-based draft path.
When `--enable-quality-review` is set, the pipeline writes `quality_reviews_*.json` using the latest available cards for card-level review, plus bundles and blog drafts when those outputs exist in the current run.

## Result files

- Normalized example:
  `python_pipeline/data/normalized/normalized_devvit_keep_2026-04-05.json`
- Cards example:
  `python_pipeline/data/cards/cards_devvit_keep_2026-04-05.json`
- URL-seeded raw example:
  `python_pipeline/data/raw/raw_from_urls_my_threads.json`
- Summary cards example:
  `python_pipeline/data/cards/cards_with_summary_devvit_keep_2026-04-05.json`
- Translation cards example:
  `python_pipeline/data/cards/cards_with_translation_devvit_keep_2026-04-05.json`
- Topic cards example:
  `python_pipeline/data/cards/cards_with_topics_devvit_keep_2026-04-05.json`
- Bundle example:
  `python_pipeline/data/cards/bundles_devvit_keep_2026-04-05.json`
- Blog draft example:
  `python_pipeline/data/cards/blog_drafts_devvit_keep_2026-04-05.json`
- Quality review example:
  `python_pipeline/data/cards/quality_reviews_devvit_keep_2026-04-05.json`
- Publish export example:
  `python_pipeline/data/publish/publish_blog_draft_devvit_keep_2026-04-05.md`

## Summary Stage

The V2-1 summary stage is a deterministic heuristic placeholder.

- It does not call any external LLM API.
- It prefers `title`, then excerpt-like text, then top comments.
- It safely handles missing fields, empty strings, and `null` values.
- It is designed so a future LLM provider adapter can replace the heuristic builder without changing the `cards.json` contract.
- The summary stage now also supports an optional real provider adapter, currently `openai`, behind `--summary-provider`.
- If `OPENAI_API_KEY` is missing or the provider fails, the pipeline falls back to the existing heuristic summary path.

## Translation Stage

The V2-2 translation stage is a scaffold, not a final API integration.

- It uses a provider adapter interface so a real translation backend can be swapped in later.
- The default provider is `passthrough`, which returns cleaned input text.
- The optional real provider is `openai`, behind `--translation-provider openai`.
- It reads `OPENAI_API_KEY` and optionally `TRANSLATION_OPENAI_MODEL` when the OpenAI provider is selected.
- It adds `title_ko`, `excerpt_ko`, and `summary_ko` only in `cards_with_translation_*.json`.
- It never overwrites the original card fields.
- Empty strings, `null`, and missing fields are handled safely.
- A future LLM or translation provider adapter can be added without changing the downstream `cards.json` contract.
- If the OpenAI provider fails or is not configured, the stage falls back to the existing passthrough translation path.

## Topic Classification Stage

The V2-3 topic classification stage is a scaffold, not a final LLM integration.

- It uses a rule-based provider adapter for now.
- It prefers `title`, then `summary`, then `excerpt`, then top comments.
- It adds `topic_labels`, `primary_topic`, `topic_confidence`, and `topic_match_reason` only in `cards_with_topics_*.json`.
- The current taxonomy is intentionally small: `pricing`, `model_comparison`, `coding`, `productivity`, `api_and_tools`, `prompt_engineering`, `workflow`, `general_discussion`.
- It is designed so a future LLM classifier provider can replace the rule-based provider without changing the downstream `cards.json` contract.

## Bundle Stage

The V2-4 bundle stage is a scaffold for grouping cards into separate bundle outputs.

- It uses a provider adapter interface so a future curator or LLM bundler can replace the rule-based provider later.
- The default provider is `rule_based`.
- It creates three bundle types for now: `weekly_bundle`, `topic_bundle`, and `mixed_bundle`.
- It stores bundle references through `card_ids` instead of duplicating full cards.
- It writes only `bundles_*.json` and never changes the existing cards exports.
- It is designed so a future LLM curator/provider can be added without changing the downstream `cards.json` contract.

## Blog Draft Stage

The V2-5 blog draft stage is a scaffold for pre-publish draft documents.

- It uses a provider adapter interface so a future LLM writer can replace the rule-based provider later.
- The default provider is `rule_based`.
- The optional real provider is `openai`, behind `--blog-draft-provider openai`.
- It writes `blog_drafts_*.json` only and never changes the existing cards or bundles exports.
- It prefers bundle input when bundles exist, and falls back to the latest cards when they do not.
- It creates draft-shaped output only; it is not the final post content.
- It is designed so a future LLM writer/provider can be added without changing the downstream `cards.json` or `bundles.json` contracts.

## Quality Review Stage

The V2-6 quality review stage is a scaffold for post-generation checks.

- It uses a provider adapter interface so a future LLM reviewer can replace the rule-based provider later.
- The default provider is `rule_based`.
- It can review cards, bundles, and blog drafts without changing the source outputs.
- It writes `quality_reviews_*.json` as a separate review artifact.
- It uses `pass`, `warning`, and `fail` as the only status values.
- It is designed so a future LLM reviewer/provider can be added without changing the downstream `cards.json`, `bundles.json`, or `blog_drafts.json` contracts.

## Publish Export Stage

The V2-9 publish export stage is a scaffold for human-readable Markdown handoff files.

- It uses a provider adapter interface so a future template or LLM export writer can replace the rule-based provider later.
- The default provider is `rule_based`.
- It writes Markdown only and never changes the existing JSON exports.
- It prefers `blog_drafts` when available, then `bundles`, then the latest card export.
- It keeps the output simple enough to paste into a draft document without extra cleanup.
- It writes into `python_pipeline/data/publish/`.
- The current output names are `publish_blog_draft_*.md`, `publish_bundles_*.md`, and `publish_cards_*.md`.

## What this version does not do

- No LLM summarization
- No translation
- No blog generation
- No multi-source integration
- No database or web server
- No LLM curator/provider
- No mandatory LLM writer/provider
- No LLM reviewer/provider
- No mandatory publish template/provider

## Notes

- Pipeline 0.1 uses only the Python standard library.
- `requirements.txt` exists only to make that explicit.
- The URL-seeded bridge also uses only the Python standard library and prefers Reddit public JSON responses for small, manual thread lists.
