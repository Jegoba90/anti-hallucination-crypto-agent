from datetime import datetime, timezone

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich import box

from cryptocapi.audit import AuditSummary, parse_audit_trail
from cryptocapi.models import InsightData, ScanResult, SignalResult
from .themes import (
    COLORS,
    CONFIDENCE_COLORS,
    REGIME_ICONS,
    SENTIMENT_ICONS,
    SIGNAL_COLORS,
)

console = Console()

_DIVIDER = "─" * 55


def _sentiment_color(sentiment: str) -> str:
    if "bullish" in sentiment:
        return COLORS["sentiment_bullish"]
    if "bearish" in sentiment:
        return COLORS["sentiment_bearish"]
    return COLORS["sentiment_neutral"]


def _now_utc() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def render_insight(data: InsightData, coin_id: str) -> None:
    asset = data.get("asset", {})
    name = asset.get("id", coin_id).capitalize()
    symbol = asset.get("symbol", "").upper()
    sentiment = data.get("sentiment", "neutral")
    math = data.get("math_diagnostics")
    regime = (math or {}).get("market_regime", "—")
    summary = data.get("summary", "")
    analysis = data.get("analysis", {})
    report = (analysis or {}).get("detailed_report", "")
    is_alert = (math or {}).get("extreme_volatility_detected", False)
    confidence = data.get("confidence")

    # ── Header ──────────────────────────────────────────────
    header = Text()
    header.append(f"  CRYPTOCAPI RADAR — ", style=COLORS["header"])
    header.append(f"{name} ({symbol})", style=COLORS["coin_name"])
    header.append(f"\n  {_now_utc()}", style=COLORS["muted"])

    console.print()
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print(header)
    console.print(_DIVIDER, style=COLORS["divider"])

    # ── Metrics ──────────────────────────────────────────────
    regime_icon = REGIME_ICONS.get(regime, "📊")
    sentiment_icon = SENTIMENT_ICONS.get(sentiment, "➡️ ")
    s_color = _sentiment_color(sentiment)

    console.print()
    console.print(f"  {regime_icon} MARKET REGIME:   [{COLORS['regime']}]{regime}[/]")
    console.print(f"  {sentiment_icon} SENTIMENT:       [{s_color}]{sentiment}[/]")

    if confidence:
        score = confidence.get("score", 0.0)
        label = confidence.get("label", "—")
        c_color = CONFIDENCE_COLORS.get(label, "white")
        console.print(f"  🎯 CONFIDENCE:      [{c_color}]{label} ({score:.2f})[/]")

    if math:
        z = math.get("z_score")
        if z is not None:
            # The engine already ships the verdict, computed against its dynamic
            # z_score_threshold. The display must never re-derive it.
            anomaly = (
                "⚠️  ANOMALY DETECTED"
                if data.get("statistical_anomaly_detected", False)
                else "no anomaly"
            )
            console.print(f"  🔺 Z-SCORE:         [{COLORS['muted']}]{z:.3f} ({anomaly})[/]")

    if is_alert:
        console.print(f"\n  [bold red]⚡ VOLATILITY ALERT[/bold red]")

    # ── Summary / Report ─────────────────────────────────────
    if report:
        console.print(f"\n  [bold]ANALYSIS:[/bold]")
        for line in report.strip().split("\n"):
            console.print(f"   {line}")
    elif summary:
        console.print(f"\n  [bold]SUMMARY:[/bold]")
        console.print(f"   {summary}")

    # ── Audit Trail (PRO) or Free banner ─────────────────────
    audit_trail = math.get("audit_trail") if math else None
    audit = parse_audit_trail(audit_trail)  # type: ignore[arg-type]

    console.print()
    console.print(_DIVIDER, style=COLORS["divider"])

    if not audit.is_pro:
        _render_pulse_view_banner()
        return

    _render_audit(audit)


def _render_audit(audit: AuditSummary) -> None:
    console.print(f"  🛡️  [bold]ANTI-HALLUCINATION AUDIT TRAIL[/bold]")
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print()
    console.print(f"  Pipeline:  [{COLORS['muted']}]{audit.algorithm_id}[/]")
    console.print(f"  Version:   [{COLORS['muted']}]{audit.engine_version}[/]")
    console.print(f"  Seal type: [{COLORS['muted']}]{audit.seal_type}[/]")
    console.print(f"             [{COLORS['muted']}]{audit.seal_explanation}[/]")

    console.print()
    if audit.filters:
        console.print(f"  Filters fired ({len(audit.filters)}):")
        for name, explanation in audit.filters:
            console.print(
                f"    ✂️  [{COLORS['filter_fired']}][{name}][/]"
                f"  [{COLORS['muted']}]— {explanation}[/]"
            )
    else:
        console.print(f"  [{COLORS['muted']}]No filters fired — LLM output was consistent with math[/]")

    if audit.fields_overridden:
        console.print()
        console.print(f"  Fields overridden by Python ({len(audit.fields_overridden)}):")
        for field_name in audit.fields_overridden:
            console.print(f"    🔒  [{COLORS['field_overridden']}]{field_name}[/]")

    if audit.sentiment_override:
        console.print(f"\n  [{COLORS['warning']}]⚠  Sentiment was overridden by Z-Score rule[/]")

    if audit.protocol_hash:
        console.print()
        console.print("  Protocol hash (SHA-256):")
        console.print(f"    [{COLORS['hash']}]{audit.protocol_hash}[/]")

    console.print()
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print(f"  [{COLORS['seal_ok']}]✅ Math Override Certified (CTC-2026)[/]")
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print()


