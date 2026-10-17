"""Anti-Hallucination Crypto Agent — powered by CryptoCapi."""

import asyncio
import json
import os
from collections.abc import Coroutine

import typer
from dotenv import load_dotenv

from cryptocapi.client import (
    CryptoCapiClient,
    DemoCoinRestricted,
    ProEngineRequired,
    resolve_api_key,
)
from cryptocapi.seal import SealStatus
from display.terminal import (
    console,
    render_batch,
    render_demo_restricted,
    render_error,
    render_insight,
    render_no_analysis,
    render_pro_required,
    render_scan,
    render_sentiment_change,
)

load_dotenv()

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


def _run_async(coro: Coroutine[object, object, None]) -> None:
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
        30, "--interval", "-i", min=1, help="Polling interval in minutes (requires --watch)"
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Print the raw API response as JSON (verify it yourself)"
    ),
) -> None:
    """Analyze a single coin with full anti-hallucination audit trail."""
    if json_output and watch:
        # --json is a one-shot dump meant for a file. It used to win silently and
        # drop --watch; polling it instead would chain JSON documents into one
        # stream no parser reads. Neither is what was asked, so say so.
        raise typer.BadParameter(
            "--json prints one response and exits; it cannot be combined with --watch.",
            param_hint="'--json'",
        )

    async def _run() -> None:
        client = _get_client()

        # Raw JSON mode: one-shot dump of exactly what the API returned, so a
        # dev can inspect the audit_trail and reproduce the protocol_hash. Always
        # emits valid JSON (ensure_ascii keeps it safe on non-UTF-8 terminals).
        # No analysis prints `null`, which is what the API said, and exits 0.
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
                raise typer.Exit(1)
            except Exception as exc:
                print(json.dumps({"error": str(exc)}, indent=2))
                raise typer.Exit(1)
            return

        last_sentiment: str | None = None
        while True:
            seal_mismatch = False
            try:
                data = await client.get_insight(coin_id)
                if data is None:
                    # An answer, not a failure: no engine has analyzed this coin
                    # yet. A one-shot run exits 0; --watch waits for one.
                    render_no_analysis(coin_id)
                else:
                    check = render_insight(data, coin_id)
                    seal_mismatch = check.status is SealStatus.MISMATCH
                    sentiment = data.get("sentiment")
                    # The flip is what --watch is for. It goes after the render so
                    # it is the last thing on screen while the next wait runs.
                    if last_sentiment and sentiment and sentiment != last_sentiment:
                        render_sentiment_change(last_sentiment, sentiment)
                    last_sentiment = sentiment or last_sentiment
            except DemoCoinRestricted as exc:
                render_demo_restricted(exc.user_message)
                # Not a transient failure, so --watch stops too: the demo key
                # refuses this coin on every poll, and retrying would only spend
                # the demo's hourly quota on the same refusal.
                raise typer.Exit(1)
            except Exception as exc:
                render_error(str(exc))
                # Watch mode polls through transient failures; a one-shot run
                # reports them in its exit code so scripts can react.
                if not watch:
                    raise typer.Exit(1)

            if not watch:
                # A seal that does not match is the one outcome a script must
                # never read as success. Raised here, outside the try: inside it,
                # `except Exception` would catch the Exit as an error.
                if seal_mismatch:
                    raise typer.Exit(1)
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
        help="Ranking order, not a filter: balanced | aggressive | conservative",
    ),
    # The API validates strategy and limit and says what it rejected (ApiError),
    # so its bounds are documented here, not duplicated where they could drift.
    limit: int = typer.Option(10, "--limit", "-l", help="Number of results to show (1-50)"),
) -> None:
    """Rank the Quant Plus universe by proximity to each asset's own anomaly threshold."""

    async def _run() -> None:
        client = _get_client()
        try:
            results = await client.get_market_scan(strategy=strategy, limit=limit)
            render_scan(results, strategy)
        except ProEngineRequired as exc:
            render_pro_required(exc.user_message)
            raise typer.Exit(1)
        except Exception as exc:
            render_error(str(exc))
            raise typer.Exit(1)

    _run_async(_run())


@app.command()
def batch(
    symbols: list[str] = typer.Argument(
        ..., help="Coin slugs to analyze (up to 50), e.g. bitcoin ethereum solana"
    ),
) -> None:
    """Analyze multiple coins at once and compare their signals."""

    async def _run() -> None:
        client = _get_client()
        try:
            results = await client.get_batch_signals(symbols)
            render_batch(results)
        except DemoCoinRestricted as exc:
            # The demo key reaches batch for bitcoin and ethereum; one other coin
            # in the list and the API rejects the whole batch.
            render_demo_restricted(exc.user_message)
            raise typer.Exit(1)
        except ProEngineRequired as exc:
            render_pro_required(exc.user_message)
            raise typer.Exit(1)
        except Exception as exc:
            render_error(str(exc))
            raise typer.Exit(1)

    _run_async(_run())


if __name__ == "__main__":
    app()
