"""Tool definitions in OpenAI JSON schema format. LiteLLM translates per provider."""
from __future__ import annotations

SWIGGY_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_restaurants",
            "description": (
                "Search for restaurants on Swiggy by dish or cuisine near the "
                "user's delivery address. Returns a list of restaurants with "
                "their IDs, names, ratings, and ETAs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Dish or cuisine name, e.g. 'biryani', 'pizza'",
                    },
                    "address_id": {
                        "type": "string",
                        "description": "User's delivery address ID",
                    },
                },
                "required": ["query", "address_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_food_coupons",
            "description": (
                "Fetch all available coupons for a single restaurant. "
                "Must be called once per restaurant — call in parallel for "
                "multiple restaurants."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "restaurant_id": {
                        "type": "string",
                        "description": "Restaurant ID returned by search_restaurants",
                    },
                    "address_id": {
                        "type": "string",
                        "description": "User's delivery address ID",
                    },
                },
                "required": ["restaurant_id", "address_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_food_coupons_bulk",
            "description": (
                "Fetch coupons for many restaurants in parallel. Prefer this "
                "over multiple fetch_food_coupons calls. Returns a mapping of "
                "restaurant_id to its coupons."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "restaurant_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of restaurant IDs to query in parallel",
                    },
                    "address_id": {
                        "type": "string",
                        "description": "User's delivery address ID",
                    },
                },
                "required": ["restaurant_ids", "address_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_food_cart",
            "description": "Add or update items in the Swiggy food cart for a restaurant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "restaurant_id": {"type": "string"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "item_id": {"type": "string"},
                                "quantity": {"type": "integer"},
                            },
                            "required": ["item_id", "quantity"],
                        },
                    },
                    "address_id": {"type": "string"},
                },
                "required": ["restaurant_id", "items", "address_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_food_coupon",
            "description": "Apply a coupon code to the current Swiggy cart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "coupon_code": {"type": "string"},
                    "restaurant_id": {"type": "string"},
                    "address_id": {"type": "string"},
                },
                "required": ["coupon_code", "restaurant_id", "address_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_food_cart",
            "description": "Get the current state of the Swiggy food cart, including totals.",
            "parameters": {
                "type": "object",
                "properties": {
                    "address_id": {"type": "string"},
                },
                "required": ["address_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rank_deals",
            "description": (
                "Rank coupon results by ₹ savings descending, breaking ties by "
                "min_order ascending. Returns the top 5 deals."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "coupon_responses": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Raw coupon response objects from fetch_food_coupons",
                    },
                },
                "required": ["coupon_responses"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "place_food_order",
            "description": (
                "IRREVERSIBLE: place the food order on Swiggy. The user MUST "
                "have explicitly confirmed 'yes' before this is called."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "address_id": {"type": "string"},
                    "user_confirmed": {
                        "type": "boolean",
                        "description": "Set to true only after the user typed 'yes'",
                    },
                },
                "required": ["address_id", "user_confirmed"],
            },
        },
    },
]
