"""Guards the README's CLI screen against silent drift.

The README shows one screen of the CLI: the real output of a query run on
2026-10-17, which replaced a demo GIF recorded in July on an engine three
versions old, which kept showing what the CLI no longer printed. These keep it
what the CLI prints for that response, and keep it the only screen: for a while
the README showed two, and most of the second repeated the first.

Exact column positions are not compared, on purpose: they depend on the
installed Rich, which measures emoji differently (13.7 counts "✂️" as one cell,
15 as two), so the floors job in CI would fail on a README that is right for the
version a fresh install gets. What is compared is every word, and that no line
of wrapped text falls back to the margin, which is how the CLI printed long
lines before.
"""

import json
import re
import sys
from pathlib import Path

from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_REPO_ROOT = Path(__file__).resolve().parents[1]

# The real query the README shows, kept byte for byte, and the width of the
# terminal it was run in, which is why the screen reads as wide as it does.
DEMO_FIXTURE = "readme_demo_bitcoin_2026-10-17.json"
DEMO_WIDTH = 135


def _load_readme() -> str:
    return (_REPO_ROOT / "README.md").read_text(encoding="utf-8")


def _words(text: str) -> list[str]:
    """The content, word by word: line breaks and the live age aside."""
    return re.sub(r"\(\d+ (?:min|h|d) ago\)", "", text).split()


def _lines_back_at_the_margin(text: str) -> list[str]:
    """Lines that start at column 0 and are not a divider: wrapped text that lost
    its indentation, which is how the CLI printed long lines before."""
    return [line for line in text.splitlines() if line.strip() and not line[0].isspace() and not line.startswith("─")]


def render_cli(fixture_name: str, width: int) -> str:
    """What `coin bitcoin` prints for a fixture at a given terminal width.

    Shared with whoever regenerates the README screen, so the two can only be
    produced one way.
    """
    import display.terminal

    fixture_path = Path(__file__).parent / "fixtures" / fixture_name
    data = json.loads(fixture_path.read_text(encoding="utf-8"))["data"]
    original = display.terminal.console
    display.terminal.console = Console(width=width, color_system=None)
    try:
        with display.terminal.console.capture() as capture:
            display.terminal.render_insight(data, "bitcoin")
    finally:
        display.terminal.console = original
    return capture.get()


class TestReadmeScreenIsARealRun:
    def _block(self) -> str:
        match = re.search(
            r"What `python agent\.py coin bitcoin` prints for .*?\n\n```\n(.*?)```",
            _load_readme(),
            re.DOTALL,
        )
        assert match is not None, "README no longer opens with the CLI screen"
        return match.group(1)

    def test_the_screen_says_what_the_cli_prints_for_the_capture(self) -> None:
        assert _words(self._block()) == _words(render_cli(DEMO_FIXTURE, DEMO_WIDTH))

    def test_neither_sends_wrapped_text_back_to_the_margin(self) -> None:
        assert _lines_back_at_the_margin(render_cli(DEMO_FIXTURE, DEMO_WIDTH)) == []
        assert _lines_back_at_the_margin(self._block()) == []

    def test_the_hash_on_show_is_the_captures_seal(self) -> None:
        fixture = json.loads((Path(__file__).parent / "fixtures" / DEMO_FIXTURE).read_text(encoding="utf-8"))
        seal = fixture["data"]["math_diagnostics"]["audit_trail"]["protocol_hash"]

        assert seal in self._block()


class TestTheReadmeShowsOneScreen:
    def test_one_screen_and_one_audit_trail(self) -> None:
        """Two screens, or a second audit block, would repeat the first."""
        readme = _load_readme()

        assert readme.count("CRYPTOCAPI RADAR —") == 1
        assert readme.count("ANTI-HALLUCINATION AUDIT TRAIL") == 1

    def test_no_gif_is_left_behind(self) -> None:
        assert "demo.gif" not in _load_readme()
        assert not (_REPO_ROOT / "demo.gif").exists()
