"""Watch mode — poll a coin every N minutes and flag sentiment changes.

Usage:
    python examples/watch_mode.py bitcoin 15
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from cryptocapi.client import CryptoCapiClient
from display.terminal import console, render_insight


async def watch(coin_id: str, interval_minutes: int) -> None:
    api_key = os.getenv("CRYPTOCAPI_API_KEY", "")
    client = CryptoCapiClient(api_key=api_key)
    last_sentiment: str | None = None

    while True:
        try:
            data = await client.get_insight(coin_id)
            current_sentiment = data.get("sentiment", "neutral")

            if last_sentiment and current_sentiment != last_sentiment:
                console.print(
                    f"\n  [bold yellow]⚡ SENTIMENT CHANGED:[/bold yellow] "
                    f"{last_sentiment} → {current_sentiment}\n"
                )

            render_insight(data, coin_id)
            last_sentiment = current_sentiment

        except Exception as exc:
            console.print(f"\n  [red]Error:[/red] {exc}\n")

        console.print(f"  [dim]Refreshing in {interval_minutes} min — Ctrl+C to stop[/dim]\n")
        await asyncio.sleep(interval_minutes * 60)


if __name__ == "__main__":
    coin = sys.argv[1] if len(sys.argv) > 1 else "bitcoin"
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    asyncio.run(watch(coin, interval))
