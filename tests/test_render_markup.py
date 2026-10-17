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
