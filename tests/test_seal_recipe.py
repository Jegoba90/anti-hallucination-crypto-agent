"""The README's live recipe must verify real seals, run exactly as it is written.

On 2026-09-01 the engine started sealing every number as a 6-decimal string
(`v2.2.0-radar`), and the README kept teaching the old serialization. For six
weeks its "Now do it on a live response" recipe printed False on every response
the API served, while the suite stayed green: the hash test in
test_audit_parser.py checks its own copy of the recipe against a `v2.1.0-radar`
fixture, so a change in the README or in the API could reach neither.

This closes both gaps. It makes the dump the way the README says to, with
`coin --json` (fed a captured response instead of the network), then runs the
README's own code block, not a copy of it, on that dump. It does so for a seal
on each side of the rule change, and both are seals the engine issued: the
README's own example fixture is illustrative, its hash computed from it, so a
recipe run on it could only ever agree with itself.
"""

import contextlib
import io
import re
import sys
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agent
from cryptocapi import CryptoCapiClient

_TESTS = Path(__file__).parent
_README = _TESTS.parent / "README.md"


def _live_recipe() -> str:
    readme = _README.read_text(encoding="utf-8")
    section = re.search(r"### Now do it on a live response\n(.*?)\n### ", readme, re.S)
    assert section is not None, "README no longer has the live-response section"
    code = re.search(r"```python\n(.*?)```", section.group(1), re.S)
    assert code is not None, "the live-response section no longer has a Python block"
    return code.group(1)


def _dump_with_the_cli(monkeypatch: pytest.MonkeyPatch, capture: Path) -> str:
    """What `python agent.py coin bitcoin --json > btc.json` writes for this capture."""
    body = capture.read_bytes()
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, content=body, headers={"content-type": "application/json"}
        )
    )
    monkeypatch.setattr(
        agent,
        "_get_client",
        lambda: CryptoCapiClient("demo_btc_eth_public", transport=transport),
    )
    result = CliRunner().invoke(agent.app, ["coin", "bitcoin", "--json"])
    assert result.exit_code == 0, result.output
    return result.output


@pytest.mark.parametrize(
    ("capture", "version"),
    [
        (_TESTS.parent / "docs" / "comparisons" / "2026-07-20-btc" / "radar.json", "v2.1.0-radar"),
        (_TESTS / "fixtures" / "api" / "insight_bitcoin_alpha.json", "v2.4.0-radar"),
    ],
)
def test_the_readme_recipe_verifies_the_seal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capture: Path, version: str
) -> None:
    dump = _dump_with_the_cli(monkeypatch, capture)
    assert f'"engine_version": "{version}"' in dump, "this capture is not the version it covers"
    (tmp_path / "btc.json").write_text(dump, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(_live_recipe(), {})

    assert out.getvalue().strip() == "True"
