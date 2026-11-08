"""Malformed upstream data must fail before it can look like a market reading."""

import asyncio
import json
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from cryptocapi import CryptoCapiClient, UnexpectedResponse

_FIXTURES = Path(__file__).parent / "fixtures" / "api"


def _body(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


def _client(body: object = None, *, raw: str | None = None) -> CryptoCapiClient:
    # content= deliberately permits malformed JSON for the decoder tests.
    encoded = raw if raw is not None else json.dumps(body)
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=encoded))
    return CryptoCapiClient("test-key", transport=transport)


@pytest.mark.parametrize("value", [True, "0.62", None, -0.01, 1.01, float("nan"), float("inf")])
def test_invalid_confidence_is_not_renderable_as_a_measurement(value) -> None:
    body = _body("insight_bitcoin_alpha.json")
    body["data"]["confidence"]["score"] = value

    with pytest.raises(UnexpectedResponse):
        asyncio.run(_client(body).get_insight("bitcoin"))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("asset", []),
        ("sentiment", True),
        ("statistical_anomaly_detected", "false"),
        ("math_diagnostics", "not an object"),
        ("analysis", []),
        ("confidence", {"label": "HIGH"}),
    ],
)
def test_present_insight_fields_must_match_their_types(field, value) -> None:
    body = _body("insight_bitcoin_alpha.json")
    body["data"][field] = value

    with pytest.raises(UnexpectedResponse):
        asyncio.run(_client(body).get_insight("bitcoin"))


@pytest.mark.parametrize("value", [True, "3.5", 0, -0.5, 10**400])
def test_invalid_anomaly_threshold_is_rejected(value) -> None:
    body = _body("insight_bitcoin_alpha.json")
    body["data"]["math_diagnostics"]["z_score_threshold"] = value

    with pytest.raises(UnexpectedResponse):
        asyncio.run(_client(body).get_insight("bitcoin"))


def test_a_valid_seal_does_not_make_a_different_asset_the_requested_one() -> None:
    body = _body("insight_bitcoin_alpha.json")

    with pytest.raises(UnexpectedResponse, match="requested coin"):
        asyncio.run(_client(body).get_insight("ethereum"))


def test_diagnostic_and_audit_override_flags_must_agree() -> None:
    body = _body("insight_bitcoin_alpha.json")
    body["data"]["math_diagnostics"]["sentiment_override"] = True

    with pytest.raises(UnexpectedResponse, match="flags disagree"):
        asyncio.run(_client(body).get_insight("bitcoin"))


@pytest.mark.parametrize("digest", ["0x1234", "0x" + "zz" * 32, "not a digest", " "])
def test_a_malformed_claimed_digest_cannot_downgrade_a_bad_seal_to_unchecked(digest) -> None:
    body = _body("insight_bitcoin_alpha.json")
    body["data"]["sentiment"] = "bullish"
    body["data"]["math_diagnostics"]["audit_trail"]["protocol_hash"] = digest

    with pytest.raises(UnexpectedResponse, match="SHA-256 digest"):
        asyncio.run(_client(body).get_insight("bitcoin"))


@pytest.mark.parametrize("omit_hash", [True, False])
def test_an_optional_missing_or_empty_digest_is_not_an_integrity_claim(omit_hash) -> None:
    body = _body("insight_bitcoin_alpha.json")
    trail = body["data"]["math_diagnostics"]["audit_trail"]
    trail.pop("protocol_hash")
    trail.pop("seal_type")
    if not omit_hash:
        trail["protocol_hash"] = ""

    assert asyncio.run(_client(body).get_insight("bitcoin")) == body["data"]


@pytest.mark.parametrize("field", ["filters_applied", "fields_overridden"])
def test_an_audit_string_is_not_a_list_of_filters_or_fields(field) -> None:
    body = _body("insight_bitcoin_alpha.json")
    body["data"]["math_diagnostics"]["audit_trail"][field] = "confidence"

    with pytest.raises(UnexpectedResponse):
        asyncio.run(_client(body).get_insight("bitcoin"))


def test_invalid_source_entries_are_not_treated_as_verified() -> None:
    body = _body("insight_bitcoin_alpha.json")
    body["data"]["analysis"]["sources_verified"] = ["trust me"]

    with pytest.raises(UnexpectedResponse):
        asyncio.run(_client(body).get_insight("bitcoin"))


@pytest.mark.parametrize(
    "raw",
    [
        '{"status":"success","data":{"math_diagnostics":{"z_score":NaN}}}',
        '{"status":"success","data":{"math_diagnostics":{"z_score":Infinity}}}',
        '{"status":"success","data":{"math_diagnostics":{"z_score":1e999}}}',
        '{"status":"success","data":{"sentiment":"bullish","sentiment":"bearish"}}',
        '{"status":"error","data":{"sentiment":"bullish"}}',
    ],
)
def test_nonfinite_ambiguous_or_unsuccessful_json_is_rejected(raw) -> None:
    with pytest.raises(UnexpectedResponse):
        asyncio.run(_client(raw=raw).get_insight("bitcoin"))


def test_missing_optional_fields_remain_missing() -> None:
    body = {"status": "success", "data": {"asset": {"id": "bitcoin"}}}

    assert asyncio.run(_client(body).get_insight("bitcoin")) == body["data"]


