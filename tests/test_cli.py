"""The CLI must do what the README says it does.

The README promises a watch mode that flags sentiment changes. The loop in
`coin --watch` re-rendered the coin and slept, comparing nothing: the flag lived
only in examples/watch_mode.py. It also kept polling through a demo-key
restriction no retry can lift, and `--json` silently swallowed `--watch`. These
tests drive the real Typer app with a fake client, and with a sleep that ends
the otherwise endless loop.
"""

import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agent
from cryptocapi import DemoCoinRestricted
from display.terminal import console

_RESTRICTED = "The public demo key only supports bitcoin and ethereum."


class _StopWatching(Exception):
    """Raised by the fake sleep to end a --watch loop after a set number of polls."""


class _FakeClient:
    def __init__(self, *answers: object) -> None:
        self._answers = list(answers)
        self.calls = 0

    async def _next(self) -> object:
        self.calls += 1
        answer = self._answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    async def get_insight(self, coin_id: str) -> object:
        return await self._next()

    async def get_batch_signals(self, symbols: list[str]) -> object:
        return await self._next()


def _insight(sentiment: str) -> dict:
    return {"asset": {"id": "bitcoin", "symbol": "BTC"}, "sentiment": sentiment}


def _invoke(monkeypatch: pytest.MonkeyPatch, client: _FakeClient, args: list[str], polls: int = 1):
    """Run the app; a --watch loop ends at its `polls`-th sleep."""
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        if len(sleeps) >= polls:
            raise _StopWatching

    monkeypatch.setattr(agent, "_get_client", lambda: client)
    monkeypatch.setattr(agent.asyncio, "sleep", fake_sleep)
    with console.capture() as capture:
        result = CliRunner().invoke(agent.app, args)
    return result, capture.get(), sleeps


class TestWatchFlagsSentimentChanges:
    def test_a_flip_is_flagged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _FakeClient(_insight("neutral"), _insight("bullish"))

        _, out, _ = _invoke(monkeypatch, client, ["coin", "bitcoin", "--watch"], polls=2)

        assert "SENTIMENT CHANGED" in out
        assert "neutral → bullish" in out

    def test_a_steady_sentiment_is_not_flagged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _FakeClient(_insight("neutral"), _insight("neutral"))

        _, out, _ = _invoke(monkeypatch, client, ["coin", "bitcoin", "--watch"], polls=2)

        assert "SENTIMENT CHANGED" not in out

    def test_each_poll_is_compared_with_the_one_before(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client = _FakeClient(_insight("neutral"), _insight("bullish"), _insight("bullish"))

        _, out, _ = _invoke(monkeypatch, client, ["coin", "bitcoin", "--watch"], polls=3)

        assert out.count("SENTIMENT CHANGED") == 1


class TestWatchStopsOnlyOnPermanentFailures:
    def test_the_demo_restriction_ends_the_watch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _FakeClient(DemoCoinRestricted(_RESTRICTED))

        result, out, sleeps = _invoke(monkeypatch, client, ["coin", "solana", "--watch"])

        assert result.exit_code == 1
        assert sleeps == [], "a restriction no retry can lift must not be polled again"
        assert "DEMO KEY" in out

    def test_a_transient_error_keeps_watching(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _FakeClient(RuntimeError("read timeout"), _insight("neutral"))

        _, out, _ = _invoke(monkeypatch, client, ["coin", "bitcoin", "--watch"], polls=2)

        assert client.calls == 2
        assert "read timeout" in out


class TestFlagsThatCannotWork:
    def test_json_with_watch_is_rejected_not_ignored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _FakeClient()

        result, _, _ = _invoke(monkeypatch, client, ["coin", "bitcoin", "--json", "--watch"])

        assert result.exit_code == 2
        assert client.calls == 0

    def test_an_interval_below_one_minute_is_rejected(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """0 would poll in a tight loop against a 30-requests-an-hour demo key."""
        client = _FakeClient()

        result, _, _ = _invoke(
            monkeypatch, client, ["coin", "bitcoin", "--watch", "--interval", "0"]
        )

        assert result.exit_code == 2
        assert client.calls == 0


class TestNoAnalysisIsNotAnError:
    """`data: null` used to print "Error: `data` is not an object" and exit 1."""

    def test_a_one_shot_run_says_so_and_exits_cleanly(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client = _FakeClient(None)

        result, out, _ = _invoke(monkeypatch, client, ["coin", "bitcoin"])

        assert result.exit_code == 0
        assert "NO ANALYSIS YET" in out
        assert "Error" not in out

    def test_json_prints_what_the_api_said(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _FakeClient(None)

        result, _, _ = _invoke(monkeypatch, client, ["coin", "bitcoin", "--json"])

        assert result.exit_code == 0
        assert result.output.strip() == "null"

    def test_watch_keeps_waiting_for_an_analysis(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _FakeClient(None, _insight("neutral"))

        _, out, _ = _invoke(monkeypatch, client, ["coin", "bitcoin", "--watch"], polls=2)

        assert client.calls == 2
        assert "NO ANALYSIS YET" in out
        assert "SENTIMENT CHANGED" not in out


class TestBatchRestriction:
    def test_a_coin_outside_the_demo_shows_the_demo_banner(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client = _FakeClient(DemoCoinRestricted(_RESTRICTED))

        result, out, _ = _invoke(monkeypatch, client, ["batch", "bitcoin", "solana"])

        assert result.exit_code == 1
        assert "DEMO KEY" in out
        assert "QUANT ENGINES" not in out
