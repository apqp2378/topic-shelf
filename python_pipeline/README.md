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
- `run_pipeline.py`: Runs validation, normalization, and card generation in one command and prints stage counts
- `run_pipeline.py --enable-summary`: Adds the optional heuristic summary stage and writes a second card export
- `run_pipeline.py --enable-translation`: Adds the optional translation scaffold and writes a third card export
- `run_pipeline.py --enable-topic-classification`: Adds the optional topic classification scaffold and writes a fourth card export
- `run_pipeline.py --enable-bundles`: Adds the optional bundle scaffold and writes a separate bundle export

## Example commands

```bash
python python_pipeline/scripts/validate_raw.py python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/normalize_devvit_raw.py python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/make_cards.py python_pipeline/data/normalized/normalized_devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py --enable-summary python_pipeline/data/raw/devvit_keep_2026-04-05.json
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
```

## Execution order

1. Validate the raw JSON
2. Normalize the raw JSON
3. Build cards from the normalized JSON

Or run everything at once with `run_pipeline.py`.

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

If validation issues are found, the pipeline still writes the normalized and cards outputs for the valid subset, then exits with status code `1`.

When `--enable-summary` is set, the pipeline keeps the existing `cards.json` output unchanged and also writes `cards_with_summary_*.json`.
When `--enable-translation` is set, the pipeline writes `cards_with_translation_*.json` using `cards.json` or `cards_with_summary.json` as the source, depending on whether summary is enabled.
When `--enable-topic-classification` is set, the pipeline writes `cards_with_topics_*.json` using the latest available card export as input.
When `--enable-bundles` is set, the pipeline writes `bundles_*.json` using the latest available card export as input.

## Result files

- Normalized example:
  `python_pipeline/data/normalized/normalized_devvit_keep_2026-04-05.json`
- Cards example:
  `python_pipeline/data/cards/cards_devvit_keep_2026-04-05.json`
- Summary cards example:
  `python_pipeline/data/cards/cards_with_summary_devvit_keep_2026-04-05.json`
- Translation cards example:
  `python_pipeline/data/cards/cards_with_translation_devvit_keep_2026-04-05.json`
- Topic cards example:
  `python_pipeline/data/cards/cards_with_topics_devvit_keep_2026-04-05.json`
- Bundle example:
  `python_pipeline/data/cards/bundles_devvit_keep_2026-04-05.json`

## Summary Stage

The V2-1 summary stage is a deterministic heuristic placeholder.

- It does not call any external LLM API.
- It prefers `title`, then excerpt-like text, then top comments.
- It safely handles missing fields, empty strings, and `null` values.
- It is designed so a future LLM provider adapter can replace the heuristic builder without changing the `cards.json` contract.

## Translation Stage

The V2-2 translation stage is a scaffold, not a final API integration.

- It uses a provider adapter interface so a real translation backend can be swapped in later.
- The default provider is `passthrough`, which returns cleaned input text.
- It adds `title_ko`, `excerpt_ko`, and `summary_ko` only in `cards_with_translation_*.json`.
- It never overwrites the original card fields.
- Empty strings, `null`, and missing fields are handled safely.
- A future LLM or translation provider adapter can be added without changing the downstream `cards.json` contract.

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

## What this version does not do

- No LLM summarization
- No translation
- No blog generation
- No multi-source integration
- No database or web server
- No LLM curator/provider

## Notes

- Pipeline 0.1 uses only the Python standard library.
- `requirements.txt` exists only to make that explicit.