def render_demo_restricted(message: str) -> None:
    console.print()
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print(f"  🔒  [{COLORS['free_banner']}]DEMO KEY — bitcoin & ethereum only[/]")
    console.print()
    console.print(f"  [{COLORS['muted']}]{message}[/]")
    console.print()
    console.print(f"  [{COLORS['pro_banner']}]→ Free 14-day trial: https://cryptocapi.com[/]")
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print()


def _render_pulse_view_banner() -> None:
    console.print(f"  [{COLORS['free_banner']}]⚠  PULSE VIEW (free / no key)[/]")
    console.print()
    console.print(f"  [{COLORS['muted']}]audit_trail not available on the free tier.[/]")
    console.print(f"  [{COLORS['muted']}]Upgrade to PRO to see the anti-hallucination[/]")
    console.print(f"  [{COLORS['muted']}]proof for every insight.[/]")
    console.print()
    console.print(f"  [{COLORS['pro_banner']}]→ Free 14-day trial: https://cryptocapi.com[/]")
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print()


def render_scan(results: list[ScanResult], strategy: str) -> None:
    console.print()
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print(f"  📡 MARKET SCAN — strategy: [{COLORS['coin_name']}]{strategy}[/]")
    console.print(f"  [{COLORS['muted']}]Engine: Quant Plus — 100% Python, zero LLM, zero hallucination risk[/]")
    console.print(f"  {_now_utc()}", style=COLORS["muted"])
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print()

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold white")
    table.add_column("#", style="dim", width=4)
    table.add_column("Asset", style="cyan", min_width=12)
    table.add_column("Signal", min_width=8)
    table.add_column("Score", justify="right", min_width=7)
    table.add_column("Regime", min_width=18)
    table.add_column("Confidence", min_width=10)

    for i, r in enumerate(results, 1):
        signal = r.get("final_signal", "—")
        score = r.get("final_score", 0)
        regime = r.get("market_regime", "—")
        confidence = r.get("confidence", {})
        label = confidence.get("label", "—") if confidence else "—"
        c_color = CONFIDENCE_COLORS.get(label, "white")
        s_color = SIGNAL_COLORS.get(signal, "white")

        table.add_row(
            str(i),
            f"{r.get('name', r.get('id', '—'))} ({r.get('symbol', '').upper()})",
            f"[{s_color}]{signal}[/]",
            f"[{s_color}]{score}[/]",
            regime,
            f"[{c_color}]{label}[/]",
        )

    console.print(table)
    console.print()


def render_batch(results: list[SignalResult]) -> None:
    console.print()
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print(f"  📦 BATCH ANALYSIS — {len(results)} assets")
    console.print(f"  [{COLORS['muted']}]Engine: Quant Plus — 100% Python, zero LLM, zero hallucination risk[/]")
    console.print(f"  {_now_utc()}", style=COLORS["muted"])
    console.print(_DIVIDER, style=COLORS["divider"])

    for r in results:
        name = r.get("name", r.get("id", "—"))
        symbol = r.get("symbol", "").upper()
        sentiment = r.get("sentiment", "neutral")
        regime = r.get("market_regime", "—")
        confidence = r.get("confidence", {})
        label = confidence.get("label", "—") if confidence else "—"
        score = confidence.get("score", 0.0) if confidence else 0.0
        summary = r.get("summary", "")
        s_color = _sentiment_color(sentiment)
        c_color = CONFIDENCE_COLORS.get(label, "white")
        sentiment_icon = SENTIMENT_ICONS.get(sentiment, "➡️ ")

        console.print()
        console.print(
            f"  [{COLORS['coin_name']}]{name} ({symbol})[/]  "
            f"{sentiment_icon} [{s_color}]{sentiment}[/]  "
            f"[{c_color}]{label} ({score:.2f})[/]  "
            f"[{COLORS['regime']}]{regime}[/]"
        )
        if summary:
            console.print(f"  [{COLORS['muted']}]{summary}[/]")

    console.print()
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print()
