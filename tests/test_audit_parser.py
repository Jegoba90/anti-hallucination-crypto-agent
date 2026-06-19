"""Tests for the audit trail parser."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cryptocapi.audit import AuditSummary, explain_filter, explain_seal_type, parse_audit_trail
from cryptocapi.models import AuditTrail


def _load_fixture() -> dict:  # type: ignore[type-arg]
    fixture_path = Path(__file__).parent / "fixtures" / "sample_response.json"
    return json.loads(fixture_path.read_text())


class TestParseAuditTrail:
    def test_returns_pro_summary_from_fixture(self) -> None:
        fixture = _load_fixture()
        audit_trail: AuditTrail = fixture["data"]["math_diagnostics"]["audit_trail"]
        summary = parse_audit_trail(audit_trail)

        assert summary.is_pro is True
        assert summary.seal_type == "process_seal"
        assert summary.algorithm_id == "Radar 4-Layer Anti-Hallucination Pipeline"
        assert summary.engine_version == "v2.1.0-radar"
        assert summary.sentiment_override is True

    def test_filters_parsed_correctly(self) -> None:
        fixture = _load_fixture()
        audit_trail: AuditTrail = fixture["data"]["math_diagnostics"]["audit_trail"]
        summary = parse_audit_trail(audit_trail)

        assert len(summary.filters) == 2
        filter_names = [f[0] for f in summary.filters]
        assert "LEY 7 volume" in filter_names
        assert "band position CENTRO_BANDAS" in filter_names

    def test_fields_overridden_present(self) -> None:
        fixture = _load_fixture()
        audit_trail: AuditTrail = fixture["data"]["math_diagnostics"]["audit_trail"]
        summary = parse_audit_trail(audit_trail)

        assert "confidence" in summary.fields_overridden
        assert "sentiment" in summary.fields_overridden

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
        summary = parse_audit_trail({})  # type: ignore[arg-type]
        assert summary.is_pro is False


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
