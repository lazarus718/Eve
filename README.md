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
(best sell minus best buy) to highlight potentially profitable flips. It now also filters
by minimum daily regional trade volume and estimated post-fee net profit to avoid thin markets and low-margin traps.

By default it:

- scans **The Forge** region (`region_id=10000002`)
- samples candidate items from `/markets/prices/`
- fetches order books for each sampled item
- calculates per-item spread and ROI% plus latest daily regional volume and post-fee net profit
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
PYTHONPATH=src python -m testing_app.main eve-market --region-id 10000002 --top 25 --sample-size 75 --max-buy-price 250000000 --min-daily-volume 100 --sales-tax-pct 4.5 --broker-fee-pct 3.0 --min-net-profit 0
```

JSON output for scripting/spreadsheets:

```bash
PYTHONPATH=src python -m testing_app.main eve-market --region-id 10000002 --top 25 --sample-size 75 --max-buy-price 250000000 --min-daily-volume 100 --sales-tax-pct 4.5 --broker-fee-pct 3.0 --min-net-profit 0 --json
```

Write report directly to a file (`--output`):

```bash
PYTHONPATH=src python -m testing_app.main eve-market --region-id 10000002 --top 25 --sample-size 75 --max-buy-price 250000000 --min-daily-volume 100 --sales-tax-pct 4.5 --broker-fee-pct 3.0 --min-net-profit 0 --json --output reports/eve_report.json
```

## Notes

- This tool uses public market data only (no auth needed).
- Default budget filter: only items with `best_buy <= 250,000,000 ISK` are included; adjust with `--max-buy-price`.
- Pipeline logic (in order):
  1. Pull `/markets/prices/` candidates and keep only entries with `average_price <= max_buy_price`.
  2. Sort candidates by average price (highest first) and sample up to `--sample-size` (default 75).
  3. Fetch latest daily regional volume from `/markets/{region_id}/history/` and apply `--min-daily-volume`.
  4. Fetch regional order books for remaining items and compute best buy/best sell spread.
  5. Apply estimated costs (`--sales-tax-pct` + `--broker-fee-pct`) to compute post-fee net profit per unit.
  6. Keep only items with `spread > 0`, `best_buy <= max_buy_price`, and `net_profit >= min_net_profit`, then rank by net profit.
- Cost assumptions are configurable via `--sales-tax-pct` and `--broker-fee-pct`; defaults are 4.5% and 3.0%.
- Default minimum daily volume filter is `100` units/day; tune with `--min-daily-volume`.
- Default minimum net-profit filter is `0` ISK/unit; tune with `--min-net-profit`.
- Results still do not model hauling risk, order modification cadence, or future price movement risk.

## Major market hub region IDs

Use these with `--region-id` to scan common trade hubs:

- **Jita** (The Forge): `10000002`
- **Amarr** (Domain): `10000043`
- **Dodixie** (Sinq Laison): `10000032`
- **Rens** (Heimatar): `10000030`
- **Hek** (Metropolis): `10000042`

Example:

```bash
PYTHONPATH=src python -m testing_app.main eve-market --region-id 10000043 --top 15 --sample-size 500 --max-buy-price 125000000 --min-daily-volume 10 --sales-tax-pct 4.5 --broker-fee-pct 3.0 --min-net-profit 0
```

