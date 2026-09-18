# Data Processing Pipeline

A configuration-driven Python pipeline that reads raw data from **CSV, JSON,
or a REST API**, cleans and transforms it, and writes structured output —
with logging, a per-run JSON report, and no hard-coded assumptions about
your data.

## Features

- **Multiple sources**: CSV, JSON (local file or nested under `records`/`data`/`results`/`items`), or a REST API.
- **Missing-value handling**, per column: `drop_row`, `fill` (with a default), or `leave`. Common blank markers (`""`, `"NA"`, `"N/A"`, `"null"`, `"-"`, etc.) are normalized to real nulls first.
- **Type conversion** against a declared schema (`str`, `int`, `float`, `bool`, `date`, `datetime`), with safe coercion — invalid values become `null` and are handled by your missing-value rules rather than crashing the run.
- **Cleaning**: whitespace trimming, case normalization, duplicate removal (with a configurable subset of columns), negative-value filtering, allowed-value validation.
- **Transformation**: derived columns, column renaming, column dropping.
- **Configuration management** via a single `config.yaml`, with environment-variable overrides (`PIPELINE__SECTION__KEY=value`) for different environments.
- **Logging** to console and/or file, with a configurable level.
- **Run reports**: every run writes a `*.report.json` summary (rows in/out, rows dropped and why, cells filled, cells coerced to null, duration).
- **CLI**: override the input file, output file, or source type without touching the config file.

## Project structure

```
data-pipeline/
├── main.py                    # CLI entry point
├── config.yaml                # Default pipeline configuration
├── requirements.txt
├── src/
│   ├── config.py               # YAML config loading + env var overrides + validation
│   ├── logger.py                # Logging setup (console + file)
│   ├── readers.py               # CSVReader, JSONReader, APIReader
│   ├── cleaners.py               # Missing values, type conversion, dedupe, validation
│   ├── transformers.py            # Derived columns, renaming, column pruning
│   ├── writers.py                  # CSV/JSON output + JSON run report
│   ├── pipeline.py                  # Orchestrates read -> clean -> transform -> write
│   └── exceptions.py                # PipelineError, ConfigError, DataSourceError, DataValidationError
├── data/
│   ├── input/
│   │   ├── sales_sample.csv        # Messy sample data: blanks, bad types, dupes, negatives, bad dates
│   │   └── users_sample.json        # Sample JSON source (nested under "records")
│   └── output/
│       ├── cleaned_sales.csv         # Sample output from running the default config
│       └── cleaned_sales.report.json  # Sample run report
├── tests/
│   ├── test_cleaners.py             # Unit tests for the cleaning logic
│   └── test_pipeline.py              # Integration tests for the full pipeline
└── logs/                             # Log file output (created at runtime)
```

## Setup

Requires Python 3.10+.

```bash
git clone <your-repo-url>
cd data-pipeline
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

### Run with the default config

```bash
python main.py --config config.yaml
```

This reads `data/input/sales_sample.csv` (as configured in `config.yaml`),
cleans and transforms it, and writes:

- `data/output/cleaned_sales.csv` — the cleaned data
- `data/output/cleaned_sales.report.json` — a summary of what happened

### Override the input/output/source type from the CLI

```bash
# Point at a different CSV file, same config otherwise
python main.py --config config.yaml --input data/input/other.csv --output data/output/other.csv

