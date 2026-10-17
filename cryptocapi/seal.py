"""Recompute a Radar `process_seal` from the response that carries it.

The CLI used to print the seal under a green check without ever checking it: no
line of the agent hashed anything, only the tests and the README recipe did. So
when the engine changed how it seals numbers (2026-09-01), the screen kept its
check for six weeks while the recipe printed False. This is the README recipe,
run by the agent on every response it shows.

What a match proves is narrow, and the caller should say so: the response is
internally consistent, the one that was sealed. The digest is unkeyed, so it
says nothing about who sealed it (see "What the seal does and does not prove").
"""

import hashlib
import json
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
_LATEST_RULE = "fixed6"


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
        return format(value + 0.0, ".6f")
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in value.items()}
    return value


def _digest(payload: dict[str, object], rule: str) -> str:
    body = _canonical(payload) if rule == "fixed6" else payload
    serialized = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "0x" + hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def check_seal(data: InsightData) -> SealCheck:
    """Recompute the seal from the eight fields it covers and compare.

    MISMATCH is only ever said for an engine version whose rule is known. For a
    newer one, agreement with the latest rule still verifies, but disagreement
    means the rule may have changed again, so the answer is UNCHECKED: telling
    the reader a response was tampered with, when it was the agent that fell
    behind, would be the agent hallucinating.
    """
    math = data.get("math_diagnostics")
    trail = math.get("audit_trail") if math else None
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

    expected = trail.get("protocol_hash", "")
    version = trail["engine_version"]
    rule = _RULES.get(version)

    if rule is not None:
        if _digest(payload, rule) == expected:
            return SealCheck(SealStatus.VERIFIED)
        return SealCheck(SealStatus.MISMATCH, f"recomputed with the {version} rule, the hash differs")

    if _digest(payload, _LATEST_RULE) == expected:
        return SealCheck(SealStatus.VERIFIED)
    return SealCheck(
        SealStatus.UNCHECKED,
        f"engine {version} is newer than this agent knows, and its seal rule may have changed",
    )
