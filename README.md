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
PYTHONPATH=src python -m testing_app.main eve-market --region-id 10000002 --top 10 --sample-size 30
```

JSON output for scripting/spreadsheets:

```bash
PYTHONPATH=src python -m testing_app.main eve-market --region-id 10000002 --top 10 --sample-size 30 --json
```

## Notes

- This tool uses public market data only (no auth needed).
- Reported opportunities are raw spread-based estimates and do **not** subtract broker fees,
  sales tax, hauling risk, volume limits, or price movement risk.
