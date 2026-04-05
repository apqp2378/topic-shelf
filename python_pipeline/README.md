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

## Example commands

```bash
python python_pipeline/scripts/validate_raw.py python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/normalize_devvit_raw.py python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/make_cards.py python_pipeline/data/normalized/normalized_devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py --enable-summary python_pipeline/data/raw/devvit_keep_2026-04-05.json
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

If validation issues are found, the pipeline still writes the normalized and cards outputs for the valid subset, then exits with status code `1`.

When `--enable-summary` is set, the pipeline keeps the existing `cards.json` output unchanged and also writes `cards_with_summary_*.json`.

## Result files

- Normalized example:
  `python_pipeline/data/normalized/normalized_devvit_keep_2026-04-05.json`
- Cards example:
  `python_pipeline/data/cards/cards_devvit_keep_2026-04-05.json`
- Summary cards example:
  `python_pipeline/data/cards/cards_with_summary_devvit_keep_2026-04-05.json`

## Summary Stage

The V2-1 summary stage is a deterministic heuristic placeholder.

- It does not call any external LLM API.
- It prefers `title`, then excerpt-like text, then top comments.
- It safely handles missing fields, empty strings, and `null` values.
- It is designed so a future LLM provider adapter can replace the heuristic builder without changing the `cards.json` contract.

## What this version does not do

- No LLM summarization
- No translation
- No blog generation
- No weekly bundle generation
- No multi-source integration
- No database or web server

## Notes

- Pipeline 0.1 uses only the Python standard library.
- `requirements.txt` exists only to make that explicit.
