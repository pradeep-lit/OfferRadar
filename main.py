"""CLI entry point. Read input, print output, delegate everything else."""
from __future__ import annotations

import asyncio
import sys

from agent import Agent
from config import load_settings
from llm_client import LLMClient
from swiggy_mcp import SwiggyMCPClient

BANNER = """\
╭──────────────────────────────────────────╮
│  OfferRadar — Swiggy deal finder agent   │
│  Type 'exit' or Ctrl-D to quit.          │
╰──────────────────────────────────────────╯
"""


async def _read_line(prompt: str) -> str | None:
    """Read a line of input from stdin without blocking the event loop."""
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, input, prompt)
    except (EOFError, KeyboardInterrupt):
        return None


async def repl() -> int:
    print(BANNER)

    try:
        settings = load_settings()
    except RuntimeError as exc:
        print(f"❌  {exc}", file=sys.stderr)
        return 1

    llm = LLMClient(model=settings.llm_model)
    print(f"✓ Model: {settings.llm_model}")
    print(f"✓ Address: {settings.swiggy_address_id}\n")

    async with SwiggyMCPClient(
        endpoint=settings.swiggy_mcp_endpoint,
        token=settings.swiggy_mcp_token,
        timeout=settings.request_timeout,
    ) as swiggy:
        agent = Agent(llm=llm, swiggy=swiggy, address_id=settings.swiggy_address_id)

        while True:
            user_input = await _read_line("you › ")
            if user_input is None:
                print()
                break
            user_input = user_input.strip()
            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit", ":q"}:
                break

            reply = await agent.run_turn(user_input)
            print(f"\nagent › {reply}\n")

    print("Goodbye 👋")
    return 0


def main() -> None:
    try:
        sys.exit(asyncio.run(repl()))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