@pytest.mark.parametrize("row", [None, 42, "HOLD", []])
def test_scan_does_not_cast_primitive_rows_to_signals(row) -> None:
    body = {"status": "success", "data": {"results": [row]}}

    with pytest.raises(UnexpectedResponse):
        asyncio.run(_client(body).get_market_scan())


@pytest.mark.parametrize(
    ("field", "value"),
    [("evidence_weight", 1.01), ("evidence_weight", True), ("threshold_proximity", -1), ("current_price", -1)],
)
def test_scan_axes_and_prices_have_valid_ranges(field, value) -> None:
    body = _body("market_scan_openapi_example.json")
    body["data"]["results"][0][field] = value

    with pytest.raises(UnexpectedResponse):
        asyncio.run(_client(body).get_market_scan())


def test_null_scan_axes_are_preserved() -> None:
    body = _body("market_scan_openapi_example.json")
    body["data"]["results"][0]["threshold_proximity"] = None
    body["data"]["results"][0]["evidence_weight"] = None

    rows = asyncio.run(_client(body).get_market_scan())

    assert rows[0]["threshold_proximity"] is None
    assert rows[0]["evidence_weight"] is None


@pytest.mark.parametrize("field", ["requested", "available"])
def test_batch_counter_must_match_rows(field) -> None:
    body = _body("batch_btc_eth.json")
    body["data"][field] = 0

    with pytest.raises(UnexpectedResponse):
        asyncio.run(_client(body).get_batch_signals(["bitcoin", "ethereum"]))


def test_batch_response_must_belong_to_the_requested_assets() -> None:
    body = _body("batch_btc_eth.json")

    with pytest.raises(UnexpectedResponse, match="unrequested"):
        asyncio.run(_client(body).get_batch_signals(["bitcoin", "solana"]))


def test_duplicate_batch_asset_cannot_replace_a_missing_asset() -> None:
    body = _body("batch_btc_eth.json")
    body["data"]["results"][1]["asset"] = {"id": "bitcoin", "symbol": "btc"}

    with pytest.raises(UnexpectedResponse, match="duplicate"):
        asyncio.run(_client(body).get_batch_signals(["bitcoin", "ethereum"]))


@pytest.mark.parametrize("asset", [None, {}, {"symbol": "eth"}, {"id": None, "symbol": "eth"}])
def test_available_batch_signal_must_have_attributable_asset_identity(asset) -> None:
    row = {"available": True, "signal": "BUY", "sentiment": "bullish"}
    if asset is not None:
        row["asset"] = asset
    body = {"status": "success", "data": {"results": [row]}}

    with pytest.raises(UnexpectedResponse, match="asset.id"):
        asyncio.run(_client(body).get_batch_signals(["bitcoin"]))


def test_a_null_batch_identity_requires_explicit_unavailability() -> None:
    body = {"status": "success", "data": {"results": [{"asset": {"id": None, "symbol": "xyz"}}]}}

    with pytest.raises(UnexpectedResponse, match="asset.id"):
        asyncio.run(_client(body).get_batch_signals(["xyz"]))


@pytest.mark.parametrize("asset", [None, {"id": None, "symbol": "XYZ"}])
def test_a_genuinely_unavailable_unknown_symbol_needs_no_invented_asset_id(asset) -> None:
    row = {"available": False, "signal": None, "sentiment": None}
    if asset is not None:
        row["asset"] = asset
    body = {"status": "success", "data": {"requested": 1, "available": 0, "results": [row]}}

    assert asyncio.run(_client(body).get_batch_signals(["unknown-asset"])) == [row]


def test_known_and_unavailable_unknown_batch_rows_can_coexist() -> None:
    body = _body("batch_btc_eth.json")
    unknown = {"asset": {"id": None, "symbol": "XYZ"}, "available": False, "signal": None}
    body["data"]["results"][1] = unknown
    body["data"]["available"] = 1

    rows = asyncio.run(_client(body).get_batch_signals(["bitcoin", "unknown-asset"]))

    assert rows[0]["asset"]["id"] == "bitcoin"
    assert rows[1] == unknown


def test_unavailable_batch_asset_cannot_carry_a_buy_signal() -> None:
    body = {"status": "success", "data": {"results": [{"available": False, "signal": "BUY"}]}}

    with pytest.raises(UnexpectedResponse, match="unavailable"):
        asyncio.run(_client(body).get_batch_signals(["bitcoin"]))


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", False, None])
def test_bad_price_is_not_a_decimal_measurement(value) -> None:
    body = [{"id": "bitcoin", "current_price": value}]

    with pytest.raises(UnexpectedResponse):
        asyncio.run(_client(body).get_prices())


def test_price_precision_is_preserved_for_decimal_calculations() -> None:
    exact = "0.12345678901234567890123456789"

    rows = asyncio.run(_client([{"id": "bitcoin", "current_price": exact}]).get_prices())

    assert rows[0]["current_price"] == exact
    assert Decimal(rows[0]["current_price"]) == Decimal(exact)


@pytest.mark.parametrize(
    ("field", "value"),
    [("fear_greed_index", True), ("fear_greed_index", 101), ("btc_dominance", "101"), ("eth_dominance", "NaN")],
)
def test_market_summary_rejects_invalid_ranges_and_types(field, value) -> None:
    body = _body("market_summary.json")
    body[field] = value

    with pytest.raises(UnexpectedResponse):
        asyncio.run(_client(body).get_market_summary())
