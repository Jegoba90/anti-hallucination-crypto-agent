"""Watch mode — poll a coin every N minutes and flag sentiment changes.

Usage:
    python examples/watch_mode.py bitcoin 15
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

from cryptocapi.client import CryptoCapiClient, DemoCoinRestricted, resolve_api_key
from display.terminal import (
    console,
    render_demo_restricted,
    render_error,
    render_insight,
    render_no_analysis,
    render_sentiment_change,
)

load_dotenv()


async def watch(coin_id: str, interval_minutes: int) -> None:
    client = CryptoCapiClient(api_key=resolve_api_key())
    last_sentiment: str | None = None

    while True:
        try:
            data = await client.get_insight(coin_id)
            if data is None:
                # No analysis yet: an answer, not an error. Keep waiting for one.
                render_no_analysis(coin_id)
            else:
                render_insight(data, coin_id)
                current_sentiment = data.get("sentiment")
                if last_sentiment and current_sentiment and current_sentiment != last_sentiment:
                    render_sentiment_change(last_sentiment, current_sentiment)
                last_sentiment = current_sentiment or last_sentiment

        except DemoCoinRestricted as exc:
            # Permanent: the demo key refuses this coin on every poll.
            render_demo_restricted(exc.user_message)
            return
        except Exception as exc:
            render_error(str(exc))

        console.print(f"  [dim]Refreshing in {interval_minutes} min — Ctrl+C to stop[/dim]\n")
        await asyncio.sleep(interval_minutes * 60)


if __name__ == "__main__":
    coin = sys.argv[1] if len(sys.argv) > 1 else "bitcoin"
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    try:
        asyncio.run(watch(coin, interval))
    except KeyboardInterrupt:
        console.print("\n  [dim]Stopped.[/dim]\n")
