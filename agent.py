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
from cryptocapi.seal import SealStatus, check_seal
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
        "Inspect CryptoCapi market analysis, reported corrections, and seal integrity.\n\n"
        "Market indicators and narrative are supplied by the CryptoCapi API.\n"
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
        False, "--json", help="Print the API insight data as JSON (verify it yourself)"
    ),
    require_verified_seal: bool = typer.Option(
        False,
        "--require-verified-seal",
        help="Reject readings without a matching supported process seal (covered fields only)",
    ),
) -> None:
    """Inspect one coin's analysis and any audit trail returned by the API."""
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
        # No analysis prints `null`; strict seal mode then exits nonzero.
        if json_output:
            try:
                data = await client.get_insight(coin_id)
                print(json.dumps(data, indent=2, ensure_ascii=True, allow_nan=False))
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
            check = check_seal(data) if data is not None else None
            if (check is not None and check.status is SealStatus.MISMATCH) or (
                require_verified_seal and (check is None or check.status is not SealStatus.VERIFIED)
            ):
                raise typer.Exit(1)
            return

        last_sentiment: str | None = None
        while True:
            reading_rejected = False
            try:
                data = await client.get_insight(coin_id)
                if data is None:
                    # An answer, not a failure: no engine has analyzed this coin
                    # yet. A one-shot run exits 0; --watch waits for one.
                    render_no_analysis(coin_id)
                    reading_rejected = require_verified_seal
                else:
                    check = render_insight(data, coin_id)
                    reading_rejected = check.status is SealStatus.MISMATCH or (
                        require_verified_seal and check.status is not SealStatus.VERIFIED
                    )
                    if require_verified_seal and check.status is SealStatus.UNCHECKED:
                        render_error(f"A verified process seal is required: {check.reason}")
                    # A failed integrity check must not trigger an alert or
                    # replace the previous reading used by the next poll.
                    sentiment = None if reading_rejected else data.get("sentiment")
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
                # Rejected readings must not be reported as success. Raised
                # here, outside the try: inside it,
                # `except Exception` would catch the Exit as an error.
                if reading_rejected:
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
