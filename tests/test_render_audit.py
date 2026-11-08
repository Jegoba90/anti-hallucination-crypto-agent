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
    fixture_path = Path(__file__).parent / "fixtures" / "radar_alpha_v2.2.0.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))["data"]


def _with_trail(**fields: object) -> InsightData:
    """The real fixture with its audit trail changed: the cases here are built,
    not borrowed, so they hold whatever response the fixture happens to be."""
    data = _load_fixture()
    data["math_diagnostics"]["audit_trail"].update(fields)  # type: ignore[typeddict-item]
    return data


class TestFilterNamesSurviveRichMarkup:
    def test_band_position_filter_name_is_not_swallowed(self) -> None:
        # The name exactly as insights_common.py emits it.
        out = _render(_with_trail(filters_applied=["LEY 7 volume", "band position (CENTRO_BANDAS)"]))

        assert "band position (CENTRO_BANDAS)" in out
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
    def test_the_real_seal_shows_both_sections(self) -> None:
        """The production response: one filter fired, the report was rewritten."""
        out = _render(_load_fixture())

        assert "Corrections reported by API (1)" in out
        assert "Python-owned fields reported by API (5)" in out

    def test_every_conditional_entry_is_a_correction(self) -> None:
        """sentiment, the report and, since v2.4.0-radar, the summary."""
        out = _render(
            _with_trail(
                sentiment_override=True,
                filters_applied=["LEY 7 volume"],
                fields_overridden=[
                    "analysis.anomaly_details",
                    "analysis.confidence",
                    "analysis.detailed_report",
                    "analysis.sentiment_score",
                    "confidence",
                    "is_volatility_alert",
                    "sentiment",
                    "summary",
                ],
            )
        )

        assert "Corrections reported by API (3)" in out
        assert "Python-owned fields reported by API (5)" in out

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

        assert "Corrections reported" not in out
        assert "Python-owned fields reported by API (5)" in out
        assert "consistent with the math" not in out
        assert "does not establish" in out

    def test_unknown_overrides_are_not_presented_as_confirmed_python_ownership(self) -> None:
        out = _render(_with_trail(fields_overridden=["future_field"]))

        assert "Other overrides reported by API" in out
        assert "future_field" in out
        assert "Python-owned fields" not in out

    def test_a_matching_hash_does_not_claim_the_narrative_was_verified(self) -> None:
        out = _render(_load_fixture())

        assert "covered fields match" in out
        assert "does not cover the narrative" in out
        assert "Math Override applied" not in out

    def test_a_bad_seal_is_flagged_before_metrics_and_withholds_narrative(self) -> None:
        data = _load_fixture()
        data["sentiment"] = "bearish"
        data["analysis"]["detailed_report"] = "Untrusted narrative marker"

        out = _render(data)

        assert out.index("SEAL DOES NOT MATCH") < out.index("MARKET REGIME")
        assert "Narrative withheld" in out
        assert "Untrusted narrative marker" not in out
