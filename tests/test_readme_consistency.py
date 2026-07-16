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


def _load_fixture_audit_trail() -> dict:
    fixture_path = Path(__file__).parent / "fixtures" / "sample_response.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    return fixture["data"]["math_diagnostics"]["audit_trail"]


def _block(heading: str, readme: str) -> tuple[int, str]:
    """Return the (N) count and the body of a heading, up to the next blank line.

    Entries in the README wrap onto continuation lines, so the body is everything
    until the block ends rather than only the lines carrying an icon.
    """
    match = re.search(rf"{heading} \((\d+)\):\n((?:.+\n)+)", readme)
    assert match is not None, f"README no longer has a '{heading}' block"
    return int(match.group(1)), match.group(2)


class TestReadmeOutputBlock:
    def test_owned_plus_corrected_match_the_fixture(self) -> None:
        """The block splits the sealed list in two. Nothing may be lost or invented."""
        readme = _load_readme()

        owned_count, owned_body = _block("Fields Python owns, never the LLM", readme)
        corrected_count, corrected_body = _block(
            "Corrections applied to the LLM's output", readme
        )

        owned = re.findall(r"🔒\s+(\S+)", owned_body)
        corrected = re.findall(r"✏️\s+(\S+)", corrected_body)
        expected = _load_fixture_audit_trail()["fields_overridden"]

        assert sorted(owned + corrected) == sorted(expected), (
            "the two blocks must partition exactly what the seal hashes"
        )
        assert owned_count == len(owned), "the (N) count contradicts the list"
        assert corrected_count == len(corrected), "the (N) count contradicts the list"

    def test_a_field_is_never_both_a_guarantee_and_a_catch(self) -> None:
        readme = _load_readme()

        owned = re.findall(r"🔒\s+(\S+)", _block("Fields Python owns, never the LLM", readme)[1])
        corrected = re.findall(
            r"✏️\s+(\S+)", _block("Corrections applied to the LLM's output", readme)[1]
        )

        assert not set(owned) & set(corrected)

    def test_filters_fired_count_matches_the_fixture(self) -> None:
        match = re.search(r"Filters fired \((\d+)\):", _load_readme())
        assert match is not None, "README no longer has a 'Filters fired' block"

        expected = _load_fixture_audit_trail()["filters_applied"]
        assert int(match.group(1)) == len(expected)

    def test_printed_hash_matches_the_fixture(self) -> None:
        match = re.search(r"Protocol hash \(SHA-256\):\n\s*(0x[0-9a-f]{64})", _load_readme())
        assert match is not None, "README no longer prints a protocol hash"

        assert match.group(1) == _load_fixture_audit_trail()["protocol_hash"]
