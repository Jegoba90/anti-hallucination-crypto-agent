"""The Quant plan gate must reach the reader as an offer, not as an HTTP error.

`scan` and `batch` run on Quant Plus, which the public demo key does not cover,
so a 403 there is the single most common thing a new reader will hit after the
README tells them those commands need a key. It used to surface as a raw httpx
error carrying the internal URL and a link to MDN's 403 page, with no way to act
on it. Two things are pinned here: the API's own explanation survives the trip
from the response body to the screen, and the trial CTA is printed next to it.

No network and no key: the responses are built by hand, the way the API returns
them (verified against the live endpoint on 2026-07-16).
"""

import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cryptocapi.client import ProEngineRequired, _pro_plan_message
from display.terminal import console, render_pro_required

_LIVE_403_BODY = {
    "status": "error",
    "message": "Quantitative signals require a PRO plan subscription.",
}


def _render(message: str) -> str:
    with console.capture() as capture:
        render_pro_required(message)
    return capture.get()


class TestPlanMessageIsExtracted:
    def test_the_apis_own_explanation_is_returned(self) -> None:
        response = httpx.Response(403, json=_LIVE_403_BODY)

        assert _pro_plan_message(response) == (
            "Quantitative signals require a PRO plan subscription."
        )

    def test_401_is_treated_as_the_same_gate(self) -> None:
        response = httpx.Response(401, json={"message": "API key required."})

        assert _pro_plan_message(response) == "API key required."

    def test_a_success_is_never_mistaken_for_the_gate(self) -> None:
        response = httpx.Response(200, json={"data": []})

        assert _pro_plan_message(response) is None

    def test_a_body_that_is_not_json_does_not_explode(self) -> None:
        """A 403 from a proxy or gateway carries HTML, not our envelope."""
        response = httpx.Response(403, text="<html>Forbidden</html>")

        assert _pro_plan_message(response) is None

    def test_a_403_without_a_message_falls_through(self) -> None:
        """Nothing to say means the caller should raise the real HTTP error."""
        response = httpx.Response(403, json={"status": "error"})

        assert _pro_plan_message(response) is None


class TestBannerReachesTheScreen:
    def test_the_api_message_is_printed_verbatim(self) -> None:
        out = _render(_LIVE_403_BODY["message"])

        assert "Quantitative signals require a PRO plan subscription." in out

    def test_the_trial_cta_is_printed(self) -> None:
        """The gate fires exactly when the reader reached for a paid engine."""
        out = _render(_LIVE_403_BODY["message"])

        assert "Free 14-day trial" in out
        assert "https://cryptocapi.com" in out

    def test_no_raw_http_noise_survives(self) -> None:
        """What the old path leaked: the internal URL and MDN's 403 page."""
        out = _render(_LIVE_403_BODY["message"])

        assert "403 Forbidden" not in out
        assert "developer.mozilla.org" not in out
        assert "api.cryptocapi.com" not in out

    def test_a_message_that_looks_like_rich_markup_still_prints(self) -> None:
        """Same trap as the filter names: [bold red] is valid markup, not text."""
        out = _render("[bold red] plan required")

        assert "[bold red] plan required" in out


class TestExceptionCarriesTheMessage:
    def test_user_message_is_what_the_api_said(self) -> None:
        exc = ProEngineRequired("Quantitative signals require a PRO plan subscription.")

        assert exc.user_message == (
            "Quantitative signals require a PRO plan subscription."
        )

    def test_it_is_catchable_as_an_exception(self) -> None:
        with pytest.raises(ProEngineRequired):
            raise ProEngineRequired("nope")
