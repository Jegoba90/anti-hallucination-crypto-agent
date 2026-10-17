"""The client must read what CryptoCapi actually sends, not what models.py assumed.

Every endpoint but the insight failed on its first successful call. Scan and
batch read `data` as the list when the rows sit under `data.results`; prices and
the market summary demanded a `data` envelope those routes never had; and the
demo-key restriction was looked for inside `message` when the code sits flat in
the body, so it was never raised. A green suite missed all of it because no test
put a real response through the client. These do.

No network and no key: each response is replayed through an httpx.MockTransport
from tests/fixtures/api, captured byte for byte from the live API on 2026-10-16.
The one exception is the scan, which the demo key cannot reach: that fixture is
the example the OpenAPI document publishes for the route.
"""

import asyncio
import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cryptocapi import (
    ApiError,
    CryptoCapiClient,
    DemoCoinRestricted,
    ProEngineRequired,
    UnexpectedResponse,
)

_API = Path(__file__).parent / "fixtures" / "api"

_PULSE_BODY = {
    "status": "success",
    "data": {
        "engine_used": "radar",
        "asset": {"id": "solana", "symbol": "SOL"},
        "sentiment": "neutral",
    },
}


def _fixture(name: str) -> dict:
    return json.loads((_API / name).read_text(encoding="utf-8"))


def _captured(status: int, name: str) -> httpx.Response:
    """A response carrying the captured bytes, untouched by a json round trip."""
    return httpx.Response(
        status,
        content=(_API / name).read_bytes(),
        headers={"content-type": "application/json"},
    )


class _Replay:
    """Answer each request with the next canned response, and keep the requests."""

    def __init__(self, *responses: httpx.Response) -> None:
        self._responses = list(responses)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._responses.pop(0)


def _client(replay: _Replay) -> CryptoCapiClient:
    return CryptoCapiClient(
        api_key="demo_btc_eth_public", transport=httpx.MockTransport(replay)
    )


class TestQuantRowsSitUnderResults:
    def test_batch_returns_the_rows_not_the_envelope(self) -> None:
        replay = _Replay(_captured(200, "batch_btc_eth.json"))

        rows = asyncio.run(_client(replay).get_batch_signals(["bitcoin", "ethereum"]))

        assert [row["asset"]["id"] for row in rows] == ["bitcoin", "ethereum"]
        assert all(row["available"] for row in rows)

    def test_batch_sends_coin_ids_and_the_key(self) -> None:
        replay = _Replay(_captured(200, "batch_btc_eth.json"))

        asyncio.run(_client(replay).get_batch_signals(["bitcoin", "ethereum"]))

        sent = replay.requests[0]
        assert json.loads(sent.content) == {"symbols": ["bitcoin", "ethereum"]}
        assert sent.headers["x-api-key"] == "demo_btc_eth_public"

    def test_scan_returns_the_ranked_rows(self) -> None:
        replay = _Replay(_captured(200, "market_scan_openapi_example.json"))

        rows = asyncio.run(_client(replay).get_market_scan(strategy="aggressive", limit=2))

        assert [row["asset"]["id"] for row in rows] == ["bitcoin", "zcash"]
        # The two axes the ranking runs on, which the old model did not know about.
        assert rows[0]["threshold_proximity"] == 0.3919
        assert rows[0]["evidence_weight"] == 1

    def test_a_bare_list_under_data_is_still_refused(self) -> None:
        """The shape guard stays: rows straight under `data` are not the contract."""
        replay = _Replay(httpx.Response(200, json={"status": "success", "data": []}))

        with pytest.raises(UnexpectedResponse):
            asyncio.run(_client(replay).get_batch_signals(["bitcoin"]))


class TestPublicRoutesHaveNoEnvelope:
    def test_prices_body_is_the_array(self) -> None:
        replay = _Replay(_captured(200, "prices_latest.json"))

        rows = asyncio.run(_client(replay).get_prices(limit=2))

        assert [row["id"] for row in rows] == ["bitcoin", "ethereum"]
        # Pins the caveat in models.PriceItem: money arrives as decimal strings.
        assert isinstance(rows[0]["current_price"], str)

    def test_market_summary_body_is_the_object(self) -> None:
        replay = _Replay(_captured(200, "market_summary.json"))

        summary = asyncio.run(_client(replay).get_market_summary())

        # The pair models.py once had backwards: the number is the index.
        assert isinstance(summary["fear_greed_index"], int)
        assert summary["fear_greed_value"] == _fixture("market_summary.json")["fear_greed_value"]
        assert "market_cap_change_percentage_24h_usd" in summary

    def test_a_prices_body_that_is_not_an_array_is_refused(self) -> None:
        replay = _Replay(httpx.Response(200, json={"data": []}))

        with pytest.raises(UnexpectedResponse):
            asyncio.run(_client(replay).get_prices())


