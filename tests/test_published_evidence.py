"""The sealed responses published as evidence must still verify.

`docs/comparisons/` holds real API responses captured on a date and committed as
the evidence behind the README's comparison table. A reader who checks one and
finds the digest does not reproduce has been handed, by an anti-hallucination
project, exactly the thing it exists to catch.

The rest of the suite hashes `tests/fixtures/sample_response.json`. Nothing
covered the published captures, so an edit to one (a refreshed capture, a fixed
typo in a headline) would break the evidence in silence. These tests close that,
and they glob rather than name a file so the next comparison folder is covered
the day it lands.
"""

import hashlib
import json
import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_COMPARISONS = sorted((_REPO_ROOT / "docs" / "comparisons").glob("*/radar.json"))

# The README cites these digests truncated, e.g. `0x8f96020d…83fd059`.
_TRUNCATED_HASH = re.compile(r"0x([0-9a-f]+)…([0-9a-f]+)")


def _seal_payload(response: dict) -> dict:
    """Rebuild the eight sealed fields exactly as a third party would.

    Kept as its own function so the recipe under test is the one the README
    publishes, pulled from the response rather than from anything private.
    """
    data = response["data"]
    math = data["math_diagnostics"]
    trail = math["audit_trail"]
    return {
        "algorithm_id": trail["algorithm_id"],
        "engine_version": trail["engine_version"],
        "z_score": round(math["z_score"], 6),
        "market_regime": math["market_regime"],
        "sentiment": data["sentiment"],
        "sentiment_override": trail["sentiment_override"],
        "filters_applied": trail["filters_applied"],
        "fields_overridden": trail["fields_overridden"],
    }


def _digest(payload: dict) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "0x" + hashlib.sha256(serialized.encode()).hexdigest()


def test_there_is_published_evidence_to_check() -> None:
    """Guard the glob itself.

    A renamed or moved `docs/comparisons/` would leave every parametrised test
    below with zero cases and the suite would still pass, reporting green over
    an evidence set it never opened.
    """
    assert _COMPARISONS, "docs/comparisons/*/radar.json matched nothing"


@pytest.mark.parametrize("capture", _COMPARISONS, ids=lambda p: p.parent.name)
def test_published_capture_reproduces_its_seal(capture: Path) -> None:
    response = json.loads(capture.read_text(encoding="utf-8"))
    published = response["data"]["math_diagnostics"]["audit_trail"]["protocol_hash"]

    assert _digest(_seal_payload(response)) == published, (
        f"{capture.parent.name} no longer reproduces its own protocol_hash"
    )


@pytest.mark.parametrize("capture", _COMPARISONS, ids=lambda p: p.parent.name)
def test_capture_is_internally_consistent(capture: Path) -> None:
    """The narrative and the trail must describe the same run.

    A capture whose seal reproduces but whose `filters_applied` disagrees with
    what the report says was stripped would verify and still mislead.
    """
    response = json.loads(capture.read_text(encoding="utf-8"))
    data = response["data"]
    trail = data["math_diagnostics"]["audit_trail"]

    if trail["sentiment_override"]:
        assert "sentiment" in trail["fields_overridden"]
    if trail["filters_applied"]:
        assert "analysis.detailed_report" in trail["fields_overridden"]


def test_readme_quotes_a_hash_that_still_exists() -> None:
    """A refreshed capture must not leave the README quoting the old digest."""
    readme = (_REPO_ROOT / "README.md").read_text(encoding="utf-8")
    cited = _TRUNCATED_HASH.findall(readme)
    assert cited, "the README no longer cites a published capture's hash"

    published = [
        json.loads(c.read_text(encoding="utf-8"))["data"]["math_diagnostics"][
            "audit_trail"
        ]["protocol_hash"]
        for c in _COMPARISONS
    ]

    for prefix, suffix in cited:
        assert any(
            h.startswith("0x" + prefix) and h.endswith(suffix) for h in published
        ), f"the README cites 0x{prefix}…{suffix}, which no published capture carries"
