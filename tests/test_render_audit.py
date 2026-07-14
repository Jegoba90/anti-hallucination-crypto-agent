"""What the audit block claims on screen must survive the renderer.

Two things are pinned here. First, filter names must actually appear: a name like
"band position CENTRO_BANDAS" is valid Rich markup, so printing it unescaped made
Rich parse it as a style tag and swallow it, blanking out one of the four headline
filters in the very section that sells the product. Second, the block must keep a
guarantee and a catch apart, because they are different claims: the fields Python
owns are written on every response, while a correction only shows up when the
pipeline actually overrode the LLM.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cryptocapi.models import InsightData
from display.terminal import console, render_insight


def _render(data: InsightData) -> str:
    with console.capture() as capture:
        render_insight(data, "bitcoin")
    return capture.get()


def _load_fixture() -> InsightData:
    fixture_path = Path(__file__).parent / "fixtures" / "sample_response.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))["data"]


class TestFilterNamesSurviveRichMarkup:
    def test_band_position_filter_name_is_not_swallowed(self) -> None:
        out = _render(_load_fixture())

        assert "band position CENTRO_BANDAS" in out
        assert "LEY 7 volume" in out

    def test_filter_name_that_looks_like_a_style_tag_still_prints(self) -> None:
        data = _load_fixture()
        data["math_diagnostics"]["audit_trail"]["filters_applied"] = ["bold red on blue"]

        out = _render(data)

        assert "bold red on blue" in out


class TestFieldsAreExplained:
    """A raw key like `analysis.sentiment_score` tells a reader nothing on its own."""

    def test_every_owned_field_carries_a_plain_language_explanation(self) -> None:
        from cryptocapi.audit import explain_field, parse_audit_trail

        trail = _load_fixture()["math_diagnostics"]["audit_trail"]
        summary = parse_audit_trail(trail)

        for field_name in summary.fields_owned:
            assert explain_field(field_name), f"{field_name} has no explanation"

    def test_the_explanation_reaches_the_screen(self) -> None:
        out = _render(_load_fixture())

        assert "the volatility flag" in out
        assert "Bollinger bandwidth" in out


class TestGuaranteeAndCatchAreSeparate:
    def test_fixture_shows_both_sections(self) -> None:
        out = _render(_load_fixture())

        assert "Corrections applied to the LLM's output (2)" in out
        assert "Fields Python owns, never the LLM (5)" in out

    def test_a_quiet_response_shows_no_corrections_section(self) -> None:
        data = _load_fixture()
        trail = data["math_diagnostics"]["audit_trail"]
        trail["filters_applied"] = []
        trail["sentiment_override"] = False
        trail["fields_overridden"] = [
            "analysis.anomaly_details",
            "analysis.confidence",
            "analysis.sentiment_score",
            "confidence",
            "is_volatility_alert",
        ]

        out = _render(data)

        assert "Corrections applied" not in out
        assert "Fields Python owns, never the LLM (5)" in out
