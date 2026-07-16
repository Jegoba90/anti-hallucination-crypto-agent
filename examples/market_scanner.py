"""Market scanner — rank all tracked assets by signal strength.

Usage:
    python examples/market_scanner.py balanced 10
    python examples/market_scanner.py aggressive 5
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from cryptocapi.client import CryptoCapiClient, ProEngineRequired, resolve_api_key
from display.terminal import render_pro_required, render_scan


async def main(strategy: str, limit: int) -> None:
    client = CryptoCapiClient(api_key=resolve_api_key())
    try:
        results = await client.get_market_scan(strategy=strategy, limit=limit)
    except ProEngineRequired as exc:
        # The demo key does not reach Quant Plus. That is the expected answer
        # here, so show the offer instead of dying on a traceback.
        render_pro_required(exc.user_message)
        return
    render_scan(results, strategy)


if __name__ == "__main__":
    strategy = sys.argv[1] if len(sys.argv) > 1 else "balanced"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    asyncio.run(main(strategy, limit))
