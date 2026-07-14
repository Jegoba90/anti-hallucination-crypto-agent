"""The evidence behind the narrative must reach the screen.

The report talks about catalysts and macro backdrop. The engine ships the
articles it actually read in `analysis.sources_verified`, and the renderer used
to drop them on the floor, leaving the reader with a claim and no way to trace
it. An analysis that arrives with zero sources is a finding in itself, so that
case is rendered as a warning rather than silently omitted.
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
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    return fixture["data"]


class TestSourcesAreRendered:
    def test_fixture_sources_reach_the_screen(self) -> None:
        out = _render(_load_fixture())

        assert "SOURCES VERIFIED (1)" in out
        assert "window 24h" in out
        assert "Tier 1" in out
        assert "Bitcoin holds above key support" in out

    def test_missing_sources_are_flagged_not_hidden(self) -> None:
        data = _load_fixture()
        data["analysis"]["sources_verified"] = []

        out = _render(data)

        assert "SOURCES VERIFIED (0)" in out
        assert "not anchored" in out
