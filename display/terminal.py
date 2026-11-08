import math as numeric
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urlsplit

from rich.console import Console
from rich.markup import escape
from rich.style import Style
from rich.table import Table
from rich.text import Text
from rich import box

from cryptocapi.audit import AuditSummary, explain_field, parse_audit_trail
from cryptocapi.models import Analysis, InsightData, QuantAsset, ScanResult, SignalResult
from cryptocapi.seal import SealCheck, SealStatus, check_seal
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


# C0 controls except tab and newline, DEL, and the C1 range. ESC (0x1b) is the one
# that matters most: it opens every terminal escape sequence.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]")


def _clean(text: str) -> str:
    """API text with every terminal control character removed.

    Rich's escape() covers its own markup, not the terminal's: a news headline
    carrying ESC sequences reached the screen raw, and one built for it erased
    its own line and printed a green "SEAL VERIFIED" that nothing had verified.
    Source titles come from third-party sites, so this runs on all API text.
    """
    return _CONTROL_CHARS.sub("", text)


def _safe(text: str) -> str:
    """API text ready to sit inside Rich markup: controls removed, markup escaped."""
    return escape(_clean(text))


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
    if sentiment in ("bullish", "very_bullish"):
        return COLORS["sentiment_bullish"]
    if sentiment in ("bearish", "very_bearish"):
        return COLORS["sentiment_bearish"]
    return COLORS["sentiment_neutral"]


