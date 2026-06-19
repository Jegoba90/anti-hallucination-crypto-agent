from typing import TypedDict


class AuditTrail(TypedDict, total=False):
    protocol_hash: str
    calculated_at: str
    seal_type: str  # process_seal | output_seal | reproducible
    algorithm_id: str
    engine_version: str
    filters_applied: list[str]
    fields_overridden: list[str]
    z_score: float
    market_regime: str
    sentiment: str
    sentiment_override: bool


class Confidence(TypedDict):
    score: float
    label: str  # HIGH | MEDIUM | LOW


class Analysis(TypedDict, total=False):
    confidence: str
    sentiment_score: float
    sources_window: str


class MathDiagnostics(TypedDict, total=False):
    z_score: float
    bollinger_bandwidth: float
    data_quality: str  # OPTIMAL | PARTIAL | INSUFFICIENT
    audit_trail: AuditTrail


class SourceEntry(TypedDict, total=False):
    title: str
    url: str
    credibility: str  # Tier 1 | Tier 2 | Tier 3


class InsightData(TypedDict, total=False):
    id: str
    name: str
    symbol: str
    sentiment: str  # bullish | bearish | neutral | very_bullish | very_bearish
    market_regime: str
    confidence: Confidence
    summary: str
    detailed_report: str
    is_volatility_alert: bool
    sources_verified: list[SourceEntry]
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
