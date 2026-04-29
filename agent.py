"""Conversation orchestration + tool-call dispatch loop."""
from __future__ import annotations

import asyncio
import json
from typing import Any, Awaitable, Callable

from coupon_ranker import rank_deals
from llm_client import LLMClient
from swiggy_mcp import SwiggyMCPClient
from tools import SWIGGY_TOOLS

SYSTEM_PROMPT = """\
You are OfferRadar, an AI agent that finds the cheapest Swiggy food order for the user.

Workflow you MUST follow for any food request:
1. Call `search_restaurants` with the user's query and their address_id.
2. Collect the top restaurant IDs from the results (up to ~10).
3. Call `fetch_food_coupons_bulk` ONCE with all those IDs — never call
   `fetch_food_coupons` serially in a loop.
4. Call `rank_deals` on the bulk result to get the top deals by ₹ savings.
5. Present the best deal to the user using this exact format:

🏆 Best Deal: <Restaurant>
Coupon: <CODE>
Savings: ₹<amount>

   Then list the runner-up deals briefly.
6. Ask the user if they want to apply the best coupon.
7. If they say yes, call `update_food_cart` (if items are provided) and
   `apply_food_coupon`.
8. Before calling `place_food_order`, you MUST receive an explicit "yes"
   from the user in the conversation. Set user_confirmed=true only then.

Hard rules:
- Never invent coupon codes or restaurant IDs — only use values returned by tools.
- If a tool returns an `error` field, surface it to the user gracefully.
- Keep responses concise. The user is on a CLI.
"""

MAX_TOOL_ITERATIONS = 10


ToolHandler = Callable[[dict[str, Any]], Awaitable[Any]]


def _safe_json_loads(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _stringify_result(result: Any) -> str:
    try:
        return json.dumps(result, default=str)
    except (TypeError, ValueError):
        return str(result)


class Agent:
    def __init__(
        self,
        llm: LLMClient,
        swiggy: SwiggyMCPClient,
        address_id: str,
    ) -> None:
        self._llm = llm
        self._swiggy = swiggy
        self._address_id = address_id
        self.history: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        self._handlers: dict[str, ToolHandler] = {
            "search_restaurants": self._h_search_restaurants,
            "fetch_food_coupons": self._h_fetch_food_coupons,
            "fetch_food_coupons_bulk": self._h_fetch_food_coupons_bulk,
            "update_food_cart": self._h_update_food_cart,
            "apply_food_coupon": self._h_apply_food_coupon,
            "get_food_cart": self._h_get_food_cart,
            "rank_deals": self._h_rank_deals,
            "place_food_order": self._h_place_food_order,
        }

    # ----- tool handlers -----

    async def _h_search_restaurants(self, args: dict[str, Any]) -> Any:
        return await self._swiggy.search_restaurants(
            query=args.get("query", ""),
            address_id=args.get("address_id") or self._address_id,
        )

    async def _h_fetch_food_coupons(self, args: dict[str, Any]) -> Any:
        return await self._swiggy.fetch_food_coupons(
            restaurant_id=args.get("restaurant_id", ""),
            address_id=args.get("address_id") or self._address_id,
        )

    async def _h_fetch_food_coupons_bulk(self, args: dict[str, Any]) -> Any:
        ids = args.get("restaurant_ids") or []
        if not isinstance(ids, list):
            return {"error": "restaurant_ids must be a list"}
        return await self._swiggy.fetch_food_coupons_bulk(
            restaurant_ids=[str(r) for r in ids],
            address_id=args.get("address_id") or self._address_id,
        )

    async def _h_update_food_cart(self, args: dict[str, Any]) -> Any:
        return await self._swiggy.update_food_cart(
            restaurant_id=args.get("restaurant_id", ""),
            items=args.get("items") or [],
            address_id=args.get("address_id") or self._address_id,
        )

    async def _h_apply_food_coupon(self, args: dict[str, Any]) -> Any:
        return await self._swiggy.apply_food_coupon(
            coupon_code=args.get("coupon_code", ""),
            restaurant_id=args.get("restaurant_id", ""),
            address_id=args.get("address_id") or self._address_id,
        )

    async def _h_get_food_cart(self, args: dict[str, Any]) -> Any:
        return await self._swiggy.get_food_cart(
            address_id=args.get("address_id") or self._address_id,
        )

    async def _h_rank_deals(self, args: dict[str, Any]) -> Any:
        responses = args.get("coupon_responses") or []
        if not isinstance(responses, list):
            return {"error": "coupon_responses must be a list"}
        ranked = rank_deals(responses)
        return {"deals": [d.to_dict() for d in ranked]}

    async def _h_place_food_order(self, args: dict[str, Any]) -> Any:
        if not args.get("user_confirmed"):
            return {
                "error": (
                    "Refusing to place order: user_confirmed is false. Ask the "
                    "user to type 'yes' first, then retry."
                )
            }
        return await self._swiggy.place_food_order(
            address_id=args.get("address_id") or self._address_id,
        )

    # ----- dispatch -----

    async def _dispatch(self, name: str, args: dict[str, Any]) -> Any:
        handler = self._handlers.get(name)
        if handler is None:
            return {"error": f"Unknown tool: {name}"}
        try:
            return await handler(args)
        except Exception as exc:  # noqa: BLE001 - never crash the loop
            return {"error": f"Tool '{name}' raised {type(exc).__name__}: {exc}"}

    async def _execute_tool_calls(self, tool_calls: list[Any]) -> list[dict[str, Any]]:
        async def run_one(call: Any) -> dict[str, Any]:
            fn = getattr(call, "function", None) or call.get("function", {})
            name = getattr(fn, "name", None) or fn.get("name", "")
            raw_args = getattr(fn, "arguments", None) or fn.get("arguments", "")
            args = _safe_json_loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
            tool_call_id = getattr(call, "id", None) or call.get("id", "")

            result = await self._dispatch(name, args)
            return {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": name,
                "content": _stringify_result(result),
            }

        # Execute every tool the LLM requested in this turn concurrently
        return await asyncio.gather(*(run_one(c) for c in tool_calls))

    # ----- public turn loop -----

    async def run_turn(self, user_message: str) -> str:
        self.history.append({"role": "user", "content": user_message})

        for _ in range(MAX_TOOL_ITERATIONS):
            try:
                response = await self._llm.chat(
                    messages=self.history, tools=SWIGGY_TOOLS
                )
            except Exception as exc:  # noqa: BLE001
                msg = f"⚠️  LLM call failed: {type(exc).__name__}: {exc}"
                self.history.append({"role": "assistant", "content": msg})
                return msg

            message = response.choices[0].message
            tool_calls = getattr(message, "tool_calls", None)

            if tool_calls:
                # LiteLLM returns Pydantic-like objects; convert to a dict the
                # provider will accept on the next round-trip.
                self.history.append(
                    message.model_dump() if hasattr(message, "model_dump") else dict(message)
                )
                results = await self._execute_tool_calls(tool_calls)
                self.history.extend(results)
                continue

            content = (message.content or "").strip()
            self.history.append({"role": "assistant", "content": content})
            return content

        fallback = "⚠️  Hit the tool-iteration limit without a final answer."
        self.history.append({"role": "assistant", "content": fallback})
        return fallback
