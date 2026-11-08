"""Compare eight Radar process-seal fields with their unkeyed SHA-256 digest.

A match checks only those fields under a known recipe. It cannot authenticate
the issuer, validate the market inputs, or check the unsealed narrative,
confidence, sources, timestamps and remaining diagnostics.
"""

import hashlib
import json
import math
import re
from dataclasses import dataclass
from enum import Enum

from .models import InsightData

# How each engine version writes numbers before hashing: v2.1.0 hashed them as
# they were, and from v2.2.0 every number is a string with exactly 6 decimals
# (SEAL.md, "Version boundary"). v2.1.0, v2.2.0 and v2.4.0 are checked against
# real seals in the tests; v2.3.0 follows the same documented rule.
_RULES: dict[str, str] = {
    "v2.1.0-radar": "plain",
    "v2.2.0-radar": "fixed6",
    "v2.3.0-radar": "fixed6",
    "v2.4.0-radar": "fixed6",
}
_RADAR_ALGORITHM = "Radar 4-Layer Anti-Hallucination Pipeline"


class SealStatus(Enum):
    VERIFIED = "verified"
    MISMATCH = "mismatch"
    UNCHECKED = "unchecked"


@dataclass(frozen=True)
class SealCheck:
    status: SealStatus
    reason: str = ""


def _canonical(value: object) -> object:
    """Every number as a 6-decimal string, as the engine's utils/seal.py does.

    bool first, because it is an int in Python. `+ 0.0` turns -0.0 into 0.0,
    which the engine also does. format() rounds half to even, like the engine.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        try:
            finite = math.isfinite(value)
        except OverflowError as exc:
            raise ValueError("number cannot be represented by the seal recipe") from exc
        if not finite:
            raise ValueError("non-finite numbers cannot be sealed")
        return format(value + 0.0, ".6f")
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in value.items()}
    return value


def _digest(payload: dict[str, object], rule: str) -> str:
    if rule not in {"plain", "fixed6"}:
        raise ValueError(f"unknown seal rule: {rule}")
    body = _canonical(payload) if rule == "fixed6" else payload
    serialized = json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    )
    return "0x" + hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def check_seal(data: InsightData) -> SealCheck:
    """Compare a well-formed seal only when its algorithm and version are known."""
    if not isinstance(data, dict):
        return SealCheck(SealStatus.UNCHECKED, "the response is not an object")
    math = data.get("math_diagnostics")
    if not isinstance(math, dict):
        return SealCheck(SealStatus.UNCHECKED, "this response carries no valid math diagnostics")
    trail = math.get("audit_trail")
    if not isinstance(trail, dict):
        return SealCheck(SealStatus.UNCHECKED, "this response carries no valid audit trail")
    if not math or not trail:
        return SealCheck(SealStatus.UNCHECKED, "this response carries no seal")

    seal_type = trail.get("seal_type", "")
    if seal_type != "process_seal":
        return SealCheck(SealStatus.UNCHECKED, f"seal type {seal_type!r} is not one this agent recomputes")

    try:
        payload: dict[str, object] = {
            "algorithm_id": trail["algorithm_id"],
            "engine_version": trail["engine_version"],
            "z_score": math["z_score"],
            "market_regime": math["market_regime"],
            "sentiment": data["sentiment"],
            "sentiment_override": trail["sentiment_override"],
            "filters_applied": trail["filters_applied"],
            "fields_overridden": trail["fields_overridden"],
        }
    except KeyError as missing:
        return SealCheck(
            SealStatus.UNCHECKED, f"the response lacks {missing.args[0]}, one of the sealed fields"
        )

    for name in ("algorithm_id", "engine_version", "market_regime", "sentiment"):
        value = payload[name]
        if not isinstance(value, str) or not value.strip():
            return SealCheck(SealStatus.UNCHECKED, f"sealed field {name} is not a non-empty string")
    z_score = payload["z_score"]
    if isinstance(z_score, bool) or not isinstance(z_score, (int, float)):
        return SealCheck(SealStatus.UNCHECKED, "sealed field z_score is not a finite number")
    try:
        _canonical(z_score)
    except ValueError:
        return SealCheck(SealStatus.UNCHECKED, "sealed field z_score is not a finite number")
    if not isinstance(payload["sentiment_override"], bool):
        return SealCheck(SealStatus.UNCHECKED, "sealed field sentiment_override is not a boolean")
    for name in ("filters_applied", "fields_overridden"):
        value = payload[name]
        if not isinstance(value, list) or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            return SealCheck(SealStatus.UNCHECKED, f"sealed field {name} is not a list of strings")

    expected = trail.get("protocol_hash", "")
    if not isinstance(expected, str) or re.fullmatch(r"0x[0-9a-f]{64}", expected) is None:
        return SealCheck(SealStatus.UNCHECKED, "protocol_hash is not a SHA-256 digest with 0x prefix")
    if trail["algorithm_id"] != _RADAR_ALGORITHM:
        return SealCheck(SealStatus.UNCHECKED, "the process-seal algorithm is not supported")
    if data.get("engine_used", "radar") != "radar":
        return SealCheck(SealStatus.UNCHECKED, "the response is not from the Radar engine")
    version = trail["engine_version"]
    rule = _RULES.get(version)

    if rule is not None:
        if _digest(payload, rule) == expected:
            return SealCheck(SealStatus.VERIFIED)
        return SealCheck(SealStatus.MISMATCH, f"recomputed with the {version} rule, the hash differs")

    return SealCheck(
        SealStatus.UNCHECKED,
        f"engine {version} has no supported seal recipe in this agent",
    )
