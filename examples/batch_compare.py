"""Batch compare — analyze multiple coins in a single request.

Usage:
    python examples/batch_compare.py bitcoin ethereum solana
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from cryptocapi.client import CryptoCapiClient, ProEngineRequired, resolve_api_key
from display.terminal import render_batch, render_pro_required

_DEFAULT_COINS = ["bitcoin", "ethereum", "solana"]


async def main(symbols: list[str]) -> None:
    client = CryptoCapiClient(api_key=resolve_api_key())
    try:
        results = await client.get_batch_signals(symbols)
    except ProEngineRequired as exc:
        # The demo key does not reach Quant Plus. That is the expected answer
        # here, so show the offer instead of dying on a traceback.
        render_pro_required(exc.user_message)
        return
    render_batch(results)


if __name__ == "__main__":
    coins = sys.argv[1:] if len(sys.argv) > 1 else _DEFAULT_COINS
    asyncio.run(main(coins))
