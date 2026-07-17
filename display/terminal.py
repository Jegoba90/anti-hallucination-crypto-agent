import sys
from datetime import datetime, timezone

from rich.console import Console
from rich.markup import escape
from rich.table import Table
from rich.text import Text
from rich import box

from cryptocapi.audit import AuditSummary, explain_field, parse_audit_trail
from cryptocapi.models import Analysis, InsightData, ScanResult, SignalResult
from .themes import (
    COLORS,
    CONFIDENCE_COLORS,
    CREDIBILITY_COLORS,
    REGIME_ICONS,
    SENTIMENT_ICONS,
    SIGNAL_COLORS,
)


def _force_utf8_output() -> None:
    """Make stdout able to carry the box drawing characters and emoji we print.

    Every render starts with a 55-character `─` divider, so on a stdout that is
    not UTF-8 (a Windows console under cp1252, or any redirected stream) the very
    first line raises UnicodeEncodeError and `coin bitcoin` answers with a
    traceback instead of the product. Repairing the stream here, where the output
    is owned, means the CLI and every example inherit it and the reader never has
    to export PYTHONIOENCODING to see a Quick Start that claims to just work.

    `errors="replace"` is the floor: a terminal that still cannot represent a
    glyph shows a placeholder rather than killing the run.
    """
    for stream in (sys.stdout, sys.stderr):
        # Absent under pytest's capture and any StringIO: nothing to repair there.
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass


# Runs before Console() so Rich reads the repaired encoding, not the original.
_force_utf8_output()

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
        console.print("\n  [bold red]⚡ VOLATILITY ALERT[/bold red]")

    # ── Summary / Report ─────────────────────────────────────
    if report:
        console.print("\n  [bold]ANALYSIS:[/bold]")
        for line in report.strip().split("\n"):
            console.print(f"   {line}")
    elif summary:
        console.print("\n  [bold]SUMMARY:[/bold]")
        console.print(f"   {summary}")

    _render_sources(analysis or {})

    # ── Audit Trail (PRO) or Free banner ─────────────────────
    audit_trail = math.get("audit_trail") if math else None
    audit = parse_audit_trail(audit_trail)

    console.print()
    console.print(_DIVIDER, style=COLORS["divider"])

    if not audit.is_pro:
        _render_pulse_view_banner()
        return

    _render_audit(audit)


def _render_sources(analysis: Analysis) -> None:
    """Show the evidence behind the narrative.

    The report makes claims about the news (a catalyst, a macro backdrop). The
    engine ships the articles it read in `sources_verified`, so print them: an
    unsourced claim the reader cannot trace is exactly what this tool exists to
    expose, including when the source list comes back empty.
    """
    sources = analysis.get("sources_verified", [])
    window = analysis.get("sources_window", "")

    if not sources:
        console.print(
            f"\n  [{COLORS['warning']}]⚠  SOURCES VERIFIED (0): "
            f"the narrative above is not anchored to any article[/]"
        )
        return

    heading = f"  SOURCES VERIFIED ({len(sources)})"
    if window:
        heading += f", window {window}"
    console.print(f"\n  [bold]{heading.strip()}:[/bold]")

    for source in sources:
        tier = source.get("credibility", "—")
        color = CREDIBILITY_COLORS.get(tier, "white")
        console.print(f"    [{color}][{escape(tier)}][/] {escape(source.get('title', ''))}")
        url = source.get("url", "")
        if url:
            console.print(f"             [{COLORS['muted']}]{escape(url)}[/]")


def _render_audit(audit: AuditSummary) -> None:
    console.print("  🛡️  [bold]ANTI-HALLUCINATION AUDIT TRAIL[/bold]")
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print()
    console.print(f"  Pipeline:  [{COLORS['muted']}]{audit.algorithm_id}[/]")
    console.print(f"  Version:   [{COLORS['muted']}]{audit.engine_version}[/]")
    console.print(f"  Seal type: [{COLORS['muted']}]{audit.seal_type}[/]")
    console.print(f"             [{COLORS['muted']}]{audit.seal_explanation}[/]")

    console.print()
    if audit.filters:
        console.print(f"  [bold]Filters fired ({len(audit.filters)}):[/bold]")
        for name, explanation in audit.filters:
            # escape(): a filter name like "band position CENTRO_BANDAS" is valid Rich
            # markup, so an unescaped [name] gets parsed as a style tag and vanishes.
            console.print(
                f"    ✂️  [{COLORS['filter_fired']}]{escape(f'[{name}]')}[/]"
                f"  [{COLORS['muted']}]{escape(explanation)}[/]"
            )
    else:
        console.print(
            f"  [{COLORS['muted']}]No filters fired: the LLM's output was consistent with the math[/]"
        )

    if audit.fields_corrected:
        console.print()
        console.print(
            f"  [bold]Corrections applied to the LLM's output ({len(audit.fields_corrected)}):[/bold]"
        )
        for field_name, reason in audit.fields_corrected:
            console.print(f"    ✏️  [{COLORS['warning']}]{escape(field_name)}[/]")
            console.print(f"        [{COLORS['muted']}]{escape(reason)}[/]")

    if audit.fields_owned:
        console.print()
        console.print(f"  [bold]Fields Python owns, never the LLM ({len(audit.fields_owned)}):[/bold]")
        for field_name in audit.fields_owned:
            console.print(f"    🔒  [{COLORS['field_overridden']}]{escape(field_name)}[/]")
            explanation = explain_field(field_name)
            if explanation:
                console.print(f"        [{COLORS['muted']}]{escape(explanation)}[/]")
        console.print(
            f"\n  [{COLORS['muted']}]The math engine writes these on every response, "
            f"whatever the LLM said.[/]"
        )

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


def render_pro_required(message: str) -> None:
    """Show the Quant plan gate as the offer it is, not as an HTTP failure.

    The API already explains itself ("Quantitative signals require a PRO plan
    subscription."), so print that rather than a paraphrase, and put the trial
    next to it: this fires exactly when the reader reached for a paid engine.
    """
    console.print()
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print(f"  🔒  [{COLORS['free_banner']}]QUANT ENGINES: key required[/]")
    console.print()
    console.print(f"  [{COLORS['muted']}]{escape(message)}[/]")
    console.print(
        f"  [{COLORS['muted']}]The public demo key covers bitcoin and ethereum insights only.[/]"
    )
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
    console.print(f"  [{COLORS['muted']}]Engine: Quant Plus (100% Python, no LLM in this path)[/]")
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
    console.print(f"  [{COLORS['muted']}]Engine: Quant Plus (100% Python, no LLM in this path)[/]")
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
