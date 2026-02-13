"""EVE Online market analysis helpers using ESI public APIs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import parse, request

ESI_BASE_URL = "https://esi.evetech.net/latest"
DEFAULT_REGION_ID = 10000002  # The Forge (Jita)
DEFAULT_MAX_BUY_PRICE = 250_000_000.0


@dataclass(frozen=True)
class ItemOpportunity:
    """Computed market opportunity for one item."""

    type_id: int
    name: str
    best_buy: float
    best_sell: float
    spread: float
    roi_pct: float


def _request_json(url: str, data: bytes | None = None) -> tuple[Any, dict[str, str]]:
    req = request.Request(url, data=data)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with request.urlopen(req, timeout=20) as response:  # nosec B310 - trusted ESI endpoint usage
        payload = json.loads(response.read().decode("utf-8"))
        headers = {k.lower(): v for k, v in response.headers.items()}
    return payload, headers


def fetch_market_prices(limit: int = 75, max_average_price: float | None = None) -> list[int]:
    """Return type IDs for candidate items using market average prices."""
    url = f"{ESI_BASE_URL}/markets/prices/?datasource=tranquility"
    payload, _ = _request_json(url)
    prices = [
        entry
        for entry in payload
        if isinstance(entry, dict)
        and isinstance(entry.get("type_id"), int)
        and isinstance(entry.get("average_price"), (int, float))
    ]
    if max_average_price is not None:
        prices = [entry for entry in prices if float(entry["average_price"]) <= max_average_price]
    prices.sort(key=lambda entry: float(entry["average_price"]), reverse=True)
    return [int(entry["type_id"]) for entry in prices[:limit]]


def fetch_orders_for_item(region_id: int, type_id: int) -> list[dict[str, object]]:
    """Fetch all buy/sell orders for an item in one region."""
    params = parse.urlencode(
        {
            "datasource": "tranquility",
            "order_type": "all",
            "type_id": type_id,
            "page": 1,
        }
    )
    url = f"{ESI_BASE_URL}/markets/{region_id}/orders/?{params}"
    first_page, headers = _request_json(url)
    orders: list[dict[str, object]] = first_page if isinstance(first_page, list) else []

    pages = int(headers.get("x-pages", "1"))
    for page in range(2, pages + 1):
        paged_params = parse.urlencode(
            {
                "datasource": "tranquility",
                "order_type": "all",
                "type_id": type_id,
                "page": page,
            }
        )
        page_url = f"{ESI_BASE_URL}/markets/{region_id}/orders/?{paged_params}"
        page_payload, _ = _request_json(page_url)
        if isinstance(page_payload, list):
            orders.extend(page_payload)
    return orders


def fetch_item_names(type_ids: list[int]) -> dict[int, str]:
    """Resolve type IDs to in-game names."""
    if not type_ids:
        return {}
    url = f"{ESI_BASE_URL}/universe/names/?datasource=tranquility"
    payload, _ = _request_json(url, data=json.dumps(type_ids).encode("utf-8"))
    names: dict[int, str] = {}
    if isinstance(payload, list):
        for entry in payload:
            if (
                isinstance(entry, dict)
                and isinstance(entry.get("id"), int)
                and isinstance(entry.get("name"), str)
            ):
                names[int(entry["id"])] = str(entry["name"])
    return names


def calculate_opportunity(
    type_id: int, name: str, orders: list[dict[str, object]]
) -> ItemOpportunity | None:
    """Calculate spread and ROI for one item from raw orders."""
    buy_prices: list[float] = []
    sell_prices: list[float] = []

    for order in orders:
        if not isinstance(order, dict):
            continue
        price = order.get("price")
        if not isinstance(price, (int, float)):
            continue

        if order.get("is_buy_order") is True:
            buy_prices.append(float(price))
        elif order.get("is_buy_order") is False:
            sell_prices.append(float(price))

    if not buy_prices or not sell_prices:
        return None

    best_buy = max(buy_prices)
    best_sell = min(sell_prices)
    spread = best_sell - best_buy
    if spread <= 0 or best_buy <= 0:
        return None

    roi_pct = (spread / best_buy) * 100
    return ItemOpportunity(type_id, name, best_buy, best_sell, spread, roi_pct)


def top_opportunities(
    region_id: int = DEFAULT_REGION_ID,
    limit: int = 25,
    sample_size: int = 75,
    max_buy_price: float = DEFAULT_MAX_BUY_PRICE,
) -> list[ItemOpportunity]:
    """Compute top profitable market opportunities from sampled items."""
    candidate_ids = fetch_market_prices(limit=sample_size, max_average_price=max_buy_price)
    names = fetch_item_names(candidate_ids)

    opportunities: list[ItemOpportunity] = []
    for type_id in candidate_ids:
        orders = fetch_orders_for_item(region_id, type_id)
        name = names.get(type_id, f"Type {type_id}")
        opportunity = calculate_opportunity(type_id, name, orders)
        if opportunity is not None and opportunity.best_buy <= max_buy_price:
            opportunities.append(opportunity)

    opportunities.sort(key=lambda item: item.spread, reverse=True)
    return opportunities[:limit]
