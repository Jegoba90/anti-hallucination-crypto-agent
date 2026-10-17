"""Long text keeps its indentation, nothing the API sent is cut, and the band
width the narrative talks about is on screen.

The CLI printed long lines with a plain print, so a report, a source title or an
explanation wrapped back to column 0 under its own label. The README showed the
same output aligned by hand, which the CLI never printed. And the narrative
talks about the Bollinger bands while the CLI never showed their width, though
the response carries it.
"""

import re
import sys
from pathlib import Path

import pytest
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import display.terminal
from cryptocapi.models import InsightData

_LONG = (
    "El precio opera en la zona inferior de las Bandas de Bollinger, manteniendose "
    "en rango sin ruptura clara y sin catalizador fundamental evidente en la ventana."
)


def _render(monkeypatch: pytest.MonkeyPatch, data: InsightData, width: int = 60) -> str:
    monkeypatch.setattr(display.terminal, "console", Console(width=width, color_system=None))
    with display.terminal.console.capture() as capture:
        display.terminal.render_insight(data, "bitcoin")
    return capture.get()


def _insight(**fields: object) -> InsightData:
    data: dict[str, object] = {"asset": {"id": "bitcoin", "symbol": "BTC"}, "sentiment": "neutral"}
    data.update(fields)
    return data  # type: ignore[return-value]


def _section(out: str, heading: str) -> list[str]:
    """The lines under a heading, up to the next blank line."""
    lines = out.splitlines()
    start = next(i for i, line in enumerate(lines) if heading in line) + 1
    end = next(i for i in range(start, len(lines)) if not lines[i].strip())
    return lines[start:end]


class TestLongTextKeepsItsIndent:
    def test_a_wrapped_report_stays_under_its_heading(self, monkeypatch: pytest.MonkeyPatch) -> None:
        out = _render(monkeypatch, _insight(analysis={"detailed_report": _LONG}))

        report = _section(out, "ANALYSIS:")
        assert len(report) > 1, "the report should wrap at 60 columns"
        assert all(line.startswith("   ") and line[3] != " " for line in report)

    def test_a_wrapped_source_title_lines_up_with_its_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        source = {"title": _LONG, "url": "https://example.org/a", "credibility": "Tier 1"}
        out = _render(monkeypatch, _insight(analysis={"sources_verified": [source]}))

        lines = _section(out, "SOURCES VERIFIED")
        continuation = [line for line in lines[1:] if "https://" not in line]
        assert continuation, "the title should wrap at 60 columns"
        assert all(re.match(r" {13}\S", line) for line in continuation + lines[-1:])

    def test_a_word_longer_than_the_line_is_folded_not_cut(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        word = "x" * 120
        out = _render(monkeypatch, _insight(analysis={"detailed_report": f"start {word} end"}))

        joined = "".join(line.strip() for line in _section(out, "ANALYSIS:"))
        assert word in joined
        assert "…" not in out


class TestBatchRowsKeepTheirIndent:
    def test_a_wrapped_batch_row_stays_indented(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Live at 60 columns, the regime fell back to column 0 under its asset."""
        row = {
            "asset": {"id": "bitcoin", "symbol": "btc"},
            "available": True,
            "signal": "HOLD",
            "sentiment": "neutral",
            "market_regime": "RANGING_CHOP",
            "confidence": {"score": 0.63, "label": "MEDIUM"},
        }
        monkeypatch.setattr(display.terminal, "console", Console(width=50, color_system=None))
        with display.terminal.console.capture() as capture:
            display.terminal.render_batch([row])  # type: ignore[list-item]

        regime_line = next(line for line in capture.get().splitlines() if "RANGING_CHOP" in line)
        assert "Bitcoin" not in regime_line, "the row should wrap at 50 columns"
        assert regime_line.startswith("  ") and regime_line[2] != " "


class TestBandwidthIsShown:
    def test_the_width_the_narrative_talks_about_is_on_screen(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        out = _render(monkeypatch, _insight(math_diagnostics={"z_score": -0.4278, "bollinger_bandwidth": 0.0686}))

        assert "BANDWIDTH:       0.0686" in out

    def test_it_never_claims_a_trend_the_response_does_not_carry(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Expanding or compressing is a day-over-day change the API does not ship."""
        out = _render(monkeypatch, _insight(math_diagnostics={"bollinger_bandwidth": 0.0686}))

        line = next(line for line in out.splitlines() if "BANDWIDTH" in line)
        assert not re.search(r"(?i)expand|compress", line)

    def test_no_bandwidth_no_line(self, monkeypatch: pytest.MonkeyPatch) -> None:
        out = _render(monkeypatch, _insight(math_diagnostics={"z_score": 0.1}))

        assert "BANDWIDTH" not in out
