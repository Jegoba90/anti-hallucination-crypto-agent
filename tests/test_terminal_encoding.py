"""The Quick Start must not depend on the reader's terminal encoding.

Every render opens with a 55-character `─` divider and goes on to print emoji, so
on a stdout that is not UTF-8 (a Windows console under cp1252, or any redirected
stream) `coin bitcoin` used to answer with a UnicodeEncodeError traceback before
one useful line reached the screen. The README's answer was to ask the reader to
export PYTHONIOENCODING, which is a footnote standing between a clone and the
product. These tests pin the repair that removed that footnote.
"""

import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from display.terminal import _force_utf8_output

_DIVIDER = "─" * 55


def _cp1252_stream() -> io.TextIOWrapper:
    return io.TextIOWrapper(io.BytesIO(), encoding="cp1252")


class TestWhyTheRepairExists:
    def test_the_divider_kills_an_unrepaired_stream(self) -> None:
        """The exact failure a Windows reader hit on the very first command."""
        stream = _cp1252_stream()

        with pytest.raises(UnicodeEncodeError):
            stream.write(_DIVIDER)
            stream.flush()


class TestTheRepair:
    def test_a_cp1252_stdout_becomes_utf8(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "stdout", _cp1252_stream())
        monkeypatch.setattr(sys, "stderr", _cp1252_stream())

        _force_utf8_output()

        assert sys.stdout.encoding.lower() == "utf-8"
        assert sys.stderr.encoding.lower() == "utf-8"

    def test_the_divider_then_survives(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "stdout", _cp1252_stream())

        _force_utf8_output()

        sys.stdout.write(_DIVIDER)
        sys.stdout.flush()  # no UnicodeEncodeError

    def test_emoji_survive_too(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The audit block leans on 🔒 and ✂️ to make its point."""
        monkeypatch.setattr(sys, "stdout", _cp1252_stream())

        _force_utf8_output()

        sys.stdout.write("🔒 ✂️ ⚠ →")
        sys.stdout.flush()


class TestTheRepairIsSafe:
    def test_a_stream_without_reconfigure_is_left_alone(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """pytest's own capture and StringIO are not reconfigurable text streams."""
        monkeypatch.setattr(sys, "stdout", io.StringIO())
        monkeypatch.setattr(sys, "stderr", io.StringIO())

        _force_utf8_output()  # must not raise

    def test_a_stream_that_refuses_reconfigure_is_survived(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A detached or closed stream raises on reconfigure. Not our problem to die on."""

        class Hostile:
            encoding = "cp1252"

            def reconfigure(self, **_: object) -> None:
                raise ValueError("underlying buffer has been detached")

        monkeypatch.setattr(sys, "stdout", Hostile())
        monkeypatch.setattr(sys, "stderr", Hostile())

        _force_utf8_output()  # must not raise

    def test_an_already_utf8_stream_stays_utf8(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
        )

        _force_utf8_output()

        assert sys.stdout.encoding.lower() == "utf-8"