# Switch to the JSON source
python main.py --config config.yaml --source-type json --input data/input/users_sample.json --output data/output/cleaned_users.json
```

The output format follows the `--output` file's extension (`.csv` or `.json`)
when you override it from the CLI; otherwise it follows `output.format` in
`config.yaml`.

### Run against an API

Set `source.type: api` in `config.yaml` and fill in `source.api.url` (plus
`method`, `params`, `headers`, `timeout` as needed), or point the CLI at it:

```bash
python main.py --config config.yaml --source-type api
```

The API response is expected to be JSON — either a top-level list of
records, or an object with the records under `records`, `data`, `results`,
or `items`.

### Environment variable overrides

Any config value can be overridden without editing the file, using
`PIPELINE__<SECTION>__<KEY>`:

```bash
PIPELINE__SOURCE__PATH=/tmp/prod_data.csv PIPELINE__LOGGING__LEVEL=DEBUG python main.py --config config.yaml
```

## Configuring the pipeline

Everything is driven by `config.yaml`. The main sections:

| Section | Purpose |
|---|---|
| `source` | Where data comes from: `csv`, `json`, or `api`, and the path/URL. |
| `output` | Where cleaned data goes, in what format (`csv`/`json`), and whether to write a run report. |
| `schema` | Declares every expected column and the type to coerce it to (`str`, `int`, `float`, `bool`, `date`, `datetime`). Columns not in the schema are dropped; columns in the schema but missing from the source are added as empty. |
| `missing_values` | A `default_strategy` (`drop_row`, `fill`, `leave`) plus per-column overrides, each with its own strategy and (for `fill`) a `fill_value`. |
| `cleaning` | Whitespace trimming, case normalization, duplicate removal (and which columns define a duplicate), which columns can't be negative, and which `status` values are allowed. |
| `transform` | Derived columns (e.g. `total_price = quantity * unit_price`), column renaming, column dropping. |
| `logging` | Log level, and whether to log to console and/or a file. |

See the comments in [`config.yaml`](config.yaml) for a fully worked example.

## Sample data & what happens to it

`data/input/sales_sample.csv` is deliberately messy — it exercises every
part of the pipeline:

| Issue | Row(s) | Result |
|---|---|---|
| Missing `order_id` | row with blank id | Row dropped (`order_id` strategy is `drop_row`) |
| Missing `customer_name` | order `1004` | Row dropped |
| Missing `quantity` | order `1002` | Filled with `0` |
| Missing `unit_price` | order `1007` | Filled with `0.0` |
| Missing `region` | order `1011` | Filled with `"UNKNOWN"` |
| Malformed date (`"not a date"`) | order `1005` | `order_date` becomes `null`, row kept |
| Non-numeric quantity (`"N/A"`) | order `1010` | Coerced to `null`, then filled with `0` by the missing-value rule |
| Negative quantity | order `1006` | Row dropped (`drop_negative_values`) |
| Duplicate `order_id` | order `1008` (appears twice) | Second occurrence dropped |
| Invalid `status` (`"weird_status"`) | order `1009` | Row dropped (`valid_status_values`) |
| Extra/inconsistent whitespace and casing | several rows | Trimmed, and `region`/`status` uppercased, `email` lowercased |

Running `python main.py --config config.yaml` turns the 14 messy input rows
into 9 clean output rows, with `data/output/cleaned_sales.report.json`
recording exactly what was dropped, filled, or coerced and why.

## Testing

Unit tests cover the cleaning logic (missing-value strategies, type
coercion including invalid values, negative-value and duplicate handling,
whitespace trimming, empty input) and integration tests cover a full
pipeline run, report generation, config-error handling, and CLI overrides.

```bash
pip install pytest   # included in requirements.txt
pytest -v
```

## Extending the pipeline

- **New source type**: add a class to `src/readers.py` implementing
  `.read() -> pandas.DataFrame`, and wire it into `get_reader()`.
- **New cleaning rule**: add a method to `DataCleaner` in `src/cleaners.py`
  and call it from `DataCleaner.clean()`.
- **New transformation**: add logic to `DataTransformer.transform()` in
  `src/transformers.py`, driven by a new key under `transform:` in the
  config.
- **New output format**: extend `write_output()` in `src/writers.py`.

## Design notes

- Readers normalize everything to strings on the way in; all real type
  conversion happens in one place (`DataCleaner._convert_types`), driven by
  the `schema` section, so there's a single source of truth for what type
  each column should be.
- Missing-value handling runs **after** type conversion, not before — a
  value that's syntactically present but invalid for its column's type
  (e.g. `"abc"` in an `int` column) is coerced to `null` and then goes
  through the exact same fill/drop rules as a genuinely blank cell, rather
  than silently slipping through as an unfilled `null`.
- Nothing raises on a single bad row. Bad or missing cells are coerced to
  `null`/dropped according to config and counted in the run's stats; the
  pipeline only raises for structural problems (bad config, unreadable
  source, unwritable output).