def _number(value: object, decimals: int) -> str:
    """An absent or invalid measurement is a gap, never a measured zero."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "—"
    try:
        if not numeric.isfinite(value):
            return "—"
    except OverflowError:
        return "—"
    return f"{value:.{decimals}f}"


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
        # A naive stamp is UTC, as documented by the API. Normalize while
        # guarded: a valid local datetime at year 1 or 9999 can overflow when
        # its offset is converted to UTC.
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return moment.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def _format_age(computed: datetime, now: datetime) -> str:
    """Say how old the analysis is, or "" when that cannot be said honestly.

    A negative age can mean clock skew or a bad timestamp. Report the
    discrepancy without choosing a cause the response cannot establish.
    """
    seconds = (now - computed).total_seconds()
    if seconds < 0:
        return "timestamp ahead of local clock; freshness unknown"
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


def render_insight(data: InsightData, coin_id: str) -> SealCheck:
    """Print an insight and return what the seal check found, so the caller can
    act on a seal that does not match (the CLI exits non-zero on one)."""
    asset = data.get("asset", {})
    name = asset.get("id", coin_id).capitalize()
    symbol = asset.get("symbol", "").upper()
    sentiment = data.get("sentiment") or "unavailable"
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
    check = check_seal(data)

    # `generated_at` first: the API documents it as the age of the analysis in
    # every view. Reading only the trail's stamp left the Pulse view, which has
    # no trail, declaring "no analysis timestamp" while it carried one.
    stamp = data.get("generated_at") or audit.calculated_at

    # ── Header ──────────────────────────────────────────────
    header = Text()
    engine_name = {"radar": "RADAR", "quant_plus": "QUANT PLUS"}.get(
        data.get("engine_used", ""), "INSIGHT"
    )
    header.append(f"  CRYPTOCAPI {engine_name} — ", style=COLORS["header"])
    header.append(_clean(f"{name} ({symbol})"), style=COLORS["coin_name"])
    header.append(f"\n  {_timestamp_line(stamp)}", style=COLORS["muted"])

    console.print()
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print(header)
    console.print(_DIVIDER, style=COLORS["divider"])
    if check.status is SealStatus.MISMATCH:
        _print_wrapped(
            "  ",
            f"[{COLORS['seal_bad']}]SEAL DOES NOT MATCH: response integrity failed; "
            f"values below are untrusted. Narrative withheld.[/]",
        )

    # ── Metrics ──────────────────────────────────────────────
    regime_icon = REGIME_ICONS.get(regime, "📊")
    sentiment_icon = SENTIMENT_ICONS.get(sentiment, "➡️ ")
    s_color = _sentiment_color(sentiment)

    # Everything the API wrote goes through _safe(): the narrative is LLM text,
    # and a "[/]" in it used to crash the render while a "[bold]" silently
    # vanished, so the screen showed something other than what the API sent.
    console.print()
    console.print(f"  {regime_icon} MARKET REGIME:   [{COLORS['regime']}]{_safe(regime)}[/]")
    console.print(f"  {sentiment_icon} SENTIMENT:       [{s_color}]{_safe(sentiment)}[/]")

    if confidence:
        score = _number(confidence.get("score"), 2)
        label = confidence.get("label", "—")
        c_color = CONFIDENCE_COLORS.get(label, "white")
        console.print(f"  🎯 CONFIDENCE:      [{c_color}]{_safe(label)} ({score})[/]")

    if math:
        quality = math.get("data_quality")
        if quality:
            quality_color = COLORS["warning"] if quality != "OPTIMAL" else COLORS["muted"]
            console.print(f"  DATA QUALITY:     [{quality_color}]{_safe(quality)}[/]")
            for reason in math.get("data_quality_reason", []):
                _print_wrapped("    ", f"[{quality_color}]{_safe(reason)}[/]")
        z = math.get("z_score")
        if z is not None:
            # The engine already ships the verdict, computed against its dynamic
            # z_score_threshold. The display must never re-derive it.
            verdict = data.get("statistical_anomaly_detected")
            anomaly = "anomaly verdict unavailable"
            if verdict is True:
                anomaly = "⚠️  ANOMALY DETECTED (API verdict)"
            elif verdict is False:
                anomaly = "no anomaly (API verdict)"
            console.print(f"  🔺 Z-SCORE:         [{COLORS['muted']}]{_number(z, 3)} ({anomaly})[/]")

        bandwidth = math.get("bollinger_bandwidth")
        if bandwidth is not None:
            # The width the narrative talks about, so a reader can hold it up
            # against the prose. Only the width: whether the bands are expanding
            # or compressing is a day-over-day change the engine computes and the
            # response does not carry, so the screen does not claim it either.
            console.print(
                f"  📏 BANDWIDTH:       [{COLORS['muted']}]{_number(bandwidth, 4)} "
                f"(band width / 20-period mean)[/]"
            )

    if is_alert:
        console.print("\n  [bold red]⚡ VOLATILITY ALERT[/bold red]")

    # ── Summary / Report ─────────────────────────────────────
    if check.status is not SealStatus.MISMATCH and report:
        console.print("\n  [bold]ANALYSIS:[/bold]")
        for line in report.strip().split("\n"):
            _print_wrapped("   ", _safe(line))
    elif check.status is not SealStatus.MISMATCH and summary:
        console.print("\n  [bold]SUMMARY:[/bold]")
        _print_wrapped("   ", _safe(summary))

    _render_sources(analysis or {})

    # ── Audit Trail (PRO) or Free banner ─────────────────────
    console.print()
    console.print(_DIVIDER, style=COLORS["divider"])

    if not audit.is_pro:
        _render_pulse_view_banner()
        return SealCheck(SealStatus.UNCHECKED, "this response carries no seal")

    _render_audit(audit, check)
    return check


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
            f"[{COLORS['warning']}]⚠  SOURCES REPORTED BY API (0): "
            f"no article references were included for this narrative[/]",
        )
        return

    heading = f"SOURCES REPORTED BY API ({len(sources)})"
    if window:
        heading += f", window {window}"
    console.print(f"\n  [bold]{_safe(heading)}:[/bold]")

    for source in sources:
        tier = source.get("credibility", "—")
        color = CREDIBILITY_COLORS.get(tier, "white")
        # The title wraps under itself, which is also where the URL starts.
        _print_wrapped(f"    [{color}][{_safe(tier)}][/] ", _safe(source.get("title", "")))
        url = source.get("url", "")
        if url:
            # One unbroken line. Rich used to hard-wrap a long URL at the terminal
            # width, so it reached the screen in two pieces and a click opened
            # the first one, an address that does not exist. soft_wrap leaves the
            # wrapping to the terminal, which keeps it one string to copy, and
            # the link style makes it clickable whole where the terminal can.
            url = _clean(url)
            line = Text("             ")
            line.append(url, style=_url_style(url))
            console.print(line, soft_wrap=True)
    console.print()
    _print_wrapped(
        "  ",
        f"[{COLORS['muted']}]Article contents and narrative claims were not "
        f"independently verified by this client.[/]",
    )


def _url_style(url: str) -> Style:
    muted = Style.parse(COLORS["muted"])
    # Only web addresses become links: the string comes from the API, and a
    # terminal follows whatever scheme a link hands it.
    try:
        parts = urlsplit(url)
        if (
            parts.scheme in ("https", "http")
            and parts.hostname
            and not parts.username
            and not parts.password
            and not any(char.isspace() for char in url)
        ):
            return muted + Style(link=url)
    except ValueError:
        pass
    return muted


def _render_audit(audit: AuditSummary, check: SealCheck) -> None:
    console.print("  🛡️  [bold]ANTI-HALLUCINATION AUDIT TRAIL[/bold]")
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print()
    console.print(f"  Pipeline:  [{COLORS['muted']}]{_safe(audit.algorithm_id)}[/]")
    console.print(f"  Version:   [{COLORS['muted']}]{_safe(audit.engine_version)}[/]")
    console.print(f"  Seal type: [{COLORS['muted']}]{_safe(audit.seal_type)}[/]")
    _print_wrapped("             ", f"[{COLORS['muted']}]{_safe(audit.seal_explanation)}[/]")

    console.print()
    if audit.filters:
        console.print(f"  [bold]Filters fired ({len(audit.filters)}):[/bold]")
        for name, explanation in audit.filters:
            # _safe(): a filter name like "band position CENTRO_BANDAS" is valid Rich
            # markup, so an unescaped [name] gets parsed as a style tag and vanishes.
            _print_wrapped(
                f"    ✂️  [{COLORS['filter_fired']}]{_safe(f'[{name}]')}[/]  ",
                f"[{COLORS['muted']}]{_safe(explanation)}[/]",
            )
    else:
        _print_wrapped(
            "  ",
            f"[{COLORS['muted']}]No filters reported. This does not establish "
            f"that the narrative is factually correct.[/]",
        )

    if audit.fields_corrected:
        console.print()
        console.print(
            f"  [bold]Corrections reported by API ({len(audit.fields_corrected)}):[/bold]"
        )
        for field_name, reason in audit.fields_corrected:
            console.print(f"    ✏️  [{COLORS['warning']}]{_safe(field_name)}[/]")
            _print_wrapped("        ", f"[{COLORS['muted']}]{_safe(reason)}[/]")

    if audit.fields_owned:
        console.print()
        console.print(f"  [bold]Python-owned fields reported by API ({len(audit.fields_owned)}):[/bold]")
        for field_name in audit.fields_owned:
            console.print(f"    🔒  [{COLORS['field_overridden']}]{_safe(field_name)}[/]")
            explanation = explain_field(field_name)
            if explanation:
                _print_wrapped("        ", f"[{COLORS['muted']}]{_safe(explanation)}[/]")
        console.print()
        _print_wrapped(
            "  ",
            f"[{COLORS['muted']}]Ownership is reported by the API; this client "
            f"does not execute the engine's calculations.[/]",
        )

    if audit.fields_unclassified:
        console.print()
        console.print("  [bold]Other overrides reported by API:[/bold]")
        for field_name in audit.fields_unclassified:
            _print_wrapped("    ", _safe(field_name))
        _print_wrapped(
            "    ",
            f"[{COLORS['muted']}]This client has no confirmed interpretation for these entries.[/]",
        )

    if audit.protocol_hash:
        console.print()
        console.print("  Protocol hash (SHA-256):")
        console.print(f"    [{COLORS['hash']}]{_safe(audit.protocol_hash)}[/]")
        _render_seal_check(check)

    console.print()
    console.print(_DIVIDER, style=COLORS["divider"])
    # The closing line reports what the agent itself checked, never more. Not
    # "certified" either: the seal is self-issued, so no third party stands
    # behind it.
    if check.status is SealStatus.VERIFIED:
        console.print(f"  [{COLORS['seal_ok']}]✅ Process seal verified · covered fields match[/]")
    elif check.status is SealStatus.MISMATCH:
        console.print(f"  [{COLORS['seal_bad']}]❌ SEAL DOES NOT MATCH · do not trust this response[/]")
    else:
        console.print(f"  [{COLORS['warning']}]⚠  seal not checked[/]")
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print()


def _render_seal_check(check: SealCheck) -> None:
    """Say what recomputing the seal here found, and how little a match means."""
    if check.status is SealStatus.VERIFIED:
        _print_wrapped(
            "    ",
            f"[{COLORS['seal_ok']}]✓ recomputed here from this response: it matches[/] "
            f"[{COLORS['muted']}](only covered fields match; an unkeyed "
            f"hash cannot say who sealed it)[/]",
        )
        _print_wrapped(
            "    ",
            f"[{COLORS['muted']}]The seal does not cover the narrative, confidence, bandwidth, "
            f"sources, or timestamps. It does not verify market calculations.[/]",
        )
    elif check.status is SealStatus.MISMATCH:
        _print_wrapped(
            "    ",
            f"[{COLORS['seal_bad']}]✗ recomputed here from this response: it does NOT match[/] "
            f"[{COLORS['muted']}]({_safe(check.reason)})[/]",
        )
    else:
        _print_wrapped(
            "    ",
            f"[{COLORS['warning']}]⚠ not checked:[/] [{COLORS['muted']}]{_safe(check.reason)}[/]",
        )


def render_demo_restricted(message: str) -> None:
    console.print()
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print(f"  🔒  [{COLORS['free_banner']}]DEMO KEY — bitcoin & ethereum only[/]")
    console.print()
    _print_wrapped("  ", f"[{COLORS['muted']}]{_safe(message)}[/]")
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
    console.print(f"  [{COLORS['warning']}]NO ANALYSIS YET — {_safe(coin_id)}[/]")
    console.print()
    console.print(f"  [{COLORS['muted']}]CryptoCapi has no analysis for this coin right now:[/]")
    console.print(f"  [{COLORS['muted']}]no engine has produced one, and nothing is shown in its place.[/]")
    console.print(f"  [{COLORS['muted']}]Check the id too: an unknown coin gets the same answer.[/]")
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print()


def render_error(message: str) -> None:
    # _safe(): the message can quote the API, and its text is not markup.
    console.print()
    _print_wrapped("  [bold red]Error:[/bold red] ", _safe(message))
    console.print()


def render_sentiment_change(previous: str, current: str) -> None:
    """Flag a sentiment flip between two polls of `coin --watch`."""
    console.print(
        f"  [{COLORS['warning']}]⚡ SENTIMENT CHANGED:[/] {_safe(previous)} → {_safe(current)}"
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
    _print_wrapped("  ", f"[{COLORS['muted']}]{_safe(message)}[/]")
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
    console.print(f"  [{COLORS['free_banner']}]⚠  NO AUDIT TRAIL[/]")
    console.print()
    console.print(f"  [{COLORS['muted']}]This response carries no audit trail.[/]")
    console.print(f"  [{COLORS['muted']}]Its integrity and calculations were not verified here.[/]")
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
    shown = _number(value, 2)
    # Two decimal places must not promote a reading below the boundary into a
    # displayed trigger, or a partial sample into displayed full evidence.
    if shown == "1.00" and value is not None and value != 1:
        return f"{'<' if value < 1 else '>'}1.00"
    return shown


def render_scan(results: list[ScanResult], strategy: str) -> None:
    console.print()
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print(f"  📡 MARKET SCAN — strategy: [{COLORS['coin_name']}]{_safe(strategy)}[/]")
    console.print(f"  [{COLORS['muted']}]Engine: Quant Plus (API signals; calculations not recomputed here)[/]")
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
            _safe(_asset_label(r.get("asset"))),
            f"[{s_color}]{_safe(signal)}[/]",
            _axis(r.get("threshold_proximity")),
            _axis(r.get("evidence_weight")),
            _safe(regime),
            f"[{c_color}]{_safe(label)}[/]",
        )

    console.print(table)
    # The two axes are the ranking itself, shipped so the order can be checked.
    console.print(
        f"  [{COLORS['muted']}]Prox.: |z| over the asset's own anomaly threshold (1.00 = firing)[/]"
    )
    console.print(
        f"  [{COLORS['muted']}]Evid.: sample size behind that reading (1.00 = full)[/]"
    )
    if results:
        console.print()
        console.print("  [bold]Signal timestamps reported by API:[/bold]")
        for r in results:
            _print_wrapped(
                "  ",
                f"{_safe(_asset_label(r.get('asset')))}: "
                f"[{COLORS['muted']}]{_timestamp_line(r.get('generated_at') or '')}[/]",
            )
    console.print()


def render_batch(results: list[SignalResult]) -> None:
    console.print()
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print(f"  📦 BATCH ANALYSIS — {len(results)} assets")
    console.print(f"  [{COLORS['muted']}]Engine: Quant Plus (API signals; calculations not recomputed here)[/]")
    # "Rendered": each row carries its own `generated_at` and they differ, so no
    # single stamp dates the batch. This is the clock of the run, not the age of
    # the signals. Say which one it is.
    console.print(f"  Rendered {_now_utc()}", style=COLORS["muted"])
    console.print(_DIVIDER, style=COLORS["divider"])

    for r in results:
        label_text = _safe(_asset_label(r.get("asset")))
        console.print()

        # A symbol the engine has no signal for comes back with every field null.
        if r.get("available") is not True:
            availability = (
                "no pre-computed signal for this asset"
                if r.get("available") is False
                else "signal availability not reported"
            )
            _print_wrapped(
                "  ",
                f"[{COLORS['coin_name']}]{label_text}[/]  "
                f"[{COLORS['muted']}]{availability}[/]",
            )
            continue

        signal = r.get("signal") or "—"
        sentiment = r.get("sentiment") or "unavailable"
        regime = r.get("market_regime") or "—"
        confidence = r.get("confidence")
        label = confidence.get("label", "—") if confidence else "—"
        score = _number(confidence.get("score") if confidence else None, 2)
        summary = r.get("summary") or ""
        s_color = _sentiment_color(sentiment)
        c_color = CONFIDENCE_COLORS.get(label, "white")
        sig_color = SIGNAL_COLORS.get(signal, "white")
        sentiment_icon = SENTIMENT_ICONS.get(sentiment, "➡️ ")

        _print_wrapped(
            "  ",
            f"[{COLORS['coin_name']}]{label_text}[/]  "
            f"[{sig_color}]{_safe(signal)}[/]  "
            f"{sentiment_icon} [{s_color}]{_safe(sentiment)}[/]  "
            f"[{c_color}]{_safe(label)} ({score})[/]  "
            f"[{COLORS['regime']}]{_safe(regime)}[/]",
        )
        _print_wrapped(
            "  ",
            f"[{COLORS['muted']}]{_timestamp_line(r.get('generated_at') or '')}[/]",
        )
        if summary:
            _print_wrapped("  ", f"[{COLORS['muted']}]{_safe(summary)}[/]")

    console.print()
    console.print(_DIVIDER, style=COLORS["divider"])
    console.print()
