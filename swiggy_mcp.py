"""Async HTTP client for the Swiggy MCP server. Pure transport — no LLM logic."""
from __future__ import annotations

import asyncio
import itertools
from typing import Any

import httpx


class SwiggyMCPClient:
    def __init__(
        self,
        endpoint: str,
        token: str,
        timeout: float = 30.0,
    ) -> None:
        self._endpoint = endpoint
        self._token = token
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._id_counter = itertools.count(1)

    async def __aenter__(self) -> "SwiggyMCPClient":
        self._client = httpx.AsyncClient(
            timeout=self._timeout,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if self._client is None:
            raise RuntimeError("SwiggyMCPClient must be used as an async context manager")

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
            "id": next(self._id_counter),
        }

        try:
            response = await self._client.post(self._endpoint, json=payload)
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPStatusError as exc:
            return {
                "error": f"Swiggy MCP HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            }
        except httpx.HTTPError as exc:
            return {"error": f"Swiggy MCP network error: {exc}"}
        except ValueError as exc:
            return {"error": f"Swiggy MCP returned invalid JSON: {exc}"}

        if "error" in body and body["error"]:
            err = body["error"]
            msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            return {"error": f"Swiggy MCP error: {msg}"}

        return body.get("result", body)

    # ----- public tool surface -----

    async def search_restaurants(self, query: str, address_id: str) -> dict[str, Any]:
        return await self._call(
            "search_restaurants",
            {"query": query, "addressId": address_id},
        )

    async def fetch_food_coupons(
        self, restaurant_id: str, address_id: str
    ) -> dict[str, Any]:
        result = await self._call(
            "fetch_food_coupons",
            {"restaurantId": restaurant_id, "addressId": address_id},
        )
        # Ensure caller can identify which restaurant this belongs to
        if isinstance(result, dict) and "restaurant_id" not in result:
            result["restaurant_id"] = restaurant_id
        return result

    async def fetch_food_coupons_bulk(
        self, restaurant_ids: list[str], address_id: str
    ) -> list[dict[str, Any]]:
        """Parallel coupon fetch — the only correct way to query multiple restaurants."""
        if not restaurant_ids:
            return []
        tasks = [
            self.fetch_food_coupons(rid, address_id) for rid in restaurant_ids
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        normalized: list[dict[str, Any]] = []
        for rid, result in zip(restaurant_ids, results):
            if isinstance(result, Exception):
                normalized.append(
                    {"restaurant_id": rid, "error": f"fetch failed: {result}"}
                )
            else:
                normalized.append(result)
        return normalized

    async def update_food_cart(
        self,
        restaurant_id: str,
        items: list[dict[str, Any]],
        address_id: str,
    ) -> dict[str, Any]:
        return await self._call(
            "update_food_cart",
            {
                "restaurantId": restaurant_id,
                "items": items,
                "addressId": address_id,
            },
        )

    async def apply_food_coupon(
        self, coupon_code: str, restaurant_id: str, address_id: str
    ) -> dict[str, Any]:
        return await self._call(
            "apply_food_coupon",
            {
                "couponCode": coupon_code,
                "restaurantId": restaurant_id,
                "addressId": address_id,
            },
        )

    async def get_food_cart(self, address_id: str) -> dict[str, Any]:
        return await self._call("get_food_cart", {"addressId": address_id})

    async def place_food_order(self, address_id: str) -> dict[str, Any]:
        return await self._call("place_food_order", {"addressId": address_id})
