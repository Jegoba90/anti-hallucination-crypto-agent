from typing import Optional, TypedDict


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


class MathDiagnostics(TypedDict, total=False):
    z_score: float
    z_score_threshold: float
    bollinger_bandwidth: float
    market_regime: str
    extreme_volatility_detected: bool
    data_quality: str  # OPTIMAL | PARTIAL | INSUFFICIENT
    data_quality_reason: list[str]
    sentiment_override: bool
    anomaly_details: Optional[str]
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


class ScanResult(TypedDict, total=False):
    id: str
    name: str
    symbol: str
    final_signal: str  # BUY | SELL | NEUTRAL
    final_score: int
    market_regime: str
    confidence: Confidence


class SignalResult(TypedDict, total=False):
    id: str
    name: str
    symbol: str
    sentiment: str
    market_regime: str
    confidence: Confidence
    summary: str


class PriceItem(TypedDict, total=False):
    id: str
    name: str
    symbol: str
    current_price: float
    price_change_percentage_24h: float
    market_cap: float


class MarketSummary(TypedDict, total=False):
    total_market_cap: float
    btc_dominance: float
    fear_greed_value: int
    fear_greed_label: str
    market_cap_change_percentage_24h: float
