"""Thin LiteLLM wrapper. Provider-agnostic — never import provider SDKs here."""
from __future__ import annotations

from typing import Any

import litellm


class LLMClient:
    def __init__(self, model: str) -> None:
        self.model = model

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> Any:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        return await litellm.acompletion(**kwargs)
