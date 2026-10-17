"""Guards the README's example output against silent drift.

The `Output` block in the README prints a `protocol_hash` next to a list of
`fields_overridden`. Those two must belong to the same response: the hash is a
digest *of* that list (among other fields), so if the block is edited and the
list stops matching, the README stops passing its own verification, which is the
one thing this project promises. These tests pin that block to the fixture the
rest of the suite already hashes.
"""

import json
import re
import sys
from pathlib import Path

from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_readme() -> str:
    return (_REPO_ROOT / "README.md").read_text(encoding="utf-8")


def _output_section() -> str:
    """The README's Output section alone.

    The README now opens with a second CLI run, so a search over the whole file
    finds that one first: these tests once read the owned fields from the demo
    and the corrections from the Output block, and passed by coincidence.
    """
    match = re.search(r"\n## Output\n(.*?)\n## ", _load_readme(), re.DOTALL)
    assert match is not None, "README no longer has an Output section"
    return match.group(1)


def _load_fixture_audit_trail() -> dict:
    fixture_path = Path(__file__).parent / "fixtures" / "radar_alpha_v2.2.0.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    return fixture["data"]["math_diagnostics"]["audit_trail"]


def _block(heading: str, readme: str) -> tuple[int, str]:
    """Return the (N) count and the body of a heading, up to the next blank line.

    Entries in the README wrap onto continuation lines, so the body is everything
    until the block ends rather than only the lines carrying an icon.
    """
    match = re.search(rf"{heading} \((\d+)\):\n((?:.+\n)+)", readme)
    assert match is not None, f"README no longer has a '{heading}' block"
    return int(match.group(1)), match.group(2)


class TestReadmeOutputBlock:
    def test_owned_plus_corrected_match_the_fixture(self) -> None:
        """The block splits the sealed list in two. Nothing may be lost or invented."""
        readme = _output_section()

        owned_count, owned_body = _block("Fields Python owns, never the LLM", readme)
        corrected_count, corrected_body = _block(
            "Corrections applied to the LLM's output", readme
        )

        owned = re.findall(r"🔒\s+(\S+)", owned_body)
        corrected = re.findall(r"✏️\s+(\S+)", corrected_body)
        expected = _load_fixture_audit_trail()["fields_overridden"]

        assert sorted(owned + corrected) == sorted(expected), (
            "the two blocks must partition exactly what the seal hashes"
        )
        assert owned_count == len(owned), "the (N) count contradicts the list"
        assert corrected_count == len(corrected), "the (N) count contradicts the list"

    def test_a_field_is_never_both_a_guarantee_and_a_catch(self) -> None:
        readme = _output_section()

        owned = re.findall(r"🔒\s+(\S+)", _block("Fields Python owns, never the LLM", readme)[1])
        corrected = re.findall(
            r"✏️\s+(\S+)", _block("Corrections applied to the LLM's output", readme)[1]
        )

        assert not set(owned) & set(corrected)

    def test_filters_fired_count_matches_the_fixture(self) -> None:
        match = re.search(r"Filters fired \((\d+)\):", _output_section())
        assert match is not None, "README no longer has a 'Filters fired' block"

        expected = _load_fixture_audit_trail()["filters_applied"]
        assert int(match.group(1)) == len(expected)

    def test_printed_hash_matches_the_fixture(self) -> None:
        match = re.search(r"Protocol hash \(SHA-256\):\n\s*(0x[0-9a-f]{64})", _output_section())
        assert match is not None, "README no longer prints a protocol hash"

        assert match.group(1) == _load_fixture_audit_trail()["protocol_hash"]


# The width the README's Output block is rendered at.
README_WIDTH = 78


def _words(text: str) -> list[str]:
    """The content, word by word: line breaks and the live age aside."""
    return re.sub(r"\(\d+ (?:min|h|d) ago\)", "", text).split()


