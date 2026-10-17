"""Tests for the audit trail parser."""

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cryptocapi.audit import (
    explain_filter,
    explain_seal_type,
    parse_audit_trail,
    split_fields,
)
from cryptocapi.models import AuditTrail


def _load_fixture() -> dict:
    fixture_path = Path(__file__).parent / "fixtures" / "radar_alpha_v2.2.0.json"
    return json.loads(fixture_path.read_text())


class TestParseAuditTrail:
    def test_returns_pro_summary_from_fixture(self) -> None:
        fixture = _load_fixture()
        audit_trail: AuditTrail = fixture["data"]["math_diagnostics"]["audit_trail"]
        summary = parse_audit_trail(audit_trail)

        assert summary.is_pro is True
        assert summary.seal_type == "process_seal"
        assert summary.algorithm_id == "Radar 4-Layer Anti-Hallucination Pipeline"
        assert summary.engine_version == "v2.2.0-radar"
        assert summary.sentiment_override is False

    def test_filters_parsed_correctly(self) -> None:
        fixture = _load_fixture()
        audit_trail: AuditTrail = fixture["data"]["math_diagnostics"]["audit_trail"]
        summary = parse_audit_trail(audit_trail)

        assert [name for name, _ in summary.filters] == ["LEY 7 volume"]
        assert all(explanation for _, explanation in summary.filters)

    def test_fields_overridden_present(self) -> None:
        fixture = _load_fixture()
        audit_trail: AuditTrail = fixture["data"]["math_diagnostics"]["audit_trail"]
        summary = parse_audit_trail(audit_trail)

        assert "confidence" in summary.fields_overridden
        assert "analysis.detailed_report" in summary.fields_overridden

    def test_the_one_catch_in_the_real_seal_is_the_report(self) -> None:
        """Five fields Python always owns, and one the filter actually rewrote."""
        fixture = _load_fixture()
        audit_trail: AuditTrail = fixture["data"]["math_diagnostics"]["audit_trail"]
        summary = parse_audit_trail(audit_trail)

        assert [name for name, _ in summary.fields_corrected] == ["analysis.detailed_report"]
        assert len(summary.fields_owned) == 5

    def test_protocol_hash_correct(self) -> None:
        fixture = _load_fixture()
        audit_trail: AuditTrail = fixture["data"]["math_diagnostics"]["audit_trail"]
        summary = parse_audit_trail(audit_trail)

        assert summary.protocol_hash.startswith("0x")
        assert len(summary.protocol_hash) == 66  # "0x" + 64 hex chars (SHA-256)

    def test_none_returns_non_pro_summary(self) -> None:
        summary = parse_audit_trail(None)
        assert summary.is_pro is False
        assert summary.protocol_hash == ""
        assert summary.filters == []

    def test_empty_dict_returns_non_pro_summary(self) -> None:
        summary = parse_audit_trail({})
        assert summary.is_pro is False


class TestSplitFields:
    """A guarantee and a catch are different claims. The audit must not conflate them."""

    _BASE = [
        "analysis.anomaly_details",
        "analysis.confidence",
        "analysis.sentiment_score",
        "confidence",
        "is_volatility_alert",
    ]

    def test_quiet_response_has_no_corrections(self) -> None:
        owned, corrected = split_fields(self._BASE, sentiment_override=False, filters_applied=[])

        assert owned == self._BASE
        assert corrected == []

    def test_sentiment_is_a_correction_only_when_overridden(self) -> None:
        fields = self._BASE + ["sentiment"]
        owned, corrected = split_fields(fields, sentiment_override=True, filters_applied=[])

        assert [name for name, _ in corrected] == ["sentiment"]
        assert "sentiment" not in owned

    def test_report_is_a_correction_only_when_filters_fired(self) -> None:
        fields = self._BASE + ["analysis.detailed_report"]
        owned, corrected = split_fields(
            fields, sentiment_override=False, filters_applied=["LEY 7 volume"]
        )

        assert [name for name, _ in corrected] == ["analysis.detailed_report"]
        assert "analysis.detailed_report" not in owned

    def test_summary_is_a_correction_never_a_guarantee(self) -> None:
        """Since v2.4.0-radar, LEY 7 also cuts volume claims out of the summary.

        The LLM writes the summary, so listing it as a field Python owns would
        claim a guarantee that does not exist.
        """
        fields = self._BASE + ["summary"]
        owned, corrected = split_fields(
            fields, sentiment_override=False, filters_applied=["LEY 7 volume"]
        )

        assert [name for name, _ in corrected] == ["summary"]
        assert "summary" not in owned

    def test_split_is_a_partition_of_the_sealed_list(self) -> None:
        fixture = _load_fixture()
        trail = fixture["data"]["math_diagnostics"]["audit_trail"]
        summary = parse_audit_trail(trail)

        assert sorted(summary.fields_owned + [n for n, _ in summary.fields_corrected]) == sorted(
            trail["fields_overridden"]
        )
        assert not set(summary.fields_owned) & {n for n, _ in summary.fields_corrected}

    def test_unknown_field_is_reported_as_owned_not_as_a_catch(self) -> None:
        owned, corrected = split_fields(
            ["some.future.field"], sentiment_override=False, filters_applied=[]
        )

        assert owned == ["some.future.field"]
        assert corrected == []


