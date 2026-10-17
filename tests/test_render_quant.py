"""The Quant tables must name each asset and show the numbers the engine ranked by.

Identity lives under `asset` in a scan or batch row, and the renderers read it
from the top of the row, where it never is: every asset printed as an empty
name. The scan table also had a Score column fed by a `final_score` the API does
not send, so every asset scored 0, a number that looked measured and was not.
These tests put the live batch rows and the published scan example through the
renderers.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cryptocapi.models import ScanResult, SignalResult
from display.terminal import console, render_batch, render_scan

_API = Path(__file__).parent / "fixtures" / "api"


def _rows(name: str) -> list:
    return json.loads((_API / name).read_text(encoding="utf-8"))["data"]["results"]


def _render_batch(rows: list[SignalResult]) -> str:
    with console.capture() as capture:
        render_batch(rows)
    return capture.get()


def _render_scan(rows: list[ScanResult]) -> str:
    with console.capture() as capture:
        render_scan(rows, "aggressive")
    return capture.get()


class TestBatch:
    def test_each_row_is_named_from_its_asset(self) -> None:
        out = _render_batch(_rows("batch_btc_eth.json"))

        assert "Bitcoin (BTC)" in out
        assert "Ethereum (ETH)" in out

    def test_the_engines_signal_is_shown(self) -> None:
        rows = _rows("batch_btc_eth.json")

        out = _render_batch(rows)

        assert rows[0]["signal"] in out

    def test_a_symbol_without_a_signal_says_so_instead_of_crashing(self) -> None:
        """`available: false` comes with every signal field null."""
        row: SignalResult = {
            "asset": {"id": None, "symbol": "xyz"},
            "available": False,
            "signal": None,
            "sentiment": None,
            "confidence": None,
            "summary": None,
        }

        out = _render_batch([row])

        assert "XYZ" in out
        assert "no pre-computed signal" in out

    def test_a_summary_that_looks_like_markup_still_prints(self) -> None:
        row = _rows("batch_btc_eth.json")[0]
        row["summary"] = "[bold red] breakout"

        assert "[bold red] breakout" in _render_batch([row])


class TestScan:
    def test_each_row_is_named_from_its_asset(self) -> None:
        out = _render_scan(_rows("market_scan_openapi_example.json"))

        assert "Bitcoin (BTC)" in out
        assert "Zcash (ZEC)" in out

    def test_the_ranking_axes_are_shown(self) -> None:
        """threshold_proximity 0.3919 and evidence_weight 1 in the fixture."""
        out = _render_scan(_rows("market_scan_openapi_example.json"))

        assert "0.39" in out
        assert "1.00" in out

    def test_a_null_axis_is_a_gap_not_a_zero(self) -> None:
        row = _rows("market_scan_openapi_example.json")[0]
        row["threshold_proximity"] = None
        row["evidence_weight"] = None

        out = _render_scan([row])

        assert "0.00" not in out
        assert "—" in out
