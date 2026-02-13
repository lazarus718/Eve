"""Tests for the starter app CLI helpers."""

import json

from testing_app.eve_market import ItemOpportunity, calculate_opportunity
from testing_app.main import (
    build_greeting,
    format_eve_market_output,
    run_eve_market,
    write_output,
)


def test_greets_name() -> None:
    assert build_greeting("Alice") == "Hello, Alice!"


def test_supports_spanish_greetings() -> None:
    assert build_greeting("Alicia", "es") == "Hola, Alicia!"


def test_calculate_opportunity_returns_none_without_both_sides() -> None:
    assert (
        calculate_opportunity(
            1, "Item", [{"is_buy_order": True, "price": 10.0}], daily_volume=1000.0
        )
        is None
    )


def test_calculate_opportunity_computes_spread_and_roi() -> None:
    orders = [
        {"is_buy_order": True, "price": 100.0},
        {"is_buy_order": True, "price": 105.0},
        {"is_buy_order": False, "price": 130.0},
        {"is_buy_order": False, "price": 135.0},
    ]
    result = calculate_opportunity(34, "Tritanium", orders, daily_volume=1500.0)
    assert result is not None
    assert result.best_buy == 105.0
    assert result.best_sell == 130.0
    assert result.spread == 25.0
    assert result.daily_volume == 1500.0


def test_run_eve_market_returns_opportunities(monkeypatch) -> None:
    opportunities = [
        ItemOpportunity(1, "Item A", 10.0, 12.0, 2.0, 20.0, 1200.0),
        ItemOpportunity(2, "Item B", 20.0, 25.0, 5.0, 25.0, 800.0),
    ]

    def fake_top_opportunities(
        region_id: int,
        limit: int,
        sample_size: int,
        max_buy_price: float,
        min_daily_volume: float,
    ):
        assert region_id == 10000002
        assert limit == 2
        assert sample_size == 5
        assert max_buy_price == 250000000.0
        assert min_daily_volume == 100.0
        return opportunities

    monkeypatch.setattr("testing_app.main.top_opportunities", fake_top_opportunities)

    returned = run_eve_market(
        region_id=10000002,
        top=2,
        sample_size=5,
        max_buy_price=250000000.0,
        min_daily_volume=100.0,
    )
    assert returned == opportunities


def test_format_eve_market_output_text() -> None:
    opportunities = [
        ItemOpportunity(1, "Item A", 10.0, 12.0, 2.0, 20.0, 1200.0),
        ItemOpportunity(2, "Item B", 20.0, 25.0, 5.0, 25.0, 800.0),
    ]
    lines = format_eve_market_output(
        opportunities,
        region_id=10000002,
        sample_size=5,
        as_json=False,
        min_daily_volume=100.0,
    )
    assert lines[0].startswith("Top 2 opportunities")
    assert "daily_vol=" in lines[1]


def test_format_eve_market_output_json() -> None:
    opportunities = [ItemOpportunity(34, "Tritanium", 4.0, 4.5, 0.5, 12.5, 20000.0)]
    lines = format_eve_market_output(
        opportunities,
        region_id=10000002,
        sample_size=5,
        as_json=True,
        min_daily_volume=100.0,
    )
    parsed = json.loads(lines[0])
    assert parsed["region_id"] == 10000002
    assert parsed["count"] == 1
    assert parsed["min_daily_volume"] == 100.0
    assert parsed["opportunities"][0]["name"] == "Tritanium"
    assert parsed["opportunities"][0]["rank"] == 1
    assert parsed["opportunities"][0]["daily_volume"] == 20000.0


def test_write_output_writes_file_and_stdout(capsys, tmp_path) -> None:
    output_file = tmp_path / "reports" / "eve_report.json"
    write_output(["line one", "line two"], output_file)
    captured = capsys.readouterr()
    assert captured.out == "line one\nline two\n"
    assert output_file.read_text(encoding="utf-8") == "line one\nline two\n"


def test_fetch_market_prices_applies_budget_prefilter(monkeypatch) -> None:
    from testing_app import eve_market

    def fake_request_json(url: str, data: bytes | None = None):
        del url, data
        return (
            [
                {"type_id": 1, "average_price": 1000000.0},
                {"type_id": 2, "average_price": 200000.0},
                {"type_id": 3, "average_price": 150000.0},
            ],
            {},
        )

    monkeypatch.setattr(eve_market, "_request_json", fake_request_json)
    result = eve_market.fetch_market_prices(limit=10, max_average_price=250000.0)
    assert result == [2, 3]


def test_top_opportunities_prefilters_candidates_by_budget_and_volume(monkeypatch) -> None:
    from testing_app import eve_market

    called_with: dict[str, float | int] = {}

    def fake_fetch_market_prices(limit: int, max_average_price: float | None = None):
        called_with["limit"] = limit
        called_with["max_average_price"] = (
            max_average_price if max_average_price is not None else -1
        )
        return [11, 12]

    def fake_fetch_item_daily_volume(region_id: int, type_id: int):
        del region_id
        return 1000.0 if type_id == 11 else 50.0

    monkeypatch.setattr(eve_market, "fetch_market_prices", fake_fetch_market_prices)
    monkeypatch.setattr(eve_market, "fetch_item_names", lambda type_ids: {11: "A", 12: "B"})
    monkeypatch.setattr(eve_market, "fetch_item_daily_volume", fake_fetch_item_daily_volume)
    monkeypatch.setattr(
        eve_market,
        "fetch_orders_for_item",
        lambda region_id, type_id: [
            {"is_buy_order": True, "price": 10.0},
            {"is_buy_order": False, "price": 12.0},
        ],
    )

    result = eve_market.top_opportunities(
        sample_size=75,
        max_buy_price=250000000.0,
        min_daily_volume=100.0,
    )
    assert len(result) == 1
    assert result[0].type_id == 11
    assert called_with["limit"] == 75
    assert called_with["max_average_price"] == 250000000.0
