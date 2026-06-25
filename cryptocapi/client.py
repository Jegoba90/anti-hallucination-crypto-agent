import httpx

from .models import InsightData, MarketSummary, PriceItem, ScanResult, SignalResult

_DEFAULT_BASE_URL = "https://api.cryptocapi.com/v1"


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
        """
        url = f"{self._base_url}/market/insights/{coin_id}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers=self._headers, params={"view": "alpha"})
            if r.status_code in (401, 403):
                r = await client.get(url, headers=self._headers, params={"view": "pulse"})
            r.raise_for_status()
            return r.json()["data"]

    async def get_market_scan(
        self, strategy: str = "balanced", limit: int = 10
    ) -> list[ScanResult]:
        """GET /quant/market-scan — ranked list of assets by signal strength."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                f"{self._base_url}/quant/market-scan",
                headers=self._headers,
                params={"strategy": strategy, "limit": limit},
            )
            r.raise_for_status()
            return r.json()["data"]

    async def get_batch_signals(self, symbols: list[str]) -> list[SignalResult]:
        """POST /quant/batch — signals for multiple assets in one request."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                f"{self._base_url}/quant/batch",
                headers=self._headers,
                json={"symbols": symbols},
            )
            r.raise_for_status()
            return r.json()["data"]

    async def get_prices(self, limit: int = 20) -> list[PriceItem]:
        """GET /market/prices/latest — public endpoint, no key required."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                f"{self._base_url}/market/prices/latest",
                params={"limit": limit},
            )
            r.raise_for_status()
            return r.json()["data"]

    async def get_market_summary(self) -> MarketSummary:
        """GET /market/market-summary — public endpoint, no key required."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(f"{self._base_url}/market/market-summary")
            r.raise_for_status()
            return r.json()["data"]
