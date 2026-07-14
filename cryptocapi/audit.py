from dataclasses import dataclass, field

from .models import AuditTrail

_FILTER_EXPLANATIONS: dict[str, str] = {
    "LEY 7 volume": "Removed a qualitative volume claim: the system has no volume data",
    "magnitude inflation": "Removed an inflated adjective: the Z-Score was too low to justify it",
    "certainty inflation": "Removed a certainty marker: sentiment was neutral or confidence too low",
}

_FIELD_EXPLANATIONS: dict[str, str] = {
    "confidence": "how sure the call is. Derived from the math, never from how assertive the AI sounded",
    "is_volatility_alert": "the volatility flag. Raised by the Bollinger bandwidth alone",
    "sentiment": "bullish, bearish or neutral. The Z-Score rule can overrule the AI here",
    "analysis.sentiment_score": "the numeric sentiment inside the report, computed from the Z-Score",
    "analysis.confidence": "the HIGH / MEDIUM / LOW label, derived from the score, not from the AI's wording",
    "analysis.anomaly_details": "the anomaly description. Written from the Z-Score or left empty. The AI cannot invent one",
    "analysis.detailed_report": "the narrative itself. The lexical filters can cut sentences out of it",
}


def explain_field(field_name: str) -> str:
    """Say what a field is, in words a reader who has never seen the API can use.

    Raw keys like `analysis.sentiment_score` are internal names: printed bare they
    tell a reader nothing, which wastes the strongest claim the audit trail makes.
    Spelled out, the same list reads as what it is: the things the LLM is never
    allowed to decide.
    """
    return _FIELD_EXPLANATIONS.get(field_name, "")


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
        return f"Removed a band-edge claim: the price was at {zone}"
    return _FILTER_EXPLANATIONS.get(filter_name, f"Filter applied: {filter_name}")


def explain_seal_type(seal_type: str) -> str:
    return _SEAL_TYPE_EXPLANATIONS.get(seal_type, seal_type)


_CORRECTION_REASONS: dict[str, str] = {
    "sentiment": "Python overrode the LLM's verdict (Z-Score rule)",
    "analysis.detailed_report": "the lexical filters rewrote the narrative",
}


def split_fields(
    fields_overridden: list[str], sentiment_override: bool, filters_applied: list[str]
) -> tuple[list[str], list[tuple[str, str]]]:
    """Split `fields_overridden` into fields Python *owns* and fields it *corrected*.

    The two are not the same thing, and lumping them together overstates the case.
    Most entries are structural: Python writes them on every single response, so the
    LLM never gets a say, whether or not it was about to say something wrong. Only
    two entries are conditional, and those are the real catches: `sentiment` appears
    only when the Z-Score rule overrode the LLM's verdict, and
    `analysis.detailed_report` only when a lexical filter cut text out of it.

    The split is derived from the trail itself (`sentiment_override` and
    `filters_applied` are exactly the conditions that add those two entries), so this
    does not hardcode a copy of the engine's list. Anything unrecognised is reported
    as owned, which is the conservative side: it claims a guarantee, not a catch.
    """
    corrected: list[tuple[str, str]] = []
    if sentiment_override and "sentiment" in fields_overridden:
        corrected.append(("sentiment", _CORRECTION_REASONS["sentiment"]))
    if filters_applied and "analysis.detailed_report" in fields_overridden:
        corrected.append(
            ("analysis.detailed_report", _CORRECTION_REASONS["analysis.detailed_report"])
        )

    corrected_names = {name for name, _ in corrected}
    owned = [f for f in fields_overridden if f not in corrected_names]
    return owned, corrected


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
    fields_owned: list[str] = field(default_factory=list)
    fields_corrected: list[tuple[str, str]] = field(default_factory=list)
    sentiment_override: bool = False


def parse_audit_trail(audit_trail: AuditTrail | None) -> AuditSummary:
    if not audit_trail:
        return AuditSummary(is_pro=False)

    seal_type = audit_trail.get("seal_type", "")
    filters_raw = audit_trail.get("filters_applied", [])
    fields_raw = audit_trail.get("fields_overridden", [])
    sentiment_override = audit_trail.get("sentiment_override", False)

    owned, corrected = split_fields(fields_raw, sentiment_override, filters_raw)

    return AuditSummary(
        is_pro=True,
        protocol_hash=audit_trail.get("protocol_hash", ""),
        seal_type=seal_type,
        seal_explanation=explain_seal_type(seal_type),
        algorithm_id=audit_trail.get("algorithm_id", ""),
        engine_version=audit_trail.get("engine_version", ""),
        filters=[(f, explain_filter(f)) for f in filters_raw],
        fields_overridden=fields_raw,
        fields_owned=owned,
        fields_corrected=corrected,
        sentiment_override=sentiment_override,
    )
