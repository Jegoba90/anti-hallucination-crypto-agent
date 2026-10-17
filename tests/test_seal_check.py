"""The agent recomputes every seal it shows, and says only what it found.

The CLI printed a green check under the seal without ever checking it: no line
of the agent hashed anything, so when the engine changed its seal rule on
2026-09-01 the screen kept its check for six weeks. It now recomputes the seal
from the response, says whether it matches, exits non-zero when it does not, and
never calls a seal wrong when the agent is the one that fell behind.
"""

import json
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agent
from cryptocapi import SealStatus, check_seal
from cryptocapi.models import InsightData
from cryptocapi.seal import _digest
from display.terminal import console, render_insight

_ROOT = Path(__file__).resolve().parents[1]
_FIXTURES = _ROOT / "tests" / "fixtures"
_REAL_SEALS = [
    (_ROOT / "docs" / "comparisons" / "2026-07-20-btc" / "radar.json", "v2.1.0-radar"),
    (_FIXTURES / "radar_alpha_v2.2.0.json", "v2.2.0-radar"),
    (_FIXTURES / "api" / "insight_bitcoin_alpha.json", "v2.4.0-radar"),
    (_FIXTURES / "readme_demo_bitcoin_2026-10-17.json", "v2.4.0-radar"),
]
_LATEST = _FIXTURES / "readme_demo_bitcoin_2026-10-17.json"


def _data(path: Path) -> InsightData:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw.get("data", raw)


def _render(data: InsightData) -> str:
    with console.capture() as capture:
        render_insight(data, "bitcoin")
    return capture.get()


def _resealed_as(version: str, data: InsightData) -> InsightData:
    """The response as a future engine version would seal it under today's rule."""
    math = data["math_diagnostics"]
    trail = math["audit_trail"]
    trail["engine_version"] = version
    payload = {
        "algorithm_id": trail["algorithm_id"],
        "engine_version": version,
        "z_score": math["z_score"],
        "market_regime": math["market_regime"],
        "sentiment": data["sentiment"],
        "sentiment_override": trail["sentiment_override"],
        "filters_applied": trail["filters_applied"],
        "fields_overridden": trail["fields_overridden"],
    }
    trail["protocol_hash"] = _digest(payload, "fixed6")
    return data


class TestRealSealsVerify:
    @pytest.mark.parametrize(("path", "version"), _REAL_SEALS)
    def test_every_real_seal_verifies(self, path: Path, version: str) -> None:
        data = _data(path)

        assert data["math_diagnostics"]["audit_trail"]["engine_version"] == version
        assert check_seal(data).status is SealStatus.VERIFIED


class TestAChangedResponseIsCaught:
    @pytest.mark.parametrize(
        "change",
        [
            # The fixture reads bullish, 2.2794, BULLISH_TREND: each value differs.
            lambda d: d.__setitem__("sentiment", "bearish"),
            lambda d: d["math_diagnostics"].__setitem__("z_score", 3.9),
            lambda d: d["math_diagnostics"].__setitem__("market_regime", "RANGING_CHOP"),
            lambda d: d["math_diagnostics"]["audit_trail"].__setitem__("filters_applied", []),
            lambda d: d["math_diagnostics"]["audit_trail"]["fields_overridden"].pop(),
        ],
        ids=["sentiment", "z_score", "regime", "filters", "fields"],
    )
    def test_any_sealed_field_changed_is_a_mismatch(self, change) -> None:
        data = _data(_FIXTURES / "radar_alpha_v2.2.0.json")
        change(data)

        assert check_seal(data).status is SealStatus.MISMATCH


class TestTheAgentNeverAccusesWhatItCannotCheck:
    def test_a_response_without_a_seal_is_unchecked(self) -> None:
        data = _data(_LATEST)
        del data["math_diagnostics"]["audit_trail"]

        assert check_seal(data).status is SealStatus.UNCHECKED

    def test_a_seal_type_it_does_not_recompute_is_unchecked(self) -> None:
        data = _data(_LATEST)
        data["math_diagnostics"]["audit_trail"]["seal_type"] = "reproducible"

        assert check_seal(data).status is SealStatus.UNCHECKED

    def test_a_missing_sealed_field_is_unchecked(self) -> None:
        data = _data(_LATEST)
        del data["math_diagnostics"]["z_score"]

        check = check_seal(data)
        assert check.status is SealStatus.UNCHECKED
        assert "z_score" in check.reason

    def test_a_newer_engine_that_kept_the_rule_still_verifies(self) -> None:
        data = _resealed_as("v2.5.0-radar", _data(_LATEST))

        assert check_seal(data).status is SealStatus.VERIFIED

    def test_a_newer_engine_that_changed_the_rule_is_unchecked_not_wrong(self) -> None:
        """What happened on 2026-09-01: calling that a mismatch would accuse the API."""
        data = _resealed_as("v2.5.0-radar", _data(_LATEST))
        data["math_diagnostics"]["audit_trail"]["protocol_hash"] = "0x" + "ab" * 32

        check = check_seal(data)
        assert check.status is SealStatus.UNCHECKED
        assert "v2.5.0-radar" in check.reason


class TestTheScreenSaysWhatWasFound:
    def test_a_real_seal_reads_verified(self) -> None:
        out = _render(_data(_LATEST))

        assert "recomputed here from this response: it matches" in out
        assert "seal verified" in out
        assert "cannot say who sealed it" in out, "a match proves integrity, not origin"

    def test_a_changed_response_reads_does_not_match(self) -> None:
        data = _data(_LATEST)
        data["sentiment"] = "bullish"

        out = _render(data)

        assert "SEAL DOES NOT MATCH" in out
        assert "seal verified" not in out

    def test_a_seal_it_cannot_check_says_so(self) -> None:
        data = _resealed_as("v2.5.0-radar", _data(_LATEST))
        data["math_diagnostics"]["audit_trail"]["protocol_hash"] = "0x" + "ab" * 32

        out = _render(data)

        assert "seal not checked" in out
        assert "DOES NOT MATCH" not in out


class _StopWatching(Exception):
    pass


class _FakeClient:
    def __init__(self, *answers: InsightData) -> None:
        self._answers = list(answers)
        self.calls = 0

    async def get_insight(self, coin_id: str) -> InsightData:
        self.calls += 1
        return self._answers.pop(0)


def _invoke(monkeypatch: pytest.MonkeyPatch, client: _FakeClient, args: list[str], polls: int = 1):
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        if len(sleeps) >= polls:
            raise _StopWatching

    monkeypatch.setattr(agent, "_get_client", lambda: client)
    monkeypatch.setattr(agent.asyncio, "sleep", fake_sleep)
    with console.capture():
        return CliRunner().invoke(agent.app, args)


class TestTheCliActsOnAMismatch:
    def test_a_one_shot_run_on_a_changed_response_exits_non_zero(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        data = _data(_LATEST)
        data["sentiment"] = "bullish"

        result = _invoke(monkeypatch, _FakeClient(data), ["coin", "bitcoin"])

        assert result.exit_code == 1

    def test_a_verified_run_exits_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        result = _invoke(monkeypatch, _FakeClient(_data(_LATEST)), ["coin", "bitcoin"])

        assert result.exit_code == 0

    def test_watch_flags_it_and_keeps_watching(self, monkeypatch: pytest.MonkeyPatch) -> None:
        bad = _data(_LATEST)
        bad["sentiment"] = "bullish"
        client = _FakeClient(bad, _data(_LATEST))

        _invoke(monkeypatch, client, ["coin", "bitcoin", "--watch"], polls=2)

        assert client.calls == 2
