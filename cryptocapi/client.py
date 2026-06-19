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
        """GET /market/insights/:id — returns full Alpha payload with audit_trail on PRO keys."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                f"{self._base_url}/market/insights/{coin_id}",
                headers=self._headers,
                params={"view": "alpha"},
            )
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
