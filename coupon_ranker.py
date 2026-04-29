"""Pure ranking logic. No I/O, no globals."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

MAX_RESULTS = 5


@dataclass(frozen=True)
class RankedDeal:
    restaurant_name: str
    restaurant_id: str
    coupon_code: str
    savings_inr: float
    min_order: float
    description: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_coupons(response: dict[str, Any]) -> Iterable[dict[str, Any]]:
    """Yield individual coupon dicts from one fetch_food_coupons response."""
    if not isinstance(response, dict):
        return []

    direct = response.get("coupons")
    if isinstance(direct, list):
        return direct

    for key in ("data", "result"):
        nested = response.get(key)
        if isinstance(nested, dict):
            inner = nested.get("coupons")
            if isinstance(inner, list):
                return inner

    return []


def _restaurant_meta(response: dict[str, Any]) -> tuple[str, str]:
    name = (
        response.get("restaurant_name")
        or response.get("restaurantName")
        or (response.get("restaurant") or {}).get("name")
        or "Unknown"
    )
    rid = (
        response.get("restaurant_id")
        or response.get("restaurantId")
        or (response.get("restaurant") or {}).get("id")
        or ""
    )
    return str(name), str(rid)


def rank_deals(coupon_responses: list[dict[str, Any]]) -> list[RankedDeal]:
    """Flatten coupon responses, sort by savings DESC then min_order ASC, take top 5."""
    deals: list[RankedDeal] = []

    for response in coupon_responses or []:
        if not isinstance(response, dict):
            continue
        # Skip error envelopes returned by swiggy_mcp
        if response.get("error"):
            continue

        rname, rid = _restaurant_meta(response)
        for coupon in _extract_coupons(response):
            if not isinstance(coupon, dict):
                continue
            code = coupon.get("code") or coupon.get("coupon_code") or ""
            if not code:
                continue
            savings = _coerce_float(
                coupon.get("savings")
                or coupon.get("savings_inr")
                or coupon.get("max_discount")
                or coupon.get("discount_amount")
            )
            min_order = _coerce_float(
                coupon.get("min_order")
                or coupon.get("min_cart_amount")
                or coupon.get("minOrderValue")
            )
            description = (
                coupon.get("description")
                or coupon.get("header")
                or coupon.get("title")
                or ""
            )
            deals.append(
                RankedDeal(
                    restaurant_name=rname,
                    restaurant_id=rid,
                    coupon_code=str(code),
                    savings_inr=savings,
                    min_order=min_order,
                    description=str(description),
                )
            )

    deals.sort(key=lambda d: (-d.savings_inr, d.min_order))
    return deals[:MAX_RESULTS]