def _lines_back_at_the_margin(text: str) -> list[str]:
    """Lines that start at column 0 and are not a divider: wrapped text that lost
    its indentation, which is how the CLI printed long lines before."""
    return [line for line in text.splitlines() if line.strip() and not line[0].isspace() and not line.startswith("─")]


# The README's opening block replaces a demo GIF: the real output of a query
# run on 2026-10-17, kept byte for byte, at the width of the terminal it was run
# in, which is why it reads as wide as it does.
DEMO_FIXTURE = "readme_demo_bitcoin_2026-10-17.json"
DEMO_WIDTH = 135


def render_cli(fixture_name: str, width: int) -> str:
    """What `coin bitcoin` prints for a fixture at a given terminal width.

    Shared with whoever regenerates a README block, so the two can only be
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


def render_readme_output() -> str:
    """The Output block: the production response where a filter fired."""
    return render_cli("radar_alpha_v2.2.0.json", README_WIDTH)


class TestReadmeOutputIsTheRealOutput:
    """The block once lagged the renderer (no SOURCES section for months), and
    once showed wrapped text neatly aligned while the CLI sent it back to the
    margin. Comparing words catches the first; the margin check, the second.

    Exact column positions are not compared, on purpose: they depend on the
    installed Rich, which measures emoji differently (13.7 counts "✂️" as one
    cell, 15 as two), so the floors job in CI would fail on a README that is
    right for the version a fresh install gets.
    """

    def _block(self) -> str:
        match = re.search(r"```\n(.*?)```", _output_section(), re.DOTALL)
        assert match is not None, "README's Output section no longer has a block"
        return match.group(1)

    @staticmethod
    def _audit_trail(rendered: str) -> str:
        """The audit block of a render, from the divider above its title to the end.

        The Output section shows only this part: the full screen of a run is
        already at the top of the README, and showing two would repeat it.
        """
        lines = rendered.splitlines()
        title = next(i for i, line in enumerate(lines) if "ANTI-HALLUCINATION AUDIT TRAIL" in line)
        return "\n".join(lines[title - 1 :])

    def test_the_block_says_what_the_cli_prints_for_the_fixture(self) -> None:
        assert _words(self._block()) == _words(self._audit_trail(render_readme_output()))

    def test_neither_sends_wrapped_text_back_to_the_margin(self) -> None:
        assert _lines_back_at_the_margin(render_readme_output()) == []
        assert _lines_back_at_the_margin(self._block()) == []

    def test_the_readme_shows_one_full_run_not_two(self) -> None:
        """The opening run and the Output section once both printed a whole screen."""
        assert _load_readme().count("CRYPTOCAPI RADAR —") == 1


class TestReadmeDemoIsARealRun:
    """The README opened with a GIF recorded in July, on an engine three versions
    old, which kept showing what the CLI no longer printed. It is now the text
    of a real run, and these keep it the CLI's output for that response."""

    def _block(self) -> str:
        match = re.search(
            r"What `python agent\.py coin bitcoin` printed on .*?\n\n```\n(.*?)```",
            _load_readme(),
            re.DOTALL,
        )
        assert match is not None, "README no longer opens with the demo block"
        return match.group(1)

    def test_the_block_says_what_the_cli_prints_for_the_capture(self) -> None:
        assert _words(self._block()) == _words(render_cli(DEMO_FIXTURE, DEMO_WIDTH))

    def test_it_keeps_its_indentation(self) -> None:
        assert _lines_back_at_the_margin(self._block()) == []

    def test_the_hash_on_show_is_the_captures_seal(self) -> None:
        fixture = json.loads((Path(__file__).parent / "fixtures" / DEMO_FIXTURE).read_text(encoding="utf-8"))
        seal = fixture["data"]["math_diagnostics"]["audit_trail"]["protocol_hash"]

        assert seal in self._block()

    def test_no_gif_is_left_behind(self) -> None:
        assert "demo.gif" not in _load_readme()
        assert not (_REPO_ROOT / "demo.gif").exists()
