"""The anomaly verdict printed by the CLI must come from the engine.

The response carries both the number (`z_score`) and the verdict
(`statistical_anomaly_detected`, computed by the engine against its dynamic
`z_score_threshold`). The renderer once re-derived the verdict against a
hardcoded 3.0, so any z-score between 3.0 and the real threshold made the CLI
shout ANOMALY DETECTED while the engine said false: the display layer inventing
an anomaly, in the one tool whose thesis is that math has the last word. These
tests pin the display to the engine's verdict.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cryptocapi.models import InsightData
from display.terminal import console, render_insight


def _render(data: InsightData) -> str:
    with console.capture() as capture:
        render_insight(data, "bitcoin")
    return capture.get()


def _insight(z_score: float, anomaly: bool) -> InsightData:
    return {
        "asset": {"id": "bitcoin", "symbol": "BTC"},
        "sentiment": "neutral",
        "statistical_anomaly_detected": anomaly,
        "math_diagnostics": {
            "z_score": z_score,
            "z_score_threshold": 3.5051,
            "market_regime": "RANGING_CHOP",
        },
    }


class TestAnomalyVerdictComesFromTheEngine:
    def test_z_above_3_but_below_threshold_is_not_an_anomaly(self) -> None:
        # The exact divergence window of the old hardcoded >= 3.0 check.
        out = _render(_insight(z_score=3.2, anomaly=False))
        assert "no anomaly" in out
        assert "ANOMALY DETECTED" not in out

    def test_engine_verdict_true_is_displayed(self) -> None:
        out = _render(_insight(z_score=3.8, anomaly=True))
        assert "ANOMALY DETECTED" in out

    def test_missing_verdict_defaults_to_no_anomaly(self) -> None:
        data = _insight(z_score=2.0, anomaly=False)
        del data["statistical_anomaly_detected"]
        out = _render(data)
        assert "no anomaly" in out
