from typing import TypedDict


class Asset(TypedDict, total=False):
    id: str
    symbol: str


class AuditTrail(TypedDict, total=False):
    protocol_hash: str
    calculated_at: str
    seal_type: str  # process_seal | output_seal | reproducible
    algorithm_id: str
    engine_version: str
    filters_applied: list[str]
    fields_overridden: list[str]
    sentiment_override: bool


class Confidence(TypedDict):
    score: float
    label: str  # HIGH | MEDIUM | LOW


class SourceEntry(TypedDict, total=False):
    title: str
    url: str
    credibility: str  # Tier 1 | Tier 2 | Tier 3


class RegimeThresholds(TypedDict, total=False):
    volatility_hard_limit: float
    z_score_anomaly_boundary: float
    daily_change_trend_boundary: float


class MathDiagnostics(TypedDict, total=False):
    z_score: float
    z_score_threshold: float  # dynamic, computed by the engine per response
    bollinger_bandwidth: float
    market_regime: str
    extreme_volatility_detected: bool
    data_quality: str  # OPTIMAL | PARTIAL | INSUFFICIENT
    data_quality_reason: list[str]
    sentiment_override: bool
    anomaly_details: str | None
    regime_thresholds: RegimeThresholds
    audit_trail: AuditTrail


class Analysis(TypedDict, total=False):
    detailed_report: str
    sources_verified: list[SourceEntry]
    sources_window: str


class InsightData(TypedDict, total=False):
    """Alpha-view payload returned by GET /market/insights/:id (?view=alpha).

    Note the nesting: identity lives under `asset`, the regime and the seal
    live under `math_diagnostics`, and the narrative lives under `analysis`.
    """

    engine_used: str  # radar | quant_plus
    asset: Asset
    summary: str
    sentiment: str  # bullish | bearish | neutral
    statistical_anomaly_detected: bool
    confidence: Confidence
    math_diagnostics: MathDiagnostics
    analysis: Analysis


class QuantAsset(TypedDict, total=False):
    # Nullable in the batch schema: a symbol the engine does not track.
    id: str | None
    symbol: str  # the coin's ticker, lowercase ("btc"), not a trading pair


class ScanResult(TypedDict, total=False):
    """One row of GET /quant/market-scan (OpenAPI: QuantScanItem).

    The ranking runs on two comparable axes, both shipped so the order can be
    reproduced; a raw `z_score` is NOT comparable across assets. An asset with
    no threshold or sample persisted gets null on that axis, never a default.
    """

    asset: QuantAsset
    signal: str | None  # STRONG_BUY | BUY | BUY_WATCH | HOLD | SELL_WATCH | SELL | STRONG_SELL | ALERT
    sentiment: str | None
    z_score: float | None
    market_regime: str | None
    threshold_proximity: float | None  # |z_score| over the asset's own threshold; 1.0 = firing
    evidence_weight: float | None  # min(data_points_analyzed / 50, 1.0)
    confidence: Confidence
    risk_level: str | None  # LOW | MEDIUM | HIGH | CRITICAL
    trigger_condition: str | None
    summary: str | None
    current_price: float | None
    price_change_percentage_24h: float | None
    generated_at: str


class SignalResult(TypedDict, total=False):
    """One row of POST /quant/batch (OpenAPI: QuantBatchItem).

    `available` is false for a symbol with no pre-computed signal, and every
    signal field of that row comes back null.
    """

    asset: QuantAsset
    available: bool
    signal: str | None
    sentiment: str | None
    z_score: float | None
    market_regime: str | None
    confidence: Confidence | None
    risk_level: str | None
    trigger_condition: str | None
    summary: str | None
    generated_at: str | None


class PriceItem(TypedDict, total=False):
    """One row of GET /market/prices/latest (OpenAPI: AssetDetail).

    The OpenAPI document declares the money fields as numbers, but the live
    endpoint sends them as decimal strings ("81704", "-0.80428"). They are typed
    as what actually arrives: convert with float() or Decimal before any math.
    """

    id: str
    symbol: str
    name: str
    current_price: str
    market_cap: str
    market_cap_rank: int
    price_change_percentage_24h: str
    total_volume: str


class MarketSummary(TypedDict, total=False):
    """GET /market/market-summary. Same decimal-string caveat as PriceItem.

    The Fear & Greed pair reads backwards at first sight: `fear_greed_index` is
    the 0-100 number and `fear_greed_value` is its label ("Greed").
    """

    total_market_cap: str
    total_volume_24h: str
    btc_dominance: str
    eth_dominance: str
    market_cap_change_percentage_24h_usd: str
    fear_greed_index: int
    fear_greed_value: str
    last_updated: str
