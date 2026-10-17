import os
from typing import cast

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
        payload: object = response.json()
    except ValueError:
        # A gateway or proxy answering with HTML, not our envelope.
        return None
    return payload


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
        url = f"{self._base_url}/market/insights/{coin_id}"
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
            # Every field of InsightData is optional (total=False) and every reader
            # goes through .get() with a fallback, so an object is the whole shape
            # promise there is to keep here.
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
            return cast(MarketSummary, payload)
