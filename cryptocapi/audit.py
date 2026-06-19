from dataclasses import dataclass, field

from .models import AuditTrail

_FILTER_EXPLANATIONS: dict[str, str] = {
    "LEY 7 volume": "Removed qualitative volume claim — system has no actual volume data",
    "magnitude inflation": "Removed inflated adjective — Z-Score was too low to justify it",
    "certainty inflation": "Removed certainty marker — sentiment was neutral or confidence too low",
}

_SEAL_TYPE_EXPLANATIONS: dict[str, str] = {
    "process_seal": (
        "Certifies the 4-layer pipeline ran with these exact corrections. "
        "Text is not reproducible (LLM is non-deterministic by design)."
    ),
    "output_seal": (
        "Certifies outputs were not tampered. "
        "Re-fetchable from Binance candles to reproduce."
    ),
    "reproducible": (
        "Fully reproducible — recompute from the embedded input_vector "
        "to get the exact same hash independently."
    ),
}


def explain_filter(filter_name: str) -> str:
    if filter_name.startswith("band position"):
        zone = filter_name.replace("band position", "").strip()
        return f"Removed band-edge claim — price was at {zone}, contradicting the LLM's assertion"
    return _FILTER_EXPLANATIONS.get(filter_name, f"Filter applied: {filter_name}")


def explain_seal_type(seal_type: str) -> str:
    return _SEAL_TYPE_EXPLANATIONS.get(seal_type, seal_type)


@dataclass
class AuditSummary:
    is_pro: bool
    protocol_hash: str = ""
    seal_type: str = ""
    seal_explanation: str = ""
    algorithm_id: str = ""
    engine_version: str = ""
    filters: list[tuple[str, str]] = field(default_factory=list)
    fields_overridden: list[str] = field(default_factory=list)
    sentiment_override: bool = False


def parse_audit_trail(audit_trail: AuditTrail | None) -> AuditSummary:
    if not audit_trail:
        return AuditSummary(is_pro=False)

    seal_type = audit_trail.get("seal_type", "")
    filters_raw = audit_trail.get("filters_applied", [])

    return AuditSummary(
        is_pro=True,
        protocol_hash=audit_trail.get("protocol_hash", ""),
        seal_type=seal_type,
        seal_explanation=explain_seal_type(seal_type),
        algorithm_id=audit_trail.get("algorithm_id", ""),
        engine_version=audit_trail.get("engine_version", ""),
        filters=[(f, explain_filter(f)) for f in filters_raw],
        fields_overridden=audit_trail.get("fields_overridden", []),
        sentiment_override=audit_trail.get("sentiment_override", False),
    )
