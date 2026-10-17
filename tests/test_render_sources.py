"""The evidence behind the narrative must reach the screen.

The report talks about catalysts and macro backdrop. The engine ships the
articles it actually read in `analysis.sources_verified`, and the renderer used
to drop them on the floor, leaving the reader with a claim and no way to trace
it. An analysis that arrives with zero sources is a finding in itself, so that
case is rendered as a warning rather than silently omitted.
"""

import io
import json
import sys
from pathlib import Path

from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import display.terminal
from cryptocapi.models import InsightData
from display.terminal import console, render_insight


def _render(data: InsightData) -> str:
    with console.capture() as capture:
        render_insight(data, "bitcoin")
    return capture.get()


def _load_fixture() -> InsightData:
    fixture_path = Path(__file__).parent / "fixtures" / "radar_alpha_v2.2.0.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    return fixture["data"]


class TestSourcesAreRendered:
    def test_fixture_sources_reach_the_screen(self) -> None:
        out = _render(_load_fixture())

        assert "SOURCES VERIFIED (1)" in out
        assert "window 24h" in out
        assert "Tier 2" in out
        assert "Bitcoin Miner Ditches Site for AI Deal" in out
        assert "https://decrypt.co/377363/bitcoin-mine-ai-deal-1-2-billion" in out

    def test_missing_sources_are_flagged_not_hidden(self) -> None:
        data = _load_fixture()
        data["analysis"]["sources_verified"] = []

        out = _render(data)

        assert "SOURCES VERIFIED (0)" in out
        assert "not anchored" in out


# Live on 2026-10-17: 129 characters, longer than a terminal line.
_LONG_URL = (
    "https://www.coindesk.com/tech/2026/10/16/satoshi-era-bitcoin-faces-a-bigger-"
    "quantum-threat-after-google-s-new-willow-breakthrough"
)


def _with_source(url: str) -> InsightData:
    data = _load_fixture()
    data["analysis"]["sources_verified"] = [
        {"title": "Satoshi-era bitcoin faces a bigger quantum threat", "url": url, "credibility": "Tier 1"}
    ]
    return data


class TestLinksStayWhole:
    """A long source URL used to be cut in two by a hard line break, so a click
    opened the first half: an address that does not exist, under a heading that
    says the source was verified."""

    def test_a_url_longer_than_the_line_reaches_the_screen_unbroken(self) -> None:
        out = _render(_with_source(_LONG_URL))

        assert len(_LONG_URL) > console.width
        assert _LONG_URL in out

    def test_on_a_terminal_the_url_is_a_real_link(self, monkeypatch) -> None:
        out = _render_on_a_terminal(monkeypatch, _with_source(_LONG_URL))

        # OSC 8, the terminal hyperlink escape, carrying the whole address.
        assert f";{_LONG_URL}\x1b\\" in out

    def test_only_a_web_address_becomes_a_link(self, monkeypatch) -> None:
        """The URL comes from the API; a terminal follows whatever scheme it gets."""
        out = _render_on_a_terminal(monkeypatch, _with_source("file:///etc/passwd"))

        assert "file:///etc/passwd" in out
        assert "\x1b]8;" not in out


def _render_on_a_terminal(monkeypatch, data: InsightData) -> str:
    """Render as a modern terminal would receive it, escape codes included.

    legacy_windows=False on purpose: writing to a buffer, Rich on Windows takes
    the old console for granted and drops links, which no VT-capable terminal
    (Windows Terminal, VS Code) does. Without it the test would pass on Linux CI
    and fail on the machine this agent is developed on.
    """
    buffer = io.StringIO()
    terminal = Console(
        file=buffer, force_terminal=True, color_system="truecolor", width=60, legacy_windows=False
    )
    monkeypatch.setattr(display.terminal, "console", terminal)
    display.terminal.render_insight(data, "bitcoin")
    return buffer.getvalue()
