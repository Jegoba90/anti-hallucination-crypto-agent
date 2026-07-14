"""Guards the README's example output against silent drift.

The `Output` block in the README prints a `protocol_hash` next to a list of
`fields_overridden`. Those two must belong to the same response: the hash is a
digest *of* that list (among other fields), so if the block is edited and the
list stops matching, the README stops passing its own verification, which is the
one thing this project promises. These tests pin that block to the fixture the
rest of the suite already hashes.
"""

import re
from pathlib import Path

import json

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_readme() -> str:
    return (_REPO_ROOT / "README.md").read_text(encoding="utf-8")


def _load_fixture_audit_trail() -> dict:  # type: ignore[type-arg]
    fixture_path = Path(__file__).parent / "fixtures" / "sample_response.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    return fixture["data"]["math_diagnostics"]["audit_trail"]


class TestReadmeOutputBlock:
    def test_fields_overridden_match_the_fixture(self) -> None:
        block = re.search(
            r"Fields overridden by Python \((\d+)\):\n((?:.*?🔒.*\n)+)", _load_readme()
        )
        assert block is not None, "README no longer has a 'Fields overridden by Python' block"

        documented = re.findall(r"🔒\s+(\S+)", block.group(2))
        expected = _load_fixture_audit_trail()["fields_overridden"]

        assert documented == expected
        assert int(block.group(1)) == len(expected), "the (N) count contradicts the list"

    def test_filters_fired_count_matches_the_fixture(self) -> None:
        match = re.search(r"Filters fired \((\d+)\):", _load_readme())
        assert match is not None, "README no longer has a 'Filters fired' block"

        expected = _load_fixture_audit_trail()["filters_applied"]
        assert int(match.group(1)) == len(expected)

    def test_printed_hash_matches_the_fixture(self) -> None:
        match = re.search(r"Protocol hash \(SHA-256\):\n\s*(0x[0-9a-f]{64})", _load_readme())
        assert match is not None, "README no longer prints a protocol hash"

        assert match.group(1) == _load_fixture_audit_trail()["protocol_hash"]
