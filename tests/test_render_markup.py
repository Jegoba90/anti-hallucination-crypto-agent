"""Text the API wrote must print as text, never be parsed as Rich markup.

The insight renderer put the narrative straight into markup strings. The
narrative is LLM text, so a "[/]" in it crashed the render with a MarkupError
and a "[bold]" vanished from the screen: in a tool whose whole claim is showing
exactly what the engine said, the display layer was editing it. The sources and
the filter names were already escaped; these pin the rest.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cryptocapi.models import InsightData
from display.terminal import console, render_error, render_insight


def _render(data: InsightData) -> str:
    with console.capture() as capture:
        render_insight(data, "bitcoin")
    return capture.get()


def _insight(**fields):
    return {"asset": {"id": "bitcoin", "symbol": "BTC"}, "sentiment": "neutral", **fields}


class TestTheNarrativeIsText:
    def test_a_closing_tag_in_the_summary_does_not_crash_the_render(self) -> None:
        out = _render(_insight(summary="Rango [/] lateral"))

        assert "Rango [/] lateral" in out

    def test_a_tag_in_the_report_is_printed_not_applied(self) -> None:
        out = _render(_insight(analysis={"detailed_report": "Soporte en [bold] zona media"}))

        assert "Soporte en [bold] zona media" in out

    def test_audit_fields_are_text_too(self) -> None:
        out = _render(
            _insight(
                math_diagnostics={
                    "market_regime": "RANGING_CHOP",
                    "audit_trail": {
                        "protocol_hash": "0xabc",
                        "algorithm_id": "Radar [beta]",
                        "engine_version": "v9.9.9-radar",
                        "seal_type": "process_seal",
                    },
                }
            )
        )

        assert "Radar [beta]" in out


class TestErrorsAreText:
    def test_an_error_quoting_the_api_prints_verbatim(self) -> None:
        with console.capture() as capture:
            render_error("CryptoCapi answered 400: [/] is not a coin id")

        assert "[/] is not a coin id" in capture.get()


_ESC = chr(27)
# What a hostile headline could carry: erase the line, rewind, print a fake
# verdict in green, and hide a link. None of it may reach the terminal.
_INJECTED = f"Headline{_ESC}[2K{chr(13)}{_ESC}[32m  SEAL VERIFIED{_ESC}[0m"


def _on_a_terminal(monkeypatch, draw) -> str:
    """Render as a real terminal receives it, escape codes included."""
    import io

    import display.terminal
    from rich.console import Console

    buffer = io.StringIO()
    monkeypatch.setattr(
        display.terminal,
        "console",
        Console(file=buffer, force_terminal=True, color_system="truecolor", width=100, legacy_windows=False),
    )
    draw(display.terminal)
    return buffer.getvalue()


def _assert_nothing_injected(out: str) -> None:
    assert f"{_ESC}[2K" not in out
    assert f"{_ESC}[32m  SEAL VERIFIED" not in out
    assert f"{_ESC}]8;;evil" not in out
    assert chr(13) not in out


class TestControlCharactersNeverReachTheTerminal:
    """Rich's escape() covers its markup, not the terminal's. A news headline
    carrying ESC sequences reached the screen raw, and one built for it erased
    its own line and printed a green "SEAL VERIFIED" nothing had verified."""

    def test_a_source_title_and_url(self, monkeypatch) -> None:
        data = _insight(
            analysis={
                "sources_verified": [
                    {"title": _INJECTED, "url": f"https://x.test/{_ESC}]8;;evil", "credibility": "Tier 1"}
                ]
            }
        )

        out = _on_a_terminal(monkeypatch, lambda t: t.render_insight(data, "bitcoin"))

        _assert_nothing_injected(out)
        assert "Headline" in out

    def test_the_narrative(self, monkeypatch) -> None:
        data = _insight(analysis={"detailed_report": _INJECTED}, summary=_INJECTED)

        _assert_nothing_injected(_on_a_terminal(monkeypatch, lambda t: t.render_insight(data, "bitcoin")))

    def test_a_filter_name(self, monkeypatch) -> None:
        data = _insight(
            math_diagnostics={
                "audit_trail": {"protocol_hash": "0xabc", "seal_type": "process_seal", "filters_applied": [_INJECTED]}
            }
        )

        _assert_nothing_injected(_on_a_terminal(monkeypatch, lambda t: t.render_insight(data, "bitcoin")))

    def test_an_error_quoting_the_api(self, monkeypatch) -> None:
        _assert_nothing_injected(_on_a_terminal(monkeypatch, lambda t: t.render_error(_INJECTED)))

    def test_a_batch_summary(self, monkeypatch) -> None:
        row = {"asset": {"id": "bitcoin", "symbol": "btc"}, "available": True, "summary": _INJECTED}

        _assert_nothing_injected(_on_a_terminal(monkeypatch, lambda t: t.render_batch([row])))
