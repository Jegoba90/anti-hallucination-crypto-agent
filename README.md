![Anti-Hallucination Crypto Agent: AI crypto analysis checked by a deterministic math engine](assets/banner.svg)

> A Python agent that analyzes crypto markets using AI, and shows you exactly what a **deterministic math engine** corrected.

![Python](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Anti-Hallucination](https://img.shields.io/badge/Anti--Hallucination-verifiable%20seal-blueviolet?style=flat-square)
[![Tests](https://github.com/Jegoba90/anti-hallucination-crypto-agent/actions/workflows/tests.yml/badge.svg)](https://github.com/Jegoba90/anti-hallucination-crypto-agent/actions/workflows/tests.yml)

What `python agent.py coin bitcoin` prints for the bitcoin analysis of 2026-10-17
12:04 UTC, kept byte for byte. No filter fired on this one: the AI's text agreed
with the math. The date under the coin name is when the engine computed the
analysis, not when the command ran, and the seal is recomputed on the spot.
[Verify the Hash Yourself](#verify-the-hash-yourself) works through a real
response where a filter did fire.

```
───────────────────────────────────────────────────────
  CRYPTOCAPI RADAR — Bitcoin (BTC)
  Analysis computed 2026-10-17 12:04:00 UTC (1 h ago)
───────────────────────────────────────────────────────

  ↔️  MARKET REGIME:   RANGING_CHOP
  ➡️  SENTIMENT:       neutral
  🎯 CONFIDENCE:      MEDIUM (0.63)
  🔺 Z-SCORE:         -0.428 (no anomaly)
  📏 BANDWIDTH:       0.0686 (band width / 20-period mean)

  ANALYSIS:
   Tensión Latente: El precio opera en la zona inferior de las Bandas de Bollinger, manteniéndose en rango sin ruptura clara. La
   expansión de las bandas indica volatilidad moderada, pero el movimiento sigue lateral. No hay catalizador fundamental evidente; el
   impulso es puramente técnico.

  SOURCES VERIFIED (2), window 24h:
    [Tier 1] Satoshi-era bitcoin faces a bigger quantum threat after Google’s new Willow breakthrough
             https://www.coindesk.com/tech/2026/10/16/satoshi-era-bitcoin-faces-a-bigger-quantum-threat-after-google-s-new-willow-breakthrough
    [Tier 2] Bitcoin Treasury Giant Strategy Faces Index Removal Under Finalized MSCI Rules
             https://decrypt.co/381168/bitcoin-treasury-giant-strategy-faces-index-removal-under-finalized-msci-rules

───────────────────────────────────────────────────────
  🛡️  ANTI-HALLUCINATION AUDIT TRAIL
───────────────────────────────────────────────────────

  Pipeline:  Radar 4-Layer Anti-Hallucination Pipeline
  Version:   v2.4.0-radar
  Seal type: process_seal
             Seals the exact corrections the 4-layer pipeline applied. Text is not reproducible (LLM is non-deterministic by design).

  No filters fired: the LLM's output was consistent with the math

  Fields Python owns, never the LLM (5):
    🔒  analysis.anomaly_details
        the anomaly description. Written from the Z-Score or left empty. The AI cannot invent one
    🔒  analysis.confidence
        the HIGH / MEDIUM / LOW label, derived from the score, not from the AI's wording
    🔒  analysis.sentiment_score
        the numeric sentiment inside the report, computed from the Z-Score
    🔒  confidence
        how sure the call is. Derived from the math, never from how assertive the AI sounded
    🔒  is_volatility_alert
        the volatility flag. Raised by the Bollinger bandwidth alone

  The math engine writes these on every response, whatever the LLM said.

  Protocol hash (SHA-256):
    0x4a312f6edcae9597d602721a473f84962eec9b78cc7bcfd2de3bc9372859df51
    ✓ recomputed here from this response: it matches (the response is the one that was sealed; an unkeyed hash cannot say who sealed
    it)

───────────────────────────────────────────────────────
  ✅ Math Override applied · seal verified
───────────────────────────────────────────────────────
```

---

## The Problem

Every AI crypto tool sounds confident. None of them can prove they didn't invent the data.

Ask an LLM to analyze Bitcoin and it will tell you the volume is "moderate", the movement is "significant", and the lower Bollinger Band is holding as support, even when the math says the price is sitting at dead center with a Z-Score of -0.6. That's not analysis. That's pattern-matching from training data dressed up as financial insight.

In traditional software, a wrong answer is a bug you can catch. In AI, a confident wrong answer looks **identical** to a confident right one. That's not a UX problem: it's a capital risk.

We built a different architecture. Before any insight reaches you, a deterministic Python math engine runs four sequential filters over the LLM's output, strips the claims that contradict the numbers it can check, and emits a **SHA-256 receipt** of exactly what was corrected.

---

## How It Works

![Radar 4-Layer Anti-Hallucination Pipeline: market data enters on the left, passes through Layer 1 Math Engine and Layer 2 Prompt Injection, then a caged LLM, then Layer 3 Numeric Override and Layer 4 Lexical Filters, and exits as a SHA-256 sealed verified insight](assets/pipeline.svg)

Left to right, box by box:

- **Market Data.** Price and news for the asset. This is third-party input: in this system the raw feed is never the product, only the raw material.
- **Layer 1 · Math Engine.** Python computes the Z-Score, Bollinger Bands and market regime *before* the LLM sees anything. This is the ground truth every later step defends.
- **Layer 2 · Prompt Injection (10 Laws).** Those math values go into the prompt as non-negotiable constraints. Laws 0-9 bound what the model is even allowed to claim.
- **LLM.** Writes the language, and only the language. It never gets the last word on a number, and it cannot invent one.
- **Layer 3 · Numeric Override.** Once the model answers, Python reclaims every numeric field. On any collision between the prose and the math, the math wins.
- **Layer 4 · Lexical Filters.** Four deterministic filters (~300 lexical patterns) strip volume claims the engine cannot back, magnitude inflation, false-certainty markers and band-position contradictions.
- **Verified Insight + SHA-256 seal.** The grounded narrative ships with a `protocol_hash` recording exactly which corrections ran. The same inputs always produce the same digest, so anyone can re-verify it independently.

The LLM generates the language. The math engine generates the truth.

---

## Same question, two kinds of answer

Anyone can rerun this. On 2026-07-20, in plain conversational mode with no live-data tools, we asked GPT-5.5, Gemini 3.1 Pro and the Radar agent the same four questions about Bitcoin: is trading volume high, moderate or low, where is price relative to its Bollinger Bands, what is the short-term sentiment, and how confident are you? The full prompt, the raw replies and Radar's JSON are in [`docs/comparisons/2026-07-20-btc/`](docs/comparisons/2026-07-20-btc).

One of those four, volume, is left out of the table below on purpose: the Radar engine has no volume series to read, only a 24h total it cannot call high or low, so it is not a like-for-like axis. The models' volume answers are kept, untouched, in the raw replies.

We are not claiming the raw models are wrong. We cannot prove that, and neither can they. The claim is narrower, and it is the whole point of the product: **one of these three answers you can check, the other two you cannot.**

| | Raw LLM (GPT-5.5 / Gemini 3.1 Pro) | Radar Agent |
|---|---|---|
| **Where the read comes from** | the model's own prose | a stated computation: Z-Score `0.2254`, Bollinger bandwidth `0.0773`, over a live price series |
| **Are the inputs shown?** | no | yes, in the `math_diagnostics` block |
| **Can you reproduce the result?** | no, it changes on every run | yes, recompute the SHA-256 from the payload ([Verify the Hash Yourself](#verify-the-hash-yourself)) |
| **Sources behind the claim** | none | two cited headlines, Tier 1 and Tier 2, over a 24h window |
| **What the seal proves** | there is nothing to seal | that the pipeline ran with exactly these values (`process_seal`). It is an unkeyed digest, so it is a checksum and not a proof of origin: see [what the seal does and does not prove](#what-the-seal-does-and-does-not-prove). It does not claim to be the market truth; it makes the read checkable |

Asked where price sat in the bands, GPT-5.5 answered "around the middle", Gemini 3.1 Pro said it had no live data and pointed to TradingView, and the Radar agent returned `TERCIO_SUPERIOR`, which Python computes from the price against its Bollinger Bands, in a response carrying the seal `0x8f96020d…83fd059`. Whether "middle" or "upper third" is the truer label is not the argument.

One limit, stated plainly, because overclaiming is exactly what this repo exists to catch: the band label is a different computation from the `z_score` above. The Z-Score scores the latest *return* against its own history, not where the price sits inside the bands, so neither one is derivable from the other. And today that label ships inside the narrative, not as its own field in `math_diagnostics`. So on this axis what you can reproduce independently is the seal, not the label. The other two answers offer neither.

---

## Quick Start

Requires **Python 3.11+**. No signup required: the demo key is pre-configured for BTC and ETH.

```bash
# 1. Clone
git clone https://github.com/Jegoba90/anti-hallucination-crypto-agent.git
cd anti-hallucination-crypto-agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python agent.py coin bitcoin
```

That's it. No key to configure: the agent falls back to the public demo key on its
own. You'll see the analysis **and** the audit trail of what the math corrected.

> **Want to analyze more coins?** The demo key is limited to BTC and ETH.
> Get your free 14-day trial (no credit card): [cryptocapi.com](https://cryptocapi.com).
> Then `cp .env.example .env` (Windows cmd: `copy .env.example .env`) and set
> `CRYPTOCAPI_API_KEY=sk_live_...` in it.

---

## Commands

**Works with the pre-configured demo key (BTC & ETH):**

```bash
# Analyze a single coin
python agent.py coin bitcoin
python agent.py coin ethereum

# Watch mode: refresh every 30 minutes, flag sentiment changes
python agent.py coin bitcoin --watch
python agent.py coin bitcoin --watch --interval 15

# Raw API response, audit trail included: verify the hash yourself
python agent.py coin bitcoin --json

# Batch: both coins in one request
python agent.py batch bitcoin ethereum
```

**Requires a free trial key (any coin + the Market Scan engine):**

```bash
# Any other coin
python agent.py coin solana

# Batch with any other coin (the demo key rejects the whole batch otherwise)
python agent.py batch bitcoin ethereum solana

# Market scan: rank the Quant Plus universe by how close each asset is to
# its own anomaly threshold
python agent.py scan
python agent.py scan --strategy aggressive --limit 5
python agent.py scan --strategy conservative
```

> Get your free 14-day trial (no credit card): [cryptocapi.com](https://cryptocapi.com)

---

## Use Cases

Each scenario below comes with the command that runs it, and most with a script
in `examples/` you can open and adapt.

### Sanity-check a coin before acting on an AI signal

Somewhere, a confident AI is calling Bitcoin "clearly bullish" right now. Ask
this agent instead: you get the verdict plus the receipt. If the LLM's take
contradicted the Z-Score, the override shows up in the audit trail, so you see
whether the AI had to be corrected before the answer reached you.

```bash
python agent.py coin bitcoin
# minimal version in code: python examples/basic_analysis.py
```

### Watch a position and catch sentiment flips

Poll a coin every N minutes and get flagged the moment the sentiment changes.
Each refresh ships its own audit trail, so when a flip happens you can tell
whether the math forced it (`sentiment_override: true`) or the narrative moved
on its own.

```bash
python agent.py coin bitcoin --watch --interval 15
# script version: python examples/watch_mode.py bitcoin 15
```

### Survey the market for assets nearing an anomaly

Rank the curated Quant Plus universe (up to about 15 assets) by how close each
one is to firing its own anomaly threshold, and keep the top N. The strategy
changes the order, not the set: `aggressive` ranks by that proximity,
`conservative` by the evidence behind it, `balanced` by both. It is
surveillance, not a recommendation, and it is pure math: no LLM is involved
anywhere in a scan.

```bash
python agent.py scan --strategy aggressive --limit 5
# script version: python examples/market_scanner.py aggressive 5
```

### Compare assets side by side

One request, several coins, the same deterministic yardstick. Useful for the
"rotate ETH into SOL?" kind of question, where you want both candidates
measured identically instead of narrated separately.

```bash
python agent.py batch bitcoin ethereum
# script version: python examples/batch_compare.py bitcoin ethereum
# add solana or any other coin with a trial key
```

### Archive analysis you can re-verify later

Because every alpha response carries its `protocol_hash` (and the demo key always
gets the alpha view), a JSON dump is more than a log. Store the raw responses
**and record their digests somewhere separate**, and an archive edited after the
fact stops matching. The seal is unkeyed, so the
tamper-evidence lives in that independent copy of the hash, not in the file that
carries it.

```bash
python agent.py coin bitcoin --json > btc.json
```

The next section shows exactly how to recompute the hash from that file.

### Feed verified data to your own AI agent

The inverse use case: your own LLM app needs market context, and you would
rather not inherit someone else's hallucinations. Copy the `cryptocapi/`
package, call `get_insight()`, and hand your model numbers computed by Python
and text that already went through the 4-layer pipeline. See
[Use It in Your Own Code](#use-it-in-your-own-code).

> Single-coin analysis, watch mode, the JSON dump and batch run on the
> pre-configured demo key (BTC & ETH). Market scan and any other coin need a
> [free 14-day trial key](https://cryptocapi.com).

---

## Verify the Hash Yourself

The Radar `protocol_hash` is a SHA-256 digest of exactly eight fields: the
pipeline identity (`algorithm_id`, `engine_version`), the math inputs that
drove the overrides (`z_score`, `market_regime`, `sentiment`,
`sentiment_override`), and the sorted lists of what the pipeline touched
(`filters_applied`, `fields_overridden`). No wall-clock timestamp is hashed,
so the same inputs always produce the same digest. The keys are sorted and the
JSON is compact; how the one number in it, `z_score`, is written depends on the
engine version, and the response says which version sealed it (below).

A word on `fields_overridden`, because the CLI splits it in two and the seal
does not. Five entries are always present (`analysis.anomaly_details`,
`analysis.confidence`, `analysis.sentiment_score`, `confidence`,
`is_volatility_alert`): the math engine writes those on every single response, so
the LLM never gets a say. That is a **guarantee**, not a catch, and the CLI labels
it as such. The other entries are conditional, and those are the real catches:
`sentiment` shows up only when the Z-Score rule overrode the LLM's verdict,
`analysis.detailed_report` only when a lexical filter cut text out of it, and,
since `v2.4.0-radar`, `summary` only when LEY 7 cut a volume claim out of the
summary.

The example below is a real response where a filter did fire, unlike the run at
the top: bitcoin, 2026-09-03 (`v2.2.0-radar`), published in
[CryptoCapi-Portfolio](https://github.com/Jegoba90/CryptoCapi-Portfolio/blob/main/api/examples/radar-alpha.json)
and kept byte for byte in `tests/fixtures/radar_alpha_v2.2.0.json`. LEY 7 cut a
volume claim and the report was rewritten, so it has one conditional entry, the
report, and seals six. The seal hashes the raw union of the six, exactly as the
API ships it.

These are its eight sealed fields, copied from the response. Run them and you
get the hash the engine issued, with no dependencies and no CryptoCapi account
needed. One detail: from `v2.2.0-radar`
the engine seals every number as a string with exactly 6 decimals, so the
`z_score` of `2.2794` goes in as `"2.279400"` (the next section explains why):

```python
import hashlib, json

payload = {
    "algorithm_id": "Radar 4-Layer Anti-Hallucination Pipeline",
    "engine_version": "v2.2.0-radar",
    "z_score": "2.279400",
    "market_regime": "BULLISH_TREND",
    "sentiment": "bullish",
    "sentiment_override": False,
    "filters_applied": ["LEY 7 volume"],
    "fields_overridden": [
        "analysis.anomaly_details",
        "analysis.confidence",
        "analysis.detailed_report",
        "analysis.sentiment_score",
        "confidence",
        "is_volatility_alert",
    ],
}

serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
digest = "0x" + hashlib.sha256(serialized.encode()).hexdigest()

print(digest)
# → 0x4440a68517f2929f7c73a90835b8624f8f9861b6d43dca3c37646d351e4de18c
```

### Now do it on a live response

Dump exactly what the API returned, audit trail included:

```bash
python agent.py coin bitcoin --json > btc.json
```

Then rebuild the payload from that file and hash it. One rule depends on the
version in `engine_version`: since `v2.2.0-radar` (2026-09-01), every number is
sealed as a string with exactly 6 decimals, so `0.3296` goes in as `"0.329600"`.
That keeps the digest independent of how a JSON encoder happens to print a
number, which it is not across languages: `63482.0` in Python is `63482` in
JavaScript. `v2.1.0-radar` seals, like the capture in
[`docs/comparisons/`](docs/comparisons/2026-07-20-btc), hashed the number as it
was. Every response the API serves today carries a later version; the check on
the version is there so a dump archived before the change still verifies.

```python
import hashlib, json

response = json.load(open("btc.json"))
math = response["math_diagnostics"]
trail = math["audit_trail"]

payload = {
    "algorithm_id": trail["algorithm_id"],
    "engine_version": trail["engine_version"],
    "z_score": math["z_score"],
    "market_regime": math["market_regime"],
    "sentiment": response["sentiment"],
    "sentiment_override": trail["sentiment_override"],
    "filters_applied": trail["filters_applied"],
    "fields_overridden": trail["fields_overridden"],
}

# z_score is the only number in this payload. Python's format() rounds half to
# even, exactly as the engine does; JavaScript's toFixed() does not.
if trail["engine_version"] != "v2.1.0-radar":
    payload["z_score"] = format(payload["z_score"], ".6f")

serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
digest = "0x" + hashlib.sha256(serialized.encode()).hexdigest()

print(digest == trail["protocol_hash"])
# → True
```

If it prints `True`, the response is internally consistent: the corrections listed
in the trail are exactly the ones the digest was computed over.

The CLI runs this same recipe on every response it shows (`cryptocapi/seal.py`)
and says what it found: verified, does not match (the command then exits
non-zero), or not checked, for a response without a seal or an engine version
newer than the agent knows, whose rule may have changed. It never calls a seal
wrong when it is the agent that fell behind. Run the recipe yourself anyway: a
check made by the agent is the agent vouching for itself, and the recipe needs
nothing from this repo.

The full recipe for all three engines, with a JavaScript reference implementation
and every version boundary, is in
[SEAL.md](https://github.com/Jegoba90/CryptoCapi-Portfolio/blob/main/docs/SEAL.md).

### What the seal does and does not prove

Being vague here would be the same defect this repo exists to catch, only pointed
at itself. The `protocol_hash` is an **unkeyed** SHA-256 over values the engine
reports about itself, which makes it a checksum, not a signature:

- **It catches** corruption, truncation, and any later edit to a payload whose
  digest you recorded somewhere independent. Write the hash down when the
  response arrives and a changed archive stops matching months later.
- **It does not catch** anyone who can recompute the hash after editing the
  payload, which includes a man-in-the-middle and the API operator itself. An
  unkeyed digest carries no proof of origin. Only a signed seal would.

So the honest reading of `True` is "this is the response that was sealed under a
hash I already trusted", and that trust has to come from where you stored the
hash, not from the response carrying it.

---

## Use It in Your Own Code

The `cryptocapi/` package is designed to be copied directly into your project:

```python
import asyncio
from cryptocapi import CryptoCapiClient, check_seal, parse_audit_trail

async def main():
    # "demo_btc_eth_public" works out of the box for BTC/ETH; use your
    # own sk_live_... key (14-day trial) to analyze any other coin.
    client = CryptoCapiClient(api_key="demo_btc_eth_public")
    data = await client.get_insight("bitcoin")
    if data is None:
        # The API's `data: null`: no engine has analyzed the coin yet.
        # A valid answer, not an error. Don't fill the gap.
        print("No analysis available yet")
        return

    # Use the insight (note the nesting, see cryptocapi/models.py)
    print(data["sentiment"])                          # neutral
    print(data["math_diagnostics"]["market_regime"])  # RANGING_CHOP
    print(data["asset"]["symbol"])                     # BTC

    # Inspect the audit trail
    math = data.get("math_diagnostics", {})
    audit = parse_audit_trail(math.get("audit_trail"))

    if audit.is_pro:
        print(f"Filters fired: {[f[0] for f in audit.filters]}")
        print(f"Fields Python overrode: {audit.fields_overridden}")
        print(f"Hash: {audit.protocol_hash}")

    # Recompute the seal from this response: integrity, not origin
    print(check_seal(data).status)                     # SealStatus.VERIFIED

asyncio.run(main())
```

`get_insight` returns `None` when the API answers `data: null`, which it does for
any coin no engine has analyzed yet, and for an id it does not know. That is an
answer, not an error, so it is not raised.

The client raises four errors, all importable straight from `cryptocapi`:

| Error | When it fires |
|---|---|
| `DemoCoinRestricted` | the demo key asked for a coin outside BTC and ETH, in `get_insight` or anywhere in a `get_batch_signals` list |
| `ProEngineRequired` | `get_market_scan` or `get_batch_signals` ran on a key that doesn't include that engine (the demo key never reaches the scan) |
| `ApiError` | any other non-2xx answer: a rate limit, a rejected parameter, an outage. `.status_code` says which; it is also an `httpx.HTTPStatusError` |
| `UnexpectedResponse` | the API answered with something other than the envelope `models.py` describes |

All but `UnexpectedResponse` carry the API's own wording in `.user_message`, so you
can show it to a user as it is.

---

## Project Structure

```
├── agent.py               # CLI entry point (Typer)
├── cryptocapi/
│   ├── client.py          # Async HTTP client: copy this into your project
│   ├── models.py          # TypedDicts for full API response
│   ├── audit.py           # Audit trail parser + filter explanations
│   └── seal.py            # Recomputes the seal of every response it is handed
├── display/
│   ├── terminal.py        # Rich terminal renderer
│   └── themes.py          # Color scheme
├── examples/
│   ├── basic_analysis.py  # Minimal: analyze BTC and read its audit trail
│   ├── watch_mode.py      # Poll + detect sentiment changes
│   ├── market_scanner.py  # Screener using market-scan endpoint
│   └── batch_compare.py   # BTC vs ETH side by side (any coins with a trial key)
└── tests/
    ├── test_audit_parser.py        # Parser + hash reproducibility
    ├── test_readme_consistency.py  # The one CLI screen is what the CLI prints for its capture
    ├── test_seal_recipe.py         # The live recipe above, run as written, verifies real seals
    ├── test_seal_check.py          # The CLI checks every seal it shows, and never accuses blindly
    ├── test_published_evidence.py  # The sealed captures in docs/comparisons still verify
    ├── test_client_contract.py     # The client reads what the live API actually sends
    ├── test_cli.py                 # Watch mode flags sentiment flips; impossible flags fail loudly
    ├── test_render_audit.py        # The audit block's claims survive the renderer
    ├── test_render_verdict.py      # The CLI shows the engine's verdict, never its own
    ├── test_render_sources.py      # The evidence behind the narrative reaches the screen
    ├── test_render_timestamp.py    # The header dates the analysis, not the printing
    ├── test_render_quant.py        # Scan and batch rows name their asset and show the ranking
    ├── test_render_markup.py       # API text prints as text, never as Rich markup
    ├── test_render_layout.py       # Long text keeps its indent; nothing is cut; band width shown
    ├── test_pro_required.py        # The Quant plan gate reads as an offer, not an HTTP error
    ├── test_terminal_encoding.py   # The output survives a terminal that isn't UTF-8
    └── fixtures/
        ├── radar_alpha_v2.2.0.json # The real response behind the offline hash example
        ├── readme_demo_bitcoin_2026-10-17.json # The run the README opens with
        └── api/                    # Live captures, one per route the client calls
```

---

## Run the Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
mypy .
ruff check .
```

No network calls and no API key required: every test runs against a local
fixture. That includes running both recipes above, exactly as written here (the
offline payload, and the live one on the dump `coin --json` makes), against real
engine responses: `v2.1.0-radar`, `v2.2.0-radar` and `v2.4.0-radar` seals. So a
recipe cannot drift from the seals it claims to verify without the suite failing.
What the suite cannot see is an engine version newer than its newest capture: a
seal rule that changes again needs a fresh one.

The client's tests replay responses captured off the live API, in
`tests/fixtures/api/`. The scan, which the demo key cannot reach, uses the
example the API's OpenAPI document publishes for that route.

---

## Powered by CryptoCapi

This agent is built on [CryptoCapi](https://cryptocapi.com), a crypto intelligence API designed specifically for machine consumption.

That machine-first design is concrete: the API publishes a live [`llms.txt`](https://www.cryptocapi.com/llms.txt) that maps every endpoint, its parameters and response shapes in the format AI agents read. This repo shows the *copy-a-typed-client* path; `llms.txt` is the *zero-code* one, an agent in Claude Code, Cursor or Copilot discovers the whole API on its own. Works anywhere: Claude Code · Cursor · GitHub Copilot · ChatGPT · LangChain · any REST client.

Unlike general-purpose LLM wrappers, CryptoCapi's Radar engine runs a deterministic Python math pipeline between the AI and every API response. Every numeric field is computed by Python, not the LLM. Qualitative claims are cross-validated against the math. And every alpha response ships with a SHA-256 audit trail you can verify independently.

Want to look under the hood? [CryptoCapi-Portfolio](https://github.com/Jegoba90/CryptoCapi-Portfolio) documents the architecture behind the API: the three engines, the 4-layer pipeline, the seal semantics per engine ([SEAL.md](https://github.com/Jegoba90/CryptoCapi-Portfolio/blob/main/docs/SEAL.md)), and real sealed responses captured from production.

**Get your free 14-day trial** (no credit card required): [cryptocapi.com](https://cryptocapi.com)

---

## ⚠️ Disclaimer

This tool is for educational and informational purposes only. It does not constitute financial advice. Never make investment decisions based solely on automated analysis tools. Crypto markets are highly volatile and past performance does not indicate future results.

---

## License

MIT: use it, fork it, copy the `cryptocapi/` package into your own project.
