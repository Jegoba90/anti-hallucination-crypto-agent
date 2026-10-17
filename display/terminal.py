import sys
from datetime import datetime, timezone

from rich.console import Console
from rich.markup import escape
from rich.style import Style
from rich.table import Table
from rich.text import Text
from rich import box

from cryptocapi.audit import AuditSummary, explain_field, parse_audit_trail
from cryptocapi.models import Analysis, InsightData, QuantAsset, ScanResult, SignalResult
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


def _print_wrapped(prefix: str, body: str) -> None:
    """Print `body` after `prefix`, wrapping under the body instead of the margin.

    A plain print wraps long text back to column 0, so a report or an explanation
    ran ragged under its own label, and the README showed it aligned in a way
    the CLI never printed. A two-column grid keeps every wrapped line under the
    first. Both arguments are Rich markup: escape API text before passing it.
    """
    grid = Table.grid()
    grid.add_column(no_wrap=True)
    # fold, not the default ellipsis: a word longer than the line is split, and
    # no character the API sent is ever cut off the screen.
    grid.add_column(overflow="fold")
    grid.add_row(prefix, body)
    console.print(grid)


def _sentiment_color(sentiment: str) -> str:
    if "bullish" in sentiment:
        return COLORS["sentiment_bullish"]
    if "bearish" in sentiment:
        return COLORS["sentiment_bearish"]
    return COLORS["sentiment_neutral"]


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _format_utc(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _now_utc() -> str:
    return _format_utc(_utc_now())


def _parse_calculated_at(raw: str) -> datetime | None:
    """Read the engine's `calculated_at`, or None if absent or unparseable.

    Never raises. A timestamp this renderer cannot read is a reason to say so in
    the header, not to kill a run that is holding a perfectly good analysis.
    """
    if not raw:
        return None
    try:
        moment = datetime.fromisoformat(raw)
    except ValueError:
        return None
    # A naive stamp is UTC: the API documents `calculated_at` in UTC and every
    # response observed carries the trailing Z. Assuming local time here would
    # silently shift the age by the reader's offset.
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


def _format_age(computed: datetime, now: datetime) -> str:
    """Say how old the analysis is, or "" when that cannot be said honestly.

    A negative age means this machine's clock trails the engine's, not that the
    analysis came from the future, so it is omitted rather than printed as a
    nonsense "-3 min ago".
    """
    seconds = (now - computed).total_seconds()
    if seconds < 0:
        return ""
    minutes = int(seconds // 60)
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 48:
        return f"{hours} h ago"
    return f"{hours // 24} d ago"


def _timestamp_line(stamp: str) -> str:
    """Report when the analysis was computed, never when it was printed.

    The header used to print `datetime.now()`, which a reader takes for the age
    of the data and is not: the collector runs on a cron, so a response can be
    up to an hour old by the time it reaches the screen. A wall clock next to the
    numbers is the display layer asserting a freshness nobody measured, which is
    the move this whole tool exists to catch, made by the tool itself.

    `stamp` is the engine's own: `generated_at`, or the seal's `calculated_at`
    in a response that predates it. When a response carries neither, the line
    says the time is the render's rather than passing it off as the data's.
    """
    computed = _parse_calculated_at(stamp)
    if computed is None:
        return f"Rendered {_now_utc()}, this response carries no analysis timestamp"

    age = _format_age(computed, _utc_now())
    line = f"Analysis computed {_format_utc(computed)}"
    return f"{line} ({age})" if age else line


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

    # Parsed before the header, not just before the audit block: when a response
    # has no `generated_at`, the header falls back to the trail's `calculated_at`,
    # so both readers of the audit share one parse.
    audit = parse_audit_trail(math.get("audit_trail") if math else None)

    # `generated_at` first: the API documents it as the age of the analysis in
    # every view. Reading only the trail's stamp left the Pulse view, which has
    # no trail, declaring "no analysis timestamp" while it carried one.
    stamp = data.get("generated_at") or audit.calculated_at

    # ── Header ──────────────────────────────────────────────
    header = Text()
    header.append("  CRYPTOCAPI RADAR — ", style=COLORS["header"])
    header.append(f"{name} ({symbol})", style=COLORS["coin_name"])
    header.append(f"\n  {_timestamp_line(stamp)}", style=COLORS["muted"])

    console.print()
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print(header)
    console.print(_DIVIDER, style=COLORS["divider"])

    # ── Metrics ──────────────────────────────────────────────
    regime_icon = REGIME_ICONS.get(regime, "📊")
    sentiment_icon = SENTIMENT_ICONS.get(sentiment, "➡️ ")
    s_color = _sentiment_color(sentiment)

    # Everything the API wrote goes through escape(): the narrative is LLM text,
    # and a "[/]" in it used to crash the render while a "[bold]" silently
    # vanished, so the screen showed something other than what the API sent.
    console.print()
    console.print(f"  {regime_icon} MARKET REGIME:   [{COLORS['regime']}]{escape(regime)}[/]")
    console.print(f"  {sentiment_icon} SENTIMENT:       [{s_color}]{escape(sentiment)}[/]")

    if confidence:
        score = confidence.get("score", 0.0)
        label = confidence.get("label", "—")
        c_color = CONFIDENCE_COLORS.get(label, "white")
        console.print(f"  🎯 CONFIDENCE:      [{c_color}]{escape(label)} ({score:.2f})[/]")

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

        bandwidth = math.get("bollinger_bandwidth")
        if bandwidth is not None:
            # The width the narrative talks about, so a reader can hold it up
            # against the prose. Only the width: whether the bands are expanding
            # or compressing is a day-over-day change the engine computes and the
            # response does not carry, so the screen does not claim it either.
            console.print(
                f"  📏 BANDWIDTH:       [{COLORS['muted']}]{bandwidth:.4f} "
                f"(band width / 20-period mean)[/]"
            )

    if is_alert:
        console.print("\n  [bold red]⚡ VOLATILITY ALERT[/bold red]")

    # ── Summary / Report ─────────────────────────────────────
    if report:
        console.print("\n  [bold]ANALYSIS:[/bold]")
        for line in report.strip().split("\n"):
            _print_wrapped("   ", escape(line))
    elif summary:
        console.print("\n  [bold]SUMMARY:[/bold]")
        _print_wrapped("   ", escape(summary))

    _render_sources(analysis or {})

    # ── Audit Trail (PRO) or Free banner ─────────────────────
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
        console.print()
        _print_wrapped(
            "  ",
            f"[{COLORS['warning']}]⚠  SOURCES VERIFIED (0): "
            f"the narrative above is not anchored to any article[/]",
        )
        return

    heading = f"  SOURCES VERIFIED ({len(sources)})"
    if window:
        heading += f", window {window}"
    console.print(f"\n  [bold]{heading.strip()}:[/bold]")

    for source in sources:
        tier = source.get("credibility", "—")
        color = CREDIBILITY_COLORS.get(tier, "white")
        # The title wraps under itself, which is also where the URL starts.
        _print_wrapped(f"    [{color}][{escape(tier)}][/] ", escape(source.get("title", "")))
        url = source.get("url", "")
        if url:
            # One unbroken line. Rich used to hard-wrap a long URL at the terminal
            # width, so it reached the screen in two pieces and a click opened
            # the first one, an address that does not exist. soft_wrap leaves the
            # wrapping to the terminal, which keeps it one string to copy, and
            # the link style makes it clickable whole where the terminal can.
            line = Text("             ")
            line.append(url, style=_url_style(url))
            console.print(line, soft_wrap=True)


def _url_style(url: str) -> Style:
    muted = Style.parse(COLORS["muted"])
    # Only web addresses become links: the string comes from the API, and a
    # terminal follows whatever scheme a link hands it.
    if url.startswith(("https://", "http://")):
        return muted + Style(link=url)
    return muted


def _render_audit(audit: AuditSummary) -> None:
    console.print("  🛡️  [bold]ANTI-HALLUCINATION AUDIT TRAIL[/bold]")
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print()
    console.print(f"  Pipeline:  [{COLORS['muted']}]{escape(audit.algorithm_id)}[/]")
    console.print(f"  Version:   [{COLORS['muted']}]{escape(audit.engine_version)}[/]")
    console.print(f"  Seal type: [{COLORS['muted']}]{escape(audit.seal_type)}[/]")
    _print_wrapped("             ", f"[{COLORS['muted']}]{escape(audit.seal_explanation)}[/]")

    console.print()
    if audit.filters:
        console.print(f"  [bold]Filters fired ({len(audit.filters)}):[/bold]")
        for name, explanation in audit.filters:
            # escape(): a filter name like "band position CENTRO_BANDAS" is valid Rich
            # markup, so an unescaped [name] gets parsed as a style tag and vanishes.
            _print_wrapped(
                f"    ✂️  [{COLORS['filter_fired']}]{escape(f'[{name}]')}[/]  ",
                f"[{COLORS['muted']}]{escape(explanation)}[/]",
            )
    else:
        _print_wrapped(
            "  ",
            f"[{COLORS['muted']}]No filters fired: the LLM's output was consistent with the math[/]",
        )

    if audit.fields_corrected:
        console.print()
        console.print(
            f"  [bold]Corrections applied to the LLM's output ({len(audit.fields_corrected)}):[/bold]"
        )
        for field_name, reason in audit.fields_corrected:
            console.print(f"    ✏️  [{COLORS['warning']}]{escape(field_name)}[/]")
            _print_wrapped("        ", f"[{COLORS['muted']}]{escape(reason)}[/]")

    if audit.fields_owned:
        console.print()
        console.print(f"  [bold]Fields Python owns, never the LLM ({len(audit.fields_owned)}):[/bold]")
        for field_name in audit.fields_owned:
            console.print(f"    🔒  [{COLORS['field_overridden']}]{escape(field_name)}[/]")
            explanation = explain_field(field_name)
            if explanation:
                _print_wrapped("        ", f"[{COLORS['muted']}]{escape(explanation)}[/]")
        console.print()
        _print_wrapped(
            "  ",
            f"[{COLORS['muted']}]The math engine writes these on every response, "
            f"whatever the LLM said.[/]",
        )

    if audit.protocol_hash:
        console.print()
        console.print("  Protocol hash (SHA-256):")
        console.print(f"    [{COLORS['hash']}]{escape(audit.protocol_hash)}[/]")

    console.print()
    console.print(_DIVIDER, style=COLORS["divider"])
    # "verifiable", not "certified": the seal is self-issued, and anyone can check
    # it with the recipe in the README. Certified would claim a third party.
    console.print(f"  [{COLORS['seal_ok']}]✅ Math Override applied · seal verifiable[/]")
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print()


def render_demo_restricted(message: str) -> None:
    console.print()
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print(f"  🔒  [{COLORS['free_banner']}]DEMO KEY — bitcoin & ethereum only[/]")
    console.print()
    _print_wrapped("  ", f"[{COLORS['muted']}]{escape(message)}[/]")
    console.print()
    console.print(f"  [{COLORS['pro_banner']}]→ Free 14-day trial: https://cryptocapi.com[/]")
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print()


def render_no_analysis(coin_id: str) -> None:
    """Say the API has no analysis for this coin: an answer, not a failure.

    The API answers `data: null` when no engine has produced an analysis yet, for
    any coin, majors included. Putting something in that gap is exactly what this
    tool exists to catch, so the screen says there is nothing and shows nothing.
    """
    console.print()
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print(f"  [{COLORS['warning']}]NO ANALYSIS YET — {escape(coin_id)}[/]")
    console.print()
    console.print(f"  [{COLORS['muted']}]CryptoCapi has no analysis for this coin right now:[/]")
    console.print(f"  [{COLORS['muted']}]no engine has produced one, and nothing is shown in its place.[/]")
    console.print(f"  [{COLORS['muted']}]Check the id too: an unknown coin gets the same answer.[/]")
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print()


def render_error(message: str) -> None:
    # escape(): the message can quote the API, and its text is not markup.
    console.print()
    _print_wrapped("  [bold red]Error:[/bold red] ", escape(message))
    console.print()


def render_sentiment_change(previous: str, current: str) -> None:
    """Flag a sentiment flip between two polls of `coin --watch`."""
    console.print(
        f"  [{COLORS['warning']}]⚡ SENTIMENT CHANGED:[/] {escape(previous)} → {escape(current)}"
    )
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
    _print_wrapped("  ", f"[{COLORS['muted']}]{escape(message)}[/]")
    _print_wrapped(
        "  ",
        f"[{COLORS['muted']}]The public demo key reaches bitcoin and ethereum only, "
        f"on insights and batch.[/]",
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


def _asset_label(asset: QuantAsset | None) -> str:
    """Name a Quant row. Identity lives under `asset` there, never at the top."""
    asset = asset or {}
    name = (asset.get("id") or "—").capitalize()
    symbol = (asset.get("symbol") or "").upper()
    return f"{name} ({symbol})" if symbol else name


def _axis(value: float | None) -> str:
    # null means the engine had no threshold or sample for this asset: show the
    # gap rather than a 0.00 that would read as a measurement.
    return f"{value:.2f}" if value is not None else "—"


def render_scan(results: list[ScanResult], strategy: str) -> None:
    console.print()
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print(f"  📡 MARKET SCAN — strategy: [{COLORS['coin_name']}]{escape(strategy)}[/]")
    console.print(f"  [{COLORS['muted']}]Engine: Quant Plus (100% Python, no LLM in this path)[/]")
    # "Rendered": each row carries its own `generated_at` and they differ, so no
    # single stamp dates the table. This is the clock of the run, not the age of
    # the signals. Say which one it is.
    console.print(f"  Rendered {_now_utc()}", style=COLORS["muted"])
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print()

    # Short headers on purpose: seven columns have to fit an 80-column terminal.
    # Signal and regime never wrap, because a cut enum value is a lost reading;
    # when space runs out, the asset name wraps instead. The legend below spells
    # out the two headers that need it.
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold white", pad_edge=False)
    table.add_column("#", style="dim")
    table.add_column("Asset", style="cyan")
    table.add_column("Signal", no_wrap=True)
    table.add_column("Prox.", justify="right")
    table.add_column("Evid.", justify="right")
    table.add_column("Regime", no_wrap=True)
    table.add_column("Conf.")

    for i, r in enumerate(results, 1):
        signal = r.get("signal") or "—"
        regime = r.get("market_regime") or "—"
        confidence = r.get("confidence")
        label = confidence.get("label", "—") if confidence else "—"
        c_color = CONFIDENCE_COLORS.get(label, "white")
        s_color = SIGNAL_COLORS.get(signal, "white")

        table.add_row(
            str(i),
            escape(_asset_label(r.get("asset"))),
            f"[{s_color}]{escape(signal)}[/]",
            _axis(r.get("threshold_proximity")),
            _axis(r.get("evidence_weight")),
            escape(regime),
            f"[{c_color}]{escape(label)}[/]",
        )

    console.print(table)
    # The two axes are the ranking itself, shipped so the order can be checked.
    console.print(
        f"  [{COLORS['muted']}]Prox.: |z| over the asset's own anomaly threshold (1.00 = firing)[/]"
    )
    console.print(
        f"  [{COLORS['muted']}]Evid.: sample size behind that reading (1.00 = full)[/]"
    )
    console.print()


def render_batch(results: list[SignalResult]) -> None:
    console.print()
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print(f"  📦 BATCH ANALYSIS — {len(results)} assets")
    console.print(f"  [{COLORS['muted']}]Engine: Quant Plus (100% Python, no LLM in this path)[/]")
    # "Rendered": each row carries its own `generated_at` and they differ, so no
    # single stamp dates the batch. This is the clock of the run, not the age of
    # the signals. Say which one it is.
    console.print(f"  Rendered {_now_utc()}", style=COLORS["muted"])
    console.print(_DIVIDER, style=COLORS["divider"])

    for r in results:
        label_text = escape(_asset_label(r.get("asset")))
        console.print()

        # A symbol the engine has no signal for comes back with every field null.
        if not r.get("available", True):
            _print_wrapped(
                "  ",
                f"[{COLORS['coin_name']}]{label_text}[/]  "
                f"[{COLORS['muted']}]no pre-computed signal for this asset[/]",
            )
            continue

        signal = r.get("signal") or "—"
        sentiment = r.get("sentiment") or "neutral"
        regime = r.get("market_regime") or "—"
        confidence = r.get("confidence")
        label = confidence.get("label", "—") if confidence else "—"
        score = confidence.get("score", 0.0) if confidence else 0.0
        summary = r.get("summary") or ""
        s_color = _sentiment_color(sentiment)
        c_color = CONFIDENCE_COLORS.get(label, "white")
        sig_color = SIGNAL_COLORS.get(signal, "white")
        sentiment_icon = SENTIMENT_ICONS.get(sentiment, "➡️ ")

        _print_wrapped(
            "  ",
            f"[{COLORS['coin_name']}]{label_text}[/]  "
            f"[{sig_color}]{escape(signal)}[/]  "
            f"{sentiment_icon} [{s_color}]{escape(sentiment)}[/]  "
            f"[{c_color}]{escape(label)} ({score:.2f})[/]  "
            f"[{COLORS['regime']}]{escape(regime)}[/]",
        )
        if summary:
            _print_wrapped("  ", f"[{COLORS['muted']}]{escape(summary)}[/]")

    console.print()
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print()
