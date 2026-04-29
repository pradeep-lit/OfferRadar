from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    swiggy_mcp_token: str
    swiggy_mcp_endpoint: str
    swiggy_address_id: str
    llm_model: str
    request_timeout: float


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {key}. "
            f"Set it in your .env file."
        )
    return value


def load_settings() -> Settings:
    return Settings(
        swiggy_mcp_token=_require("SWIGGY_MCP_TOKEN"),
        swiggy_mcp_endpoint=os.getenv(
            "SWIGGY_MCP_ENDPOINT", "https://mcp.swiggy.com/food"
        ),
        swiggy_address_id=_require("SWIGGY_ADDRESS_ID"),
        llm_model=os.getenv("LLM_MODEL", "claude-opus-4-5"),
        request_timeout=float(os.getenv("REQUEST_TIMEOUT", "30")),
    )
