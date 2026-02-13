# Testing- Python Starter Scaffold

This project now includes a practical CLI tool for **EVE Online market scanning**.

## What "stack" means

A **stack** is the collection of technologies used to build and run software:

- programming language/runtime
- libraries/frameworks
- testing tools
- linting/type-checking tools
- CI automation

For this repo, the stack is Python + pytest + Ruff + mypy + GitHub Actions.

## Main feature: EVE market opportunities

The `eve-market` command queries EVE's public ESI API and ranks items by market spread
(best sell minus best buy) to highlight potentially profitable flips.

By default it:

- scans **The Forge** region (`region_id=10000002`)
- samples candidate items from `/markets/prices/`
- fetches order books for each sampled item
- calculates per-item spread and ROI%
- prints the top opportunities

## Project layout

```text
.
├── .github/workflows/ci.yml
├── LICENSE
├── README.md
├── pyproject.toml
├── src/
│   └── testing_app/
│       ├── __init__.py
│       ├── eve_market.py
│       └── main.py
└── tests/
    └── test_main.py
```

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .[dev]
```

## Local checks

```bash
ruff check .
ruff format --check .
mypy src
PYTHONPATH=src pytest
```

## Usage

Greeting mode (legacy helper):

```bash
PYTHONPATH=src python -m testing_app.main greet --name "Newcomer" --lang fr
```

EVE market mode:

```bash
PYTHONPATH=src python -m testing_app.main eve-market --region-id 10000002 --top 10 --sample-size 75 --max-buy-price 250000000
```

JSON output for scripting/spreadsheets:

```bash
PYTHONPATH=src python -m testing_app.main eve-market --region-id 10000002 --top 10 --sample-size 75 --max-buy-price 250000000 --json
```

Write report directly to a file (`--output`):

```bash
PYTHONPATH=src python -m testing_app.main eve-market --region-id 10000002 --top 10 --sample-size 75 --max-buy-price 250000000 --json --output reports/eve_report.json
```

## Notes

- This tool uses public market data only (no auth needed).
- Default budget filter: only items with `best_buy <= 250,000,000 ISK` are included; adjust with `--max-buy-price`.
- Pipeline logic (in order):
  1. Pull `/markets/prices/` candidates and keep only entries with `average_price <= max_buy_price`.
  2. Sort candidates by average price (highest first) and sample up to `--sample-size` (default 75).
  3. Fetch regional order books for sampled items and compute best buy/best sell spread.
  4. Keep only profitable items with `spread > 0` and `best_buy <= max_buy_price`, then rank by spread.
- Reported opportunities are raw spread-based estimates and do **not** subtract broker fees,
  sales tax, hauling risk, volume limits, or price movement risk.
