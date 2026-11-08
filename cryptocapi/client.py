import json
import math
import os
import re
from decimal import Decimal, InvalidOperation
from typing import cast
from urllib.parse import quote

import httpx

from .models import InsightData, MarketSummary, PriceItem, ScanResult, SignalResult

_DEFAULT_BASE_URL = "https://api.cryptocapi.com/v1"
_TIMEOUT = 15.0

DEMO_API_KEY = "demo_btc_eth_public"


def resolve_api_key() -> str:
    """Return the API key to use, falling back to the public demo key.

    An *unset* CRYPTOCAPI_API_KEY means the user cloned and ran without copying
    .env, so we hand them the demo key and the Quick Start just works. An
    explicitly *empty* value is a deliberate "no key", which the API answers with
    the free Pulse view.
    """
    raw = os.getenv("CRYPTOCAPI_API_KEY")
    return DEMO_API_KEY if raw is None else raw


class DemoCoinRestricted(Exception):
    """Raised when the public demo key is used for a non-whitelisted coin.

    The demo key serves the full Alpha audit_trail for bitcoin & ethereum only;
    any other asset returns 403 with a DEMO_COIN_RESTRICTED code. We surface that
    as its own exception so the CLI can show a "get a free account" banner instead
    of silently falling back to the free Pulse view.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.user_message = message


class ProEngineRequired(Exception):
    """Raised when the Quant engines turn the key in use away.

    Each engine is sold separately, and the public demo key reaches only one of
    the two Quant routes: batch, for bitcoin and ethereum. market-scan stays
    closed to it, and to any key that never bought it, so the API answers 403
    with its own plain explanation. Raising that as its own exception lets the
    CLI show it next to the trial CTA, the way DemoCoinRestricted already does
    for insights, instead of leaking a raw httpx error (internal URL and a link
    to MDN's 403 page) at the exact moment the reader got curious about the paid
    engines.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.user_message = message


class ApiError(httpx.HTTPStatusError):
    """Raised for any other non-2xx answer: a rate limit, a validation error, an outage.

    These used to surface as httpx's own message, the internal URL plus a link to
    MDN's page for the status code, with the API's explanation thrown away. This
    carries the status and what the API said instead, validation details
    included. It is still an httpx.HTTPStatusError, so code that caught that
    keeps working.
    """

    def __init__(self, response: httpx.Response) -> None:
        self.status_code = response.status_code
        self.user_message = _api_error_message(response)
        super().__init__(self.user_message, request=response.request, response=response)


class UnexpectedResponse(Exception):
    """Raised when the API's envelope is not the shape models.py describes.

    The TypedDicts in models.py are a description of what CryptoCapi returns, and
    this is the only place that checks the description still holds. A client that
    declared InsightData and handed back whatever happened to arrive would be
    making precisely the kind of unverified claim this project exists to catch,
    only at the type level instead of in the prose.
    """


def _json_body(response: httpx.Response) -> object:
    """Return the response body as an object tree, or None if it is not JSON.

    `response.json()` is typed Any, and an Any that escapes this module reaches
    the callers' declared return types unchecked. It is pinned to `object` here so
    every read downstream has to narrow in the open.
    """
    try:
        payload: object = json.loads(
            response.content,
            parse_constant=_invalid_json_constant,
            object_pairs_hook=_unique_json_object,
        )
        _finite_json_numbers(payload)
    except ValueError:
        # A gateway or proxy answering with HTML, not our envelope.
        return None
    return payload


def _invalid_json_constant(value: str) -> object:
    raise ValueError(f"non-finite JSON number: {value}")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _finite_json_numbers(value: object) -> None:
    # 1e999 is valid JSON syntax, but the default float decoder makes it inf.
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("JSON number exceeds finite float range")
    if isinstance(value, dict):
        for child in value.values():
            _finite_json_numbers(child)
    elif isinstance(value, list):
        for child in value:
            _finite_json_numbers(child)


def _object(value: object, path: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise UnexpectedResponse(f"`{path}` must be an object")
    return cast(dict[str, object], value)


def _text_fields(
    data: dict[str, object], path: str, fields: tuple[str, ...], *, nullable: bool = False
) -> None:
    for name in fields:
        if name not in data or (nullable and data[name] is None):
            continue
        if not isinstance(data[name], str):
            raise UnexpectedResponse(f"`{path}.{name}` must be text")


def _number_fields(
    data: dict[str, object],
    path: str,
    fields: tuple[str, ...],
    *,
    nullable: bool = False,
    minimum: float | None = None,
    maximum: float | None = None,
) -> None:
    for name in fields:
        if name not in data or (nullable and data[name] is None):
            continue
        value = data[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise UnexpectedResponse(f"`{path}.{name}` must be a finite number")
        try:
            finite = math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            raise UnexpectedResponse(f"`{path}.{name}` must be a finite number")
        if (minimum is not None and value < minimum) or (
            maximum is not None and value > maximum
        ):
            raise UnexpectedResponse(f"`{path}.{name}` is outside its valid range")


def _bool_fields(data: dict[str, object], path: str, fields: tuple[str, ...]) -> None:
    for name in fields:
        if name in data and not isinstance(data[name], bool):
            raise UnexpectedResponse(f"`{path}.{name}` must be a boolean")


def _string_lists(data: dict[str, object], path: str, fields: tuple[str, ...]) -> None:
    for name in fields:
        if name in data:
            value = data[name]
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise UnexpectedResponse(f"`{path}.{name}` must be a list of text values")


def _confidence(value: object, path: str) -> None:
    confidence = _object(value, path)
    if "score" not in confidence or "label" not in confidence:
        raise UnexpectedResponse(f"`{path}` must include score and label")
    _number_fields(confidence, path, ("score",), minimum=0, maximum=1)
    _text_fields(confidence, path, ("label",))
    if confidence["label"] not in ("HIGH", "MEDIUM", "LOW"):
        raise UnexpectedResponse(f"`{path}.label` is not a known confidence label")


def _asset(value: object, path: str, *, nullable_id: bool = False) -> dict[str, object]:
    asset = _object(value, path)
    _text_fields(asset, path, ("symbol",))
    _text_fields(asset, path, ("id",), nullable=nullable_id)
    for name in ("id", "symbol"):
        if isinstance(asset.get(name), str) and not cast(str, asset[name]).strip():
            raise UnexpectedResponse(f"`{path}.{name}` must not be empty")
    return asset


def _validate_insight(data: dict[str, object], coin_id: str) -> None:
    path = "data"
    _text_fields(data, path, ("engine_used", "generated_at", "summary", "sentiment"))
    _bool_fields(data, path, ("statistical_anomaly_detected",))
    if "asset" in data:
        asset = _asset(data["asset"], "data.asset")
        if "id" in asset and cast(str, asset["id"]).casefold() != coin_id.casefold():
            raise UnexpectedResponse("`data.asset.id` does not match the requested coin")
    if "confidence" in data:
        _confidence(data["confidence"], "data.confidence")
    if "analysis" in data:
        analysis = _object(data["analysis"], "data.analysis")
        _text_fields(analysis, "data.analysis", ("detailed_report", "sources_window"))
        if "sources_verified" in analysis:
            sources = analysis["sources_verified"]
            if not isinstance(sources, list):
                raise UnexpectedResponse("`data.analysis.sources_verified` must be a list")
            for index, source in enumerate(sources):
                source_path = f"data.analysis.sources_verified[{index}]"
                _text_fields(_object(source, source_path), source_path, ("title", "url", "credibility"))
    if "math_diagnostics" not in data:
        return
    math_data = _object(data["math_diagnostics"], "data.math_diagnostics")
    math_path = "data.math_diagnostics"
    _number_fields(math_data, math_path, ("z_score",))
    _number_fields(math_data, math_path, ("z_score_threshold", "bollinger_bandwidth"), minimum=0)
    if math_data.get("z_score_threshold") == 0:
        raise UnexpectedResponse("`data.math_diagnostics.z_score_threshold` must be positive")
    _text_fields(math_data, math_path, ("market_regime", "data_quality"))
    _text_fields(math_data, math_path, ("anomaly_details",), nullable=True)
    _bool_fields(math_data, math_path, ("extreme_volatility_detected", "sentiment_override"))
    _string_lists(math_data, math_path, ("data_quality_reason",))
    if "regime_thresholds" in math_data:
        thresholds = _object(math_data["regime_thresholds"], f"{math_path}.regime_thresholds")
        _number_fields(
            thresholds, f"{math_path}.regime_thresholds",
            ("volatility_hard_limit", "z_score_anomaly_boundary", "daily_change_trend_boundary"),
            minimum=0,
        )
    if "audit_trail" in math_data:
        trail = _object(math_data["audit_trail"], f"{math_path}.audit_trail")
        _text_fields(
            trail, f"{math_path}.audit_trail",
            ("protocol_hash", "calculated_at", "seal_type", "algorithm_id", "engine_version"),
        )
        protocol_hash = trail.get("protocol_hash")
        if protocol_hash and re.fullmatch(r"0x[0-9a-f]{64}", cast(str, protocol_hash)) is None:
            raise UnexpectedResponse("`data.math_diagnostics.audit_trail.protocol_hash` is not a SHA-256 digest")
        _bool_fields(trail, f"{math_path}.audit_trail", ("sentiment_override",))
        _string_lists(trail, f"{math_path}.audit_trail", ("filters_applied", "fields_overridden"))
        if (
            "sentiment_override" in math_data and "sentiment_override" in trail
            and math_data["sentiment_override"] != trail["sentiment_override"]
        ):
            raise UnexpectedResponse("the diagnostic and audit sentiment_override flags disagree")


def _validate_quant_rows(rows: list[object], *, batch: bool) -> None:
    for index, row in enumerate(rows):
        path = f"data.results[{index}]"
        data = _object(row, path)
        if "asset" in data:
            _asset(data["asset"], f"{path}.asset", nullable_id=batch)
        _text_fields(
            data, path,
            ("signal", "sentiment", "market_regime", "risk_level", "trigger_condition", "summary"),
            nullable=True,
        )
        _text_fields(data, path, ("generated_at",), nullable=batch)
        _number_fields(data, path, ("z_score",), nullable=True)
        if "confidence" in data and (data["confidence"] is not None or not batch):
            _confidence(data["confidence"], f"{path}.confidence")
        if batch:
            _bool_fields(data, path, ("available",))
            asset = data.get("asset")
            asset_id = asset.get("id") if isinstance(asset, dict) else None
            if data.get("available") is not False and not isinstance(asset_id, str):
                raise UnexpectedResponse(f"`{path}.asset.id` is required unless the signal is unavailable")
            if data.get("available") is False:
                for field in (
                    "signal", "sentiment", "z_score", "market_regime", "confidence", "risk_level",
                    "trigger_condition", "summary", "generated_at",
                ):
                    if data.get(field) is not None:
                        raise UnexpectedResponse(f"`{path}.{field}` must be null for an unavailable signal")
        else:
            _number_fields(data, path, ("threshold_proximity", "current_price"), nullable=True, minimum=0)
            _number_fields(data, path, ("evidence_weight",), nullable=True, minimum=0, maximum=1)
            _number_fields(data, path, ("price_change_percentage_24h",), nullable=True)


def _decimal_fields(
    data: dict[str, object], path: str, fields: tuple[str, ...], *, minimum: int | None = None,
    maximum: int | None = None,
) -> None:
    # Keep the API's decimal strings intact; converting prices to binary floats
    # here would silently change precision before callers can use Decimal.
    for name in fields:
        if name not in data:
            continue
        value = data[name]
        if not isinstance(value, str):
            raise UnexpectedResponse(f"`{path}.{name}` must be a decimal string")
        try:
            number = Decimal(value)
        except InvalidOperation:
            raise UnexpectedResponse(f"`{path}.{name}` must be a finite decimal string") from None
        if not number.is_finite():
            raise UnexpectedResponse(f"`{path}.{name}` must be a finite decimal string")
        if (minimum is not None and number < minimum) or (maximum is not None and number > maximum):
            raise UnexpectedResponse(f"`{path}.{name}` is outside its valid range")


def _json_object(response: httpx.Response) -> dict[str, object] | None:
    """Return the response body as a JSON object, or None if it is not one."""
    payload = _json_body(response)
    if not isinstance(payload, dict):
        return None
    return cast(dict[str, object], payload)


def _envelope_data(response: httpx.Response) -> object:
    """Return the `data` of the API envelope, deliberately still unnarrowed.

    Handing back `object` rather than the target TypedDict forces each endpoint to
    say out loud what shape it expects, instead of an Any quietly becoming an
    InsightData nobody ever looked at.
    """
    payload = _json_object(response)
    if payload is None:
        raise UnexpectedResponse("the API returned a body that is not a JSON object")
    if "data" not in payload:
        raise UnexpectedResponse("the API response carries no `data` envelope")
    if payload.get("status") != "success":
        raise UnexpectedResponse("the API envelope does not report success")
    return payload["data"]


def _envelope_results(response: httpx.Response, expected: str) -> list[object]:
    """Return the rows of a Quant envelope, which sit one level below `data`.

    scan and batch do not hand back a bare list: `data` is an object carrying a
    count next to the rows, `{"strategy", "count", "results"}` for the scan and
    `{"requested", "available", "results"}` for the batch (OpenAPI document, and
    the live batch response captured in tests/fixtures/api). Reading `data`
    itself as the list is what made both commands fail on every success.
    """
    data = _envelope_data(response)
    if not isinstance(data, dict):
        raise UnexpectedResponse(f"`data` is not an object; expected {expected}")
    results: object = data.get("results")
    if not isinstance(results, list):
        raise UnexpectedResponse(f"`data.results` is not a list; expected {expected}")
    for name in ("count", "requested", "available"):
        if name not in data:
            continue
        count = data[name]
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise UnexpectedResponse(f"`data.{name}` must be a nonnegative integer")
        actual = (
            sum(isinstance(row, dict) and row.get("available") is True for row in results)
            if name == "available" else len(results)
        )
        if count != actual:
            raise UnexpectedResponse(f"`data.{name}` disagrees with the returned rows")
    return cast(list[object], results)


def _api_error_message(response: httpx.Response) -> str:
    """Say what the API said about a failure, and nothing httpx adds to it."""
    status = f"{response.status_code} {response.reason_phrase}".strip()
    payload = _json_object(response)
    message = payload.get("message") if payload else None
    if not isinstance(message, str) or not message:
        # A gateway or proxy page, not our envelope: the status is all there is.
        return f"CryptoCapi answered {status}"

    # A 400 says only "Validation failed" in `message`; what failed is in `errors`.
    details: list[str] = []
    errors = payload.get("errors") if payload else None
    if isinstance(errors, list):
        for item in errors:
            if not isinstance(item, dict) or not isinstance(item.get("message"), str):
                continue
            path = item.get("path")
            details.append(f"{path}: {item['message']}" if isinstance(path, str) else item["message"])
    suffix = f" ({'; '.join(details)})" if details else ""
    return f"CryptoCapi answered {status}: {message}{suffix}"


def _raise_for_status(response: httpx.Response) -> None:
    if not response.is_success:
        raise ApiError(response)


def _pro_plan_message(response: httpx.Response) -> str | None:
    """Return the API's own explanation when it rejects a Quant request."""
    if response.status_code not in (401, 403):
        return None
    payload = _json_object(response)
    if payload is None:
        return None
    message = payload.get("message")
    return message if isinstance(message, str) and message else None


_DEMO_RESTRICTED_FALLBACK = (
    "The public demo key only supports bitcoin and ethereum. "
    "Get a free 14-day trial at https://cryptocapi.com to analyze any asset."
)


def _demo_restriction_message(response: httpx.Response) -> str | None:
    """Return the human message if a 403 carries the DEMO_COIN_RESTRICTED code.

    The code sits flat in the body, next to `status` and `message`, on every
    route that enforces it (insights and batch alike). This used to look for it
    in a JSON document nested inside `message`, which no live response carries,
    so the restriction was never recognised: an insight silently fell back to
    the Pulse view and the restriction banner never showed.
    """
    if response.status_code != 403:
        return None
    payload = _json_object(response)
    if payload is None or payload.get("code") != "DEMO_COIN_RESTRICTED":
        return None
    # The code is what identifies the restriction; the prose is only shown. A
    # body that carries the code without words still has to read as one.
    message = payload.get("message")
    return message if isinstance(message, str) and message else _DEMO_RESTRICTED_FALLBACK


class CryptoCapiClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """`transport` swaps the network out, e.g. for an httpx.MockTransport in tests."""
        self._base_url = base_url.rstrip("/")
        self._headers: dict[str, str] = {}
        if api_key:
            self._headers["x-api-key"] = api_key
        self._transport = transport

    def _http(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=_TIMEOUT, transport=self._transport)

    async def get_insight(self, coin_id: str) -> InsightData | None:
        """GET /market/insights/:id, or None when the API has no analysis for the coin.

        None is the API's own `{"status":"success","data":null}`, which it sends
        for any coin no engine has analyzed yet, majors included, and for an id
        it does not know. It is an answer, not an error, and the caller must not
        fill the gap: that is why it comes back as None and not as an exception.

        Requests the full Alpha payload (with audit_trail) first. The API rejects
        Alpha with 401/403 when the key is missing, free or expired; in that case
        we transparently retry the public Pulse view so the caller still gets an
        insight — just without the audit_trail. The renderer detects the missing
        audit_trail and shows the upgrade banner, which is the whole free-tier hook.

        One 403 is NOT a free-tier signal: the public demo key returns
        DEMO_COIN_RESTRICTED for coins outside its bitcoin/ethereum whitelist. That
        is raised as DemoCoinRestricted so the CLI can prompt the user to register
        instead of misleadingly showing the generic Pulse banner.
        """
        url = f"{self._base_url}/market/insights/{quote(coin_id, safe='')}"
        async with self._http() as client:
            r = await client.get(url, headers=self._headers, params={"view": "alpha"})
            if r.status_code in (401, 403):
                restricted = _demo_restriction_message(r)
                if restricted:
                    raise DemoCoinRestricted(restricted)
                r = await client.get(url, headers=self._headers, params={"view": "pulse"})
            _raise_for_status(r)
            data = _envelope_data(r)
            if data is None:
                return None
            if not isinstance(data, dict):
                raise UnexpectedResponse("`data` is not an object; expected one insight")
            _validate_insight(cast(dict[str, object], data), coin_id)
            return cast(InsightData, data)

    async def get_market_scan(
        self, strategy: str = "balanced", limit: int = 10
    ) -> list[ScanResult]:
        """GET /quant/market-scan — ranked list of assets by signal strength.

        Runs on the Market Scan engine, which the public demo key does not
        include: a 401/403 here is the plan gate, not a bug, so it is raised as
        ProEngineRequired.
        """
        async with self._http() as client:
            r = await client.get(
                f"{self._base_url}/quant/market-scan",
                headers=self._headers,
                params={"strategy": strategy, "limit": limit},
            )
            message = _pro_plan_message(r)
            if message:
                raise ProEngineRequired(message)
            _raise_for_status(r)
            rows = _envelope_results(r, "ranked assets")
            _validate_quant_rows(rows, batch=False)
            return cast(list[ScanResult], rows)

    async def get_batch_signals(self, symbols: list[str]) -> list[SignalResult]:
        """POST /quant/batch — signals for multiple assets in one request.

        The demo key reaches this route for bitcoin and ethereum, and the API
        rejects a batch that includes any other coin whole, with the same
        DEMO_COIN_RESTRICTED as an insight: that is raised as DemoCoinRestricted,
        and checked first, because it is a 403 too. Any other 401/403 is the plan
        gate, which the caller should surface as an offer, not an error.
        """
        async with self._http() as client:
            r = await client.post(
                f"{self._base_url}/quant/batch",
                headers=self._headers,
                json={"symbols": symbols},
            )
            restricted = _demo_restriction_message(r)
            if restricted:
                raise DemoCoinRestricted(restricted)
            message = _pro_plan_message(r)
            if message:
                raise ProEngineRequired(message)
            _raise_for_status(r)
            rows = _envelope_results(r, "one signal per symbol")
            _validate_quant_rows(rows, batch=True)
            expected = [symbol.casefold() for symbol in symbols]
            if len(rows) != len(expected):
                raise UnexpectedResponse("the batch response does not contain one row per requested symbol")
            for row in rows:
                data = cast(dict[str, object], row)
                asset = data.get("asset")
                if isinstance(asset, dict) and isinstance(asset.get("id"), str):
                    asset_id = asset["id"].casefold()
                    if asset_id not in expected:
                        raise UnexpectedResponse("the batch response contains an unrequested or duplicate asset")
                    expected.remove(asset_id)
            return cast(list[SignalResult], rows)

    async def get_prices(self, limit: int = 20) -> list[PriceItem]:
        """GET /market/prices/latest — public endpoint, no key required.

        Unlike the engines, this route has no envelope: the body is the array.
        """
        async with self._http() as client:
            r = await client.get(
                f"{self._base_url}/market/prices/latest",
                params={"limit": limit},
            )
            _raise_for_status(r)
            payload = _json_body(r)
            if not isinstance(payload, list):
                raise UnexpectedResponse("the prices body is not a JSON array")
            for index, item in enumerate(payload):
                path = f"prices[{index}]"
                data = _object(item, path)
                _text_fields(data, path, ("id", "symbol", "name"))
                _decimal_fields(data, path, ("current_price", "market_cap", "total_volume"), minimum=0)
                _decimal_fields(data, path, ("price_change_percentage_24h",))
                if "market_cap_rank" in data and (
                    isinstance(data["market_cap_rank"], bool)
                    or not isinstance(data["market_cap_rank"], int)
                    or data["market_cap_rank"] < 1
                ):
                    raise UnexpectedResponse(f"`{path}.market_cap_rank` must be a positive integer")
            return cast(list[PriceItem], payload)

    async def get_market_summary(self) -> MarketSummary:
        """GET /market/market-summary — public endpoint, no key required.

        No envelope here either: the body is the summary object itself.
        """
        async with self._http() as client:
            r = await client.get(f"{self._base_url}/market/market-summary")
            _raise_for_status(r)
            payload = _json_object(r)
            if payload is None:
                raise UnexpectedResponse("the market summary body is not a JSON object")
            if payload.get("status") == "error":
                raise UnexpectedResponse("the market summary reports an error")
            _decimal_fields(payload, "summary", ("total_market_cap", "total_volume_24h"), minimum=0)
            _decimal_fields(payload, "summary", ("btc_dominance", "eth_dominance"), minimum=0, maximum=100)
            _decimal_fields(payload, "summary", ("market_cap_change_percentage_24h_usd",))
            _text_fields(payload, "summary", ("fear_greed_value", "last_updated"))
            _number_fields(payload, "summary", ("fear_greed_index",), minimum=0, maximum=100)
            if "fear_greed_index" in payload and not isinstance(payload["fear_greed_index"], int):
                raise UnexpectedResponse("`summary.fear_greed_index` must be an integer")
            return cast(MarketSummary, payload)
