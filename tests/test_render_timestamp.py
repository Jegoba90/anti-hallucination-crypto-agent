"""The header must date the analysis, not the printing of it.

The CLI used to put `datetime.now()` under the coin name. A reader takes that
line for the age of the data, and it never was: the collector runs on a cron, so
a response can be up to an hour old by the time it reaches the screen. That is
the display layer asserting a freshness nobody measured, in the one tool whose
thesis is that no claim ships without something behind it.

These tests pin the header to the engine's `calculated_at`, and pin the fallback
to saying so out loud when a response carries no stamp at all.
"""

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cryptocapi.models import InsightData
from display.terminal import console, render_insight

_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC")


def _render(data: InsightData) -> str:
    with console.capture() as capture:
        render_insight(data, "bitcoin")
    return capture.get()


def _load_fixture() -> InsightData:
    fixture_path = Path(__file__).parent / "fixtures" / "sample_response.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    return fixture["data"]


def _with_calculated_at(raw: str | None) -> InsightData:
    data = _load_fixture()
    trail = data["math_diagnostics"]["audit_trail"]
    if raw is None:
        trail.pop("calculated_at", None)
    else:
        trail["calculated_at"] = raw
    return data


class TestHeaderShowsTheAnalysisTime:
    def test_header_prints_calculated_at_not_the_wall_clock(self) -> None:
        out = _render(_load_fixture())

        # The fixture was computed on 2026-06-17. Whenever this suite runs, that
        # is the date that must appear.
        assert "Analysis computed 2026-06-17 23:19:21 UTC" in out

    def test_the_render_clock_never_reaches_the_screen(self) -> None:
        out = _render(_load_fixture())

        now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        printed = _TIMESTAMP.findall(out)
        assert printed, "the header lost its timestamp entirely"
        assert not any(stamp.startswith(now) for stamp in printed), (
            "the header is showing today's date, so it is dating the printing "
            "and not the analysis"
        )

    def test_a_fresh_analysis_is_reported_as_fresh(self) -> None:
        moment = datetime.now(tz=timezone.utc) - timedelta(minutes=41)
        out = _render(_with_calculated_at(moment.isoformat().replace("+00:00", "Z")))

        assert "41 min ago" in out

    def test_a_stale_analysis_shows_its_age(self) -> None:
        moment = datetime.now(tz=timezone.utc) - timedelta(days=3)
        out = _render(_with_calculated_at(moment.isoformat().replace("+00:00", "Z")))

        assert "3 d ago" in out


class TestHeaderNeverInventsATime:
    def test_missing_stamp_is_declared_not_replaced_by_now(self) -> None:
        out = _render(_with_calculated_at(None))

        assert "no analysis timestamp" in out
        assert "Analysis computed" not in out

    def test_pulse_view_without_audit_trail_does_not_crash(self) -> None:
        data = _load_fixture()
        del data["math_diagnostics"]["audit_trail"]

        out = _render(data)

        assert "no analysis timestamp" in out
        assert "PULSE VIEW" in out

    def test_unparseable_stamp_falls_back_instead_of_raising(self) -> None:
        out = _render(_with_calculated_at("last Tuesday"))

        assert "no analysis timestamp" in out

    def test_a_clock_ahead_of_ours_does_not_print_a_negative_age(self) -> None:
        """Engine clock ahead of this machine's is skew, not a future analysis."""
        moment = datetime.now(tz=timezone.utc) + timedelta(minutes=5)
        out = _render(_with_calculated_at(moment.isoformat().replace("+00:00", "Z")))

        assert "Analysis computed" in out
        # The stamp still prints; only the age is withheld, so the line carries
        # no parenthesised suffix at all.
        header_line = out.split("Analysis computed")[1].split("\n")[0]
        assert "ago" not in header_line
        assert "(" not in header_line

    def test_naive_stamp_is_read_as_utc_not_as_local_time(self) -> None:
        out = _render(_with_calculated_at("2026-06-17T23:19:21.370718"))

        assert "Analysis computed 2026-06-17 23:19:21 UTC" in out