class TestDemoRestrictionIsRecognised:
    def test_insight_raises_instead_of_falling_back_to_pulse(self) -> None:
        replay = _Replay(_captured(403, "demo_coin_restricted_403.json"))

        with pytest.raises(DemoCoinRestricted) as caught:
            asyncio.run(_client(replay).get_insight("solana"))

        assert caught.value.user_message == _fixture("demo_coin_restricted_403.json")["message"]
        assert len(replay.requests) == 1, "the restriction must not be retried as Pulse"

    def test_batch_with_a_coin_outside_the_demo_is_the_restriction(self) -> None:
        """A 403 too, but not the plan gate: the fix is the coin list, not a plan."""
        replay = _Replay(_captured(403, "demo_coin_restricted_403.json"))

        with pytest.raises(DemoCoinRestricted):
            asyncio.run(_client(replay).get_batch_signals(["bitcoin", "solana"]))

    def test_scan_on_the_demo_key_is_the_plan_gate(self) -> None:
        replay = _Replay(_captured(403, "product_not_included_403.json"))

        with pytest.raises(ProEngineRequired) as caught:
            asyncio.run(_client(replay).get_market_scan())

        assert caught.value.user_message == _fixture("product_not_included_403.json")["message"]

    def test_a_403_without_the_code_still_falls_back_to_pulse(self) -> None:
        """The free-tier path the restriction check must not swallow."""
        replay = _Replay(
            httpx.Response(403, json={"status": "error", "message": "PRO plan required"}),
            httpx.Response(200, json=_PULSE_BODY),
        )

        data = asyncio.run(_client(replay).get_insight("solana"))

        assert data is not None
        assert data["sentiment"] == "neutral"
        assert [r.url.params["view"] for r in replay.requests] == ["alpha", "pulse"]


class TestNoAnalysisIsAnAnswer:
    def test_null_data_comes_back_as_none_not_as_an_error(self) -> None:
        """The API's `data: null`: no engine has analyzed the coin. Not a failure."""
        replay = _Replay(_captured(200, "insight_no_analysis.json"))

        assert asyncio.run(_client(replay).get_insight("notacoin-xyz")) is None


class TestOtherFailuresSayWhatTheApiSaid:
    """Anything but the plan gate and the demo restriction used to leak httpx's
    own message: the internal URL and a link to MDN, without the API's words."""

    def test_a_validation_error_names_what_was_rejected(self) -> None:
        replay = _Replay(_captured(400, "batch_validation_400.json"))

        with pytest.raises(ApiError) as caught:
            asyncio.run(_client(replay).get_batch_signals([]))

        assert caught.value.status_code == 400
        # "Validation failed" alone says nothing; the detail lives in `errors`.
        assert "Validation failed" in caught.value.user_message
        assert "body.symbols" in caught.value.user_message

    def test_no_url_and_no_mdn_link_reach_the_message(self) -> None:
        replay = _Replay(_captured(400, "batch_validation_400.json"))

        with pytest.raises(ApiError) as caught:
            asyncio.run(_client(replay).get_batch_signals([]))

        assert "api.cryptocapi.com" not in str(caught.value)
        assert "mozilla" not in str(caught.value)

    def test_a_rate_limit_carries_the_apis_message(self) -> None:
        # Hand-built: the demo quota was not burned to capture a real 429.
        replay = _Replay(
            httpx.Response(429, json={"status": "error", "message": "Rate limit exceeded"})
        )

        with pytest.raises(ApiError) as caught:
            asyncio.run(_client(replay).get_insight("bitcoin"))

        assert caught.value.status_code == 429
        assert "Rate limit exceeded" in caught.value.user_message

    def test_a_body_that_is_not_json_still_names_the_status(self) -> None:
        """A gateway answering an outage with HTML, not our envelope."""
        replay = _Replay(httpx.Response(502, text="<html>Bad Gateway</html>"))

        with pytest.raises(ApiError) as caught:
            asyncio.run(_client(replay).get_prices())

        assert caught.value.user_message == "CryptoCapi answered 502 Bad Gateway"

    def test_code_that_caught_httpx_errors_still_catches_it(self) -> None:
        replay = _Replay(httpx.Response(500, json={"status": "error", "message": "boom"}))

        with pytest.raises(httpx.HTTPStatusError):
            asyncio.run(_client(replay).get_market_summary())
