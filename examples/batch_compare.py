"""Batch compare — analyze multiple coins in a single request.

Usage:
    python examples/batch_compare.py                          # bitcoin ethereum, demo key
    python examples/batch_compare.py bitcoin ethereum solana  # any coin, trial key
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

from cryptocapi.client import (
    CryptoCapiClient,
    DemoCoinRestricted,
    ProEngineRequired,
    resolve_api_key,
)
from display.terminal import render_batch, render_demo_restricted, render_pro_required

load_dotenv()

# The two coins the public demo key reaches, so the default run just works.
_DEFAULT_COINS = ["bitcoin", "ethereum"]


async def main(symbols: list[str]) -> None:
    client = CryptoCapiClient(api_key=resolve_api_key())
    try:
        results = await client.get_batch_signals(symbols)
    except DemoCoinRestricted as exc:
        # The demo key rejects the whole batch if one coin is outside BTC/ETH.
        render_demo_restricted(exc.user_message)
        return
    except ProEngineRequired as exc:
        # The key in use does not include Quant Plus. That is an expected
        # answer, so show the offer instead of dying on a traceback.
        render_pro_required(exc.user_message)
        return
    render_batch(results)


if __name__ == "__main__":
    coins = sys.argv[1:] if len(sys.argv) > 1 else _DEFAULT_COINS
    asyncio.run(main(coins))
