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

    def test_missing_verdict_is_unavailable_instead_of_no_anomaly(self) -> None:
        data = _insight(z_score=2.0, anomaly=False)
        del data["statistical_anomaly_detected"]
        out = _render(data)
        assert "anomaly verdict unavailable" in out
        assert "no anomaly" not in out

    def test_missing_sentiment_is_not_fabricated_as_neutral(self) -> None:
        data = _insight(z_score=2.0, anomaly=False)
        del data["sentiment"]

        out = _render(data)

        line = next(line for line in out.splitlines() if "SENTIMENT:" in line)
        assert "unavailable" in line
        assert "neutral" not in line

    def test_a_missing_confidence_score_is_not_fabricated_as_zero(self) -> None:
        data = _insight(z_score=2.0, anomaly=False)
        data["confidence"] = {"label": "HIGH"}  # type: ignore[typeddict-item]

        out = _render(data)

        assert "HIGH (—)" in out
        assert "0.00" not in out

    def test_nonfinite_and_boolean_metrics_are_not_printed_as_measurements(self) -> None:
        data = _insight(z_score=float("nan"), anomaly=False)
        data["math_diagnostics"]["bollinger_bandwidth"] = float("inf")
        data["confidence"] = {"score": True, "label": "HIGH"}

        out = _render(data)

        assert "nan" not in out
        assert "inf (band width" not in out
        assert "HIGH (—)" in out

    def test_insufficient_quality_and_its_reason_reach_the_screen(self) -> None:
        data = _insight(z_score=2.0, anomaly=False)
        data["math_diagnostics"]["data_quality"] = "INSUFFICIENT"
        data["math_diagnostics"]["data_quality_reason"] = ["Too few observations"]

        out = _render(data)

        assert "DATA QUALITY:" in out
        assert "INSUFFICIENT" in out
        assert "Too few observations" in out

    def test_quant_insights_are_not_mislabeled_as_radar(self) -> None:
        data = _insight(z_score=2.0, anomaly=False)
        data["engine_used"] = "quant_plus"

        out = _render(data)

        assert "CRYPTOCAPI QUANT PLUS" in out
        assert "CRYPTOCAPI RADAR" not in out

    def test_a_missing_audit_trail_does_not_infer_a_subscription_or_view(self) -> None:
        out = _render(_insight(z_score=2.0, anomaly=False))

        assert "NO AUDIT TRAIL" in out
        assert "PULSE VIEW" not in out
        assert "free / no key" not in out
