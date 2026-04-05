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
- `run_pipeline.py`: Runs validation, normalization, and card generation in one command

## Example commands

```bash
python python_pipeline/scripts/validate_raw.py python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/normalize_devvit_raw.py python_pipeline/data/raw/devvit_keep_2026-04-05.json
python python_pipeline/scripts/make_cards.py python_pipeline/data/normalized/normalized_devvit_keep_2026-04-05.json
python python_pipeline/scripts/run_pipeline.py python_pipeline/data/raw/devvit_keep_2026-04-05.json
```

## Execution order

1. Validate the raw JSON
2. Normalize the raw JSON
3. Build cards from the normalized JSON

Or run everything at once with `run_pipeline.py`.

## Result files

- Normalized example:
  `python_pipeline/data/normalized/normalized_devvit_keep_2026-04-05.json`
- Cards example:
  `python_pipeline/data/cards/cards_devvit_keep_2026-04-05.json`

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
