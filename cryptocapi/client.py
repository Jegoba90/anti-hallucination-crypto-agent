import json
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

    market-scan and batch run on Quant Plus, which the public demo key does not
    cover, so the API answers 403 with its own plain explanation. Raising that as
    its own exception lets the CLI show it next to the trial CTA, the way
    DemoCoinRestricted already does for insights, instead of leaking a raw httpx
    error (internal URL and a link to MDN's 403 page) at the exact moment the
    reader got curious about the paid engines.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.user_message = message


class UnexpectedResponse(Exception):
    """Raised when the API's envelope is not the shape models.py describes.

    The TypedDicts in models.py are a description of what CryptoCapi returns, and
    this is the only place that checks the description still holds. A client that
    declared InsightData and handed back whatever happened to arrive would be
    making precisely the kind of unverified claim this project exists to catch,
    only at the type level instead of in the prose.
    """


def _json_object(response: httpx.Response) -> dict[str, object] | None:
    """Return the response body as an object tree, or None if it is not one.

    `response.json()` is typed Any, and an Any that escapes this module reaches
    the callers' declared return types unchecked. It is pinned to `object` here so
    every read downstream has to narrow in the open.
    """
    try:
        payload: object = response.json()
    except ValueError:
        # A gateway or proxy answering with HTML, not our envelope.
        return None
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


def _pro_plan_message(response: httpx.Response) -> str | None:
    """Return the API's own explanation when it rejects a Quant request."""
    if response.status_code not in (401, 403):
        return None
    payload = _json_object(response)
    if payload is None:
        return None
    message = payload.get("message")
    return message if isinstance(message, str) and message else None


def _demo_restriction_message(response: httpx.Response) -> str | None:
    """Return the human message if a 403 carries the DEMO_COIN_RESTRICTED code."""
    if response.status_code != 403:
        return None
    payload = _json_object(response)
    if payload is None:
        return None

    # This endpoint nests a JSON document inside `message`, unlike the Quant ones.
    raw = payload.get("message")
    if not isinstance(raw, str):
        return None
    try:
        inner: object = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(inner, dict):
        return None
    if inner.get("code") != "DEMO_COIN_RESTRICTED":
        return None
    message: object = inner.get("message")
    return message if isinstance(message, str) else None


class CryptoCapiClient:
    def __init__(self, api_key: str, base_url: str = _DEFAULT_BASE_URL) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers: dict[str, str] = {}
        if api_key:
            self._headers["x-api-key"] = api_key

    async def get_insight(self, coin_id: str) -> InsightData:
        """GET /market/insights/:id.

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
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(url, headers=self._headers, params={"view": "alpha"})
            if r.status_code in (401, 403):
                restricted = _demo_restriction_message(r)
                if restricted:
                    raise DemoCoinRestricted(restricted)
                r = await client.get(url, headers=self._headers, params={"view": "pulse"})
            r.raise_for_status()
            data = _envelope_data(r)
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

        Runs on Quant Plus, which the public demo key does not cover: a 401/403
        here is the plan gate, not a bug, so it is raised as ProEngineRequired.
        """
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(
                f"{self._base_url}/quant/market-scan",
                headers=self._headers,
                params={"strategy": strategy, "limit": limit},
            )
            message = _pro_plan_message(r)
            if message:
                raise ProEngineRequired(message)
            r.raise_for_status()
            data = _envelope_data(r)
            if not isinstance(data, list):
                raise UnexpectedResponse("`data` is not a list; expected ranked assets")
            return cast(list[ScanResult], data)

    async def get_batch_signals(self, symbols: list[str]) -> list[SignalResult]:
        """POST /quant/batch — signals for multiple assets in one request.

        Same plan gate as get_market_scan: 401/403 means the key does not reach
        Quant Plus, which the caller should surface as an offer, not an error.
        """
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.post(
                f"{self._base_url}/quant/batch",
                headers=self._headers,
                json={"symbols": symbols},
            )
            message = _pro_plan_message(r)
            if message:
                raise ProEngineRequired(message)
            r.raise_for_status()
            data = _envelope_data(r)
            if not isinstance(data, list):
                raise UnexpectedResponse("`data` is not a list; expected one signal per symbol")
            return cast(list[SignalResult], data)

    async def get_prices(self, limit: int = 20) -> list[PriceItem]:
        """GET /market/prices/latest — public endpoint, no key required."""
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(
                f"{self._base_url}/market/prices/latest",
                params={"limit": limit},
            )
            r.raise_for_status()
            data = _envelope_data(r)
            if not isinstance(data, list):
                raise UnexpectedResponse("`data` is not a list; expected prices")
            return cast(list[PriceItem], data)

    async def get_market_summary(self) -> MarketSummary:
        """GET /market/market-summary — public endpoint, no key required."""
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(f"{self._base_url}/market/market-summary")
            r.raise_for_status()
            data = _envelope_data(r)
            if not isinstance(data, dict):
                raise UnexpectedResponse("`data` is not an object; expected a market summary")
            return cast(MarketSummary, data)
