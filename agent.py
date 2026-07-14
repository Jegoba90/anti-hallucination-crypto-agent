"""Anti-Hallucination Crypto Agent — powered by CryptoCapi."""

import asyncio
import json
import os
from collections.abc import Coroutine
from typing import Any

import typer
from dotenv import load_dotenv

load_dotenv()

from cryptocapi.client import CryptoCapiClient, DemoCoinRestricted, resolve_api_key
from display.terminal import (
    console,
    render_batch,
    render_demo_restricted,
    render_insight,
    render_scan,
)

app = typer.Typer(
    help=(
        "Analyze crypto markets using AI — and see exactly what the AI hallucinated.\n\n"
        "Powered by CryptoCapi's 4-layer anti-hallucination pipeline.\n"
        "Get your free API key at https://cryptocapi.com"
    ),
    no_args_is_help=True,
)


def _get_client() -> CryptoCapiClient:
    base_url = os.getenv("CRYPTOCAPI_BASE_URL", "https://api.cryptocapi.com/v1")
    return CryptoCapiClient(api_key=resolve_api_key(), base_url=base_url)


def _run_async(coro: Coroutine[Any, Any, None]) -> None:
    """Run a command coroutine, exiting quietly on Ctrl+C (used by --watch)."""
    try:
        asyncio.run(coro)
    except KeyboardInterrupt:
        console.print("\n  [dim]Stopped.[/dim]\n")


@app.command()
def coin(
    coin_id: str = typer.Argument(..., help="Coin slug, e.g. bitcoin, ethereum, solana"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Poll continuously"),
    interval: int = typer.Option(
        30, "--interval", "-i", help="Polling interval in minutes (requires --watch)"
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Print the raw API response as JSON (verify it yourself)"
    ),
) -> None:
    """Analyze a single coin with full anti-hallucination audit trail."""

    async def _run() -> None:
        client = _get_client()

        # Raw JSON mode: one-shot dump of exactly what the API returned, so a
        # dev can inspect the audit_trail and reproduce the protocol_hash. Always
        # emits valid JSON (ensure_ascii keeps it safe on non-UTF-8 terminals).
        if json_output:
            try:
                data = await client.get_insight(coin_id)
                print(json.dumps(data, indent=2, ensure_ascii=True))
            except DemoCoinRestricted as exc:
                print(
                    json.dumps(
                        {"error": "demo_coin_restricted", "message": exc.user_message},
                        indent=2,
                    )
                )
            except Exception as exc:
                print(json.dumps({"error": str(exc)}, indent=2))
            return

        while True:
            try:
                data = await client.get_insight(coin_id)
                render_insight(data, coin_id)
            except DemoCoinRestricted as exc:
                render_demo_restricted(exc.user_message)
            except Exception as exc:
                console.print(f"\n  [bold red]Error:[/bold red] {exc}\n")

            if not watch:
                break

            console.print(
                f"  [dim]Next refresh in {interval} min — Ctrl+C to stop[/dim]\n"
            )
            await asyncio.sleep(interval * 60)

    _run_async(_run())


@app.command()
def scan(
    strategy: str = typer.Option(
        "balanced",
        "--strategy",
        "-s",
        help="Ranking strategy: balanced | aggressive | conservative",
    ),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of results to show"),
) -> None:
    """Rank all tracked assets by signal strength."""

    async def _run() -> None:
        client = _get_client()
        try:
            results = await client.get_market_scan(strategy=strategy, limit=limit)
            render_scan(results, strategy)
        except Exception as exc:
            console.print(f"\n  [bold red]Error:[/bold red] {exc}\n")

    _run_async(_run())


@app.command()
def batch(
    symbols: list[str] = typer.Argument(
        ..., help="Coin slugs to analyze, e.g. bitcoin ethereum solana"
    ),
) -> None:
    """Analyze multiple coins at once and compare their signals."""

    async def _run() -> None:
        client = _get_client()
        try:
            results = await client.get_batch_signals(symbols)
            render_batch(results)
        except Exception as exc:
            console.print(f"\n  [bold red]Error:[/bold red] {exc}\n")

    _run_async(_run())


if __name__ == "__main__":
    app()
