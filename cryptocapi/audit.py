from dataclasses import dataclass, field

from .models import AuditTrail

_FILTER_EXPLANATIONS: dict[str, str] = {
    # Up to v2.3.0-radar it cut adjectives about volume; from v2.4.0 it cuts any
    # sentence that mentions it. Radar sees one 24h total and no trend, so it
    # cannot say volume is high, low or rising. Worded to hold for both.
    "LEY 7 volume": "Removed a volume claim: Radar has no volume trend to back it",
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
        "Hashes selected values and 4-layer pipeline metadata. "
        "Narrative, confidence, sources, timestamps and other diagnostics are not covered."
    ),
    "output_seal": (
        "The API labels this an output seal. "
        "This agent does not recompute its outputs or verify its coverage."
    ),
    "reproducible": (
        "The API labels this reproducible from an input_vector. "
        "This agent does not independently recompute that recipe."
    ),
}


def explain_filter(filter_name: str) -> str:
    if filter_name.startswith("band position"):
        # The engine emits "band position (CENTRO_BANDAS)"; without dropping the
        # parentheses the explanation printed "the price was at (CENTRO_BANDAS)".
        zone = filter_name.replace("band position", "").strip().strip("()").strip()
        return f"Removed a band-edge claim: the price was at {zone}"
    return _FILTER_EXPLANATIONS.get(filter_name, f"Filter applied: {filter_name}")


def explain_seal_type(seal_type: str) -> str:
    return _SEAL_TYPE_EXPLANATIONS.get(seal_type, seal_type)


_CORRECTION_REASONS: dict[str, str] = {
    "sentiment": "Python overrode the LLM's verdict (Z-Score rule)",
    "analysis.detailed_report": "the lexical filters rewrote the narrative",
    "summary": "LEY 7 cut a volume claim out of the summary",
}


def split_fields(
    fields_overridden: list[str], sentiment_override: bool, filters_applied: list[str]
) -> tuple[list[str], list[tuple[str, str]]]:
    """Interpret known ownership and correction entries reported by the API.

    Unknown fields and conditional entries without supporting metadata remain
    unclassified; neither is evidence that Python controls the field.
    """
    corrected: list[tuple[str, str]] = []
    if sentiment_override and "sentiment" in fields_overridden:
        corrected.append(("sentiment", _CORRECTION_REASONS["sentiment"]))
    if filters_applied and "analysis.detailed_report" in fields_overridden:
        corrected.append(
            ("analysis.detailed_report", _CORRECTION_REASONS["analysis.detailed_report"])
        )
    if "LEY 7 volume" in filters_applied and "summary" in fields_overridden:
        corrected.append(("summary", _CORRECTION_REASONS["summary"]))

    structural_fields = {
        "analysis.anomaly_details",
        "analysis.confidence",
        "analysis.sentiment_score",
        "confidence",
        "is_volatility_alert",
    }
    owned = list(dict.fromkeys(f for f in fields_overridden if f in structural_fields))
    return owned, corrected


@dataclass
class AuditSummary:
    is_pro: bool
    protocol_hash: str = ""
    calculated_at: str = ""
    seal_type: str = ""
    seal_explanation: str = ""
    algorithm_id: str = ""
    engine_version: str = ""
    filters: list[tuple[str, str]] = field(default_factory=list)
    fields_overridden: list[str] = field(default_factory=list)
    fields_owned: list[str] = field(default_factory=list)
    fields_corrected: list[tuple[str, str]] = field(default_factory=list)
    fields_unclassified: list[str] = field(default_factory=list)
    sentiment_override: bool = False


def parse_audit_trail(audit_trail: AuditTrail | None) -> AuditSummary:
    if not isinstance(audit_trail, dict) or not audit_trail:
        return AuditSummary(is_pro=False)

    def text(value: object) -> str:
        return value if isinstance(value, str) else ""

    def names(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return list(dict.fromkeys(item for item in value if isinstance(item, str) and item.strip()))

    seal_type = text(audit_trail.get("seal_type"))
    filters_raw = names(audit_trail.get("filters_applied"))
    fields_raw = names(audit_trail.get("fields_overridden"))
    sentiment_override = audit_trail.get("sentiment_override") is True

    owned, corrected = split_fields(fields_raw, sentiment_override, filters_raw)
    classified = set(owned) | {name for name, _ in corrected}

    return AuditSummary(
        is_pro=True,
        protocol_hash=text(audit_trail.get("protocol_hash")),
        # The engine's own stamp for when it computed this analysis. The renderer
        # shows it instead of the wall clock: the collector runs on a cron, so
        # "now" is the time of printing, never the age of the data.
        calculated_at=text(audit_trail.get("calculated_at")),
        seal_type=seal_type,
        seal_explanation=explain_seal_type(seal_type),
        algorithm_id=text(audit_trail.get("algorithm_id")),
        engine_version=text(audit_trail.get("engine_version")),
        filters=[(f, explain_filter(f)) for f in filters_raw],
        fields_overridden=fields_raw,
        fields_owned=owned,
        fields_corrected=corrected,
        fields_unclassified=[name for name in fields_raw if name not in classified],
        sentiment_override=sentiment_override,
    )