class TestExplainFilter:
    def test_ley7_volume(self) -> None:
        explanation = explain_filter("LEY 7 volume")
        assert "volume" in explanation.lower()

    def test_magnitude_inflation(self) -> None:
        explanation = explain_filter("magnitude inflation")
        assert "Z-Score" in explanation

    def test_certainty_inflation(self) -> None:
        explanation = explain_filter("certainty inflation")
        assert "certainty" in explanation.lower() or "neutral" in explanation.lower()

    def test_band_position_includes_zone(self) -> None:
        explanation = explain_filter("band position CENTRO_BANDAS")
        assert "CENTRO_BANDAS" in explanation

    def test_band_position_upper(self) -> None:
        explanation = explain_filter("band position CERCA_BANDA_SUPERIOR")
        assert "CERCA_BANDA_SUPERIOR" in explanation

    def test_band_position_as_the_engine_emits_it(self) -> None:
        """insights_common.py writes the zone in parentheses."""
        explanation = explain_filter("band position (CENTRO_BANDAS)")
        assert explanation.endswith("the price was at CENTRO_BANDAS")

    def test_unknown_filter_passthrough(self) -> None:
        explanation = explain_filter("some_unknown_filter")
        assert "some_unknown_filter" in explanation


class TestExplainSealType:
    def test_process_seal(self) -> None:
        explanation = explain_seal_type("process_seal")
        assert "4-layer" in explanation.lower() or "pipeline" in explanation.lower()

    def test_reproducible(self) -> None:
        explanation = explain_seal_type("reproducible")
        assert "reproducible" in explanation.lower() or "input_vector" in explanation.lower()

    def test_output_seal(self) -> None:
        explanation = explain_seal_type("output_seal")
        assert "tamper" in explanation.lower() or "outputs" in explanation.lower()

    def test_unknown_seal_type_passthrough(self) -> None:
        assert explain_seal_type("mystery_seal") == "mystery_seal"


class TestVerifyHashFormat:
    """The protocol_hash must be a valid SHA-256 hex digest with 0x prefix."""

    def test_hash_is_64_hex_chars_after_prefix(self) -> None:
        fixture = _load_fixture()
        hash_value: str = fixture["data"]["math_diagnostics"]["audit_trail"]["protocol_hash"]
        assert hash_value.startswith("0x")
        hex_part = hash_value[2:]
        assert len(hex_part) == 64
        assert all(c in "0123456789abcdef" for c in hex_part)


class TestHashReproducibility:
    """Reproduce the protocol_hash of a real, engine-issued seal like a third
    party would: z_score/market_regime from math_diagnostics, sentiment from the
    root, filters and fields from the audit_trail.

    The fixture is a production response (2026-09-03, `v2.2.0-radar`), so this
    checks the engine, not our own arithmetic. An earlier fixture was written for
    the README and its hash computed with the same recipe; it could never notice
    the engine sealing another way, and the 2026-09-01 rule change went unseen
    for six weeks. The README's two recipes run as written in test_seal_recipe.py.
    """

    def test_recomputed_hash_matches_the_engines_seal(self) -> None:
        fixture = _load_fixture()
        data = fixture["data"]
        math = data["math_diagnostics"]
        trail = math["audit_trail"]

        payload = {
            "algorithm_id": trail["algorithm_id"],
            "engine_version": trail["engine_version"],
            # From v2.2.0-radar every number is sealed as a 6-decimal string.
            "z_score": format(math["z_score"], ".6f"),
            "market_regime": math["market_regime"],
            "sentiment": data["sentiment"],
            "sentiment_override": trail["sentiment_override"],
            "filters_applied": trail["filters_applied"],
            "fields_overridden": trail["fields_overridden"],
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        recomputed = "0x" + hashlib.sha256(serialized.encode()).hexdigest()

        assert trail["engine_version"] == "v2.2.0-radar"
        assert recomputed == trail["protocol_hash"]
