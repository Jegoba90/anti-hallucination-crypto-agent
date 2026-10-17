COLORS: dict[str, str] = {
    "header": "bold white",
    "coin_name": "bold cyan",
    "sentiment_bullish": "bold green",
    "sentiment_bearish": "bold red",
    "sentiment_neutral": "bold yellow",
    "regime": "blue",
    "hash": "dim cyan",
    "filter_fired": "yellow",
    "field_overridden": "cyan",
    "seal_ok": "bold green",
    "seal_bad": "bold red",
    "divider": "dim white",
    "warning": "bold yellow",
    "muted": "dim",
    "pro_banner": "bold green",
    "free_banner": "bold yellow",
}

SENTIMENT_ICONS: dict[str, str] = {
    "bullish": "📈",
    "bearish": "📉",
    "neutral": "➡️ ",
    "very_bullish": "🚀",
    "very_bearish": "💥",
}

REGIME_ICONS: dict[str, str] = {
    "BULLISH_TREND": "📈",
    "BEARISH_TREND": "📉",
    "RANGING_CHOP": "↔️ ",
    "EXTREME_VOLATILITY": "⚡",
    "UNUSUAL_VOLATILITY": "🌊",
}

CONFIDENCE_COLORS: dict[str, str] = {
    "HIGH": "green",
    "MEDIUM": "yellow",
    "LOW": "red",
}

CREDIBILITY_COLORS: dict[str, str] = {
    "Tier 1": "green",
    "Tier 2": "yellow",
    "Tier 3": "red",
}

# The Quant Plus signal enum, as the OpenAPI document lists it.
SIGNAL_COLORS: dict[str, str] = {
    "STRONG_BUY": "bold green",
    "BUY": "green",
    "BUY_WATCH": "cyan",
    "HOLD": "yellow",
    "SELL_WATCH": "magenta",
    "SELL": "red",
    "STRONG_SELL": "bold red",
    "ALERT": "bold red",
}
