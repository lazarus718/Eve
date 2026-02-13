"""CLI entrypoint for greeting and EVE market analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.error import URLError

from .eve_market import (
    DEFAULT_MAX_BUY_PRICE,
    DEFAULT_MIN_DAILY_VOLUME,
    DEFAULT_REGION_ID,
    ItemOpportunity,
    top_opportunities,
)

SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "Hello",
    "es": "Hola",
    "fr": "Bonjour",
}


def build_greeting(name: str, language: str = "en") -> str:
    """Return a friendly greeting for a given name and language."""
    normalized_name = name.strip() or "world"
    normalized_language = language.strip().lower() or "en"
    salutation = SUPPORTED_LANGUAGES.get(normalized_language, SUPPORTED_LANGUAGES["en"])
    return f"{salutation}, {normalized_name}!"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Utilities for greetings and EVE market analysis.")
    subparsers = parser.add_subparsers(dest="command", required=False)

    greet_parser = subparsers.add_parser("greet", help="Print a friendly greeting")
    greet_parser.add_argument("--name", default="world", help="Name to greet")
    greet_parser.add_argument(
        "--lang",
        default="en",
        choices=sorted(SUPPORTED_LANGUAGES),
        help="Language code for the greeting",
    )

    eve_parser = subparsers.add_parser(
        "eve-market", help="Find profitable EVE market opportunities"
    )
    eve_parser.add_argument(
        "--region-id", type=int, default=DEFAULT_REGION_ID, help="EVE region ID"
    )
    eve_parser.add_argument("--top", type=int, default=25, help="How many results to show")
    eve_parser.add_argument(
        "--sample-size",
        type=int,
        default=75,
        help="How many candidate items to scan before ranking (default: 75)",
    )
    eve_parser.add_argument(
        "--json",
        action="store_true",
        help="Print EVE market results as JSON",
    )
    eve_parser.add_argument(
        "--output",
        type=Path,
        help="Optional output file path for report content",
    )
    eve_parser.add_argument(
        "--max-buy-price",
        type=float,
        default=DEFAULT_MAX_BUY_PRICE,
        help="Maximum best-buy price to include in results (default: 250000000 ISK)",
    )
    eve_parser.add_argument(
        "--min-daily-volume",
        type=float,
        default=DEFAULT_MIN_DAILY_VOLUME,
        help="Minimum latest daily trade volume required (default: 100 units/day)",
    )

    return parser.parse_args()


def _format_opportunity_row(
    rank: int,
    name: str,
    buy: float,
    sell: float,
    spread: float,
    roi: float,
    daily_volume: float,
) -> str:
    return (
        f"{rank:>2}. {name:<28} buy={buy:>12,.2f} sell={sell:>12,.2f} "
        f"spread={spread:>11,.2f} roi={roi:>6.2f}% daily_vol={daily_volume:>8,.0f}"
    )


def _opportunity_to_dict(rank: int, item: ItemOpportunity) -> dict[str, float | int | str]:
    return {
        "rank": rank,
        "type_id": item.type_id,
        "name": item.name,
        "best_buy": item.best_buy,
        "best_sell": item.best_sell,
        "spread": item.spread,
        "roi_pct": item.roi_pct,
        "daily_volume": item.daily_volume,
    }


def run_eve_market(
    region_id: int,
    top: int,
    sample_size: int,
    max_buy_price: float,
    min_daily_volume: float,
) -> list[ItemOpportunity]:
    """Execute market analysis and return computed opportunities."""
    return top_opportunities(
        region_id=region_id,
        limit=top,
        sample_size=sample_size,
        max_buy_price=max_buy_price,
        min_daily_volume=min_daily_volume,
    )


def format_eve_market_output(
    opportunities: list[ItemOpportunity],
    region_id: int,
    sample_size: int,
    as_json: bool,
    min_daily_volume: float,
) -> list[str]:
    """Format opportunities as plain text or JSON lines."""
    if as_json:
        payload = {
            "region_id": region_id,
            "sample_size": sample_size,
            "min_daily_volume": min_daily_volume,
            "count": len(opportunities),
            "opportunities": [
                _opportunity_to_dict(index, item)
                for index, item in enumerate(opportunities, start=1)
            ],
        }
        return [json.dumps(payload, indent=2)]

    if not opportunities:
        return [
            "No profitable opportunities found in current sample.",
            "Pipeline checks: average price cap -> daily volume filter -> "
            "spread and budget checks.",
            f"Current minimum daily volume filter: {min_daily_volume:,.0f} units/day.",
        ]

    lines = [
        "Top "
        f"{len(opportunities)} opportunities in region {region_id} "
        f"(sampled {sample_size} items, min daily volume {min_daily_volume:,.0f}):",
    ]
    for index, item in enumerate(opportunities, start=1):
        lines.append(
            _format_opportunity_row(
                index,
                item.name,
                item.best_buy,
                item.best_sell,
                item.spread,
                item.roi_pct,
                item.daily_volume,
            )
        )
    return lines


def write_output(lines: list[str], output_path: Path | None) -> None:
    """Print lines and optionally write them to a file."""
    content = "\n".join(lines)
    print(content)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content + "\n", encoding="utf-8")


def main() -> None:
    """CLI entrypoint."""
    args = parse_args()

    if args.command in (None, "greet"):
        name = getattr(args, "name", "world")
        language = getattr(args, "lang", "en")
        print(build_greeting(name, language))
        return

    if args.command == "eve-market":
        try:
            opportunities = run_eve_market(
                args.region_id,
                args.top,
                args.sample_size,
                args.max_buy_price,
                args.min_daily_volume,
            )
            lines = format_eve_market_output(
                opportunities,
                region_id=args.region_id,
                sample_size=args.sample_size,
                as_json=args.json,
                min_daily_volume=args.min_daily_volume,
            )
            write_output(lines, args.output)
        except URLError as error:
            print(f"Failed to query EVE ESI API: {error}")


if __name__ == "__main__":
    main()
