```
▄▀█ █▄░█ ▀█▀ █ ░ █░█ ▄▀█ █░░ █░░ █░█ █▀▀ █ █▄░█ ▄▀█ ▀█▀ █ █▀█ █▄░█
█▀█ █░▀█ ░█░ █ ░ █▀█ █▀█ █▄▄ █▄▄ █▄█ █▄▄ █ █░▀█ █▀█ ░█░ █ █▄█ █░▀█

█▀▀ █▀█ █▄█ █▀█ ▀█▀ █▀█ ░ ▄▀█ █▀▀ █▀▀ █▄░█ ▀█▀
█▄▄ █▀▄ ░█░ █▀▀ ░█░ █▄█ ░ █▀█ █▄█ ██▄ █░▀█ ░█░
```

> A Python agent that analyzes crypto markets using AI, and **proves** it didn't make anything up.

![Python](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Anti-Hallucination](https://img.shields.io/badge/Anti--Hallucination-CTC--2026%20Certified-blueviolet?style=flat-square)
[![Tests](https://github.com/Jegoba90/anti-hallucination-crypto-agent/actions/workflows/tests.yml/badge.svg)](https://github.com/Jegoba90/anti-hallucination-crypto-agent/actions/workflows/tests.yml)

![demo](demo.gif)

---

## The Problem

Every AI crypto tool sounds confident. None of them can prove they didn't invent the data.

Ask an LLM to analyze Bitcoin and it will tell you the volume is "moderate", the movement is "significant", and the lower Bollinger Band is holding as support, even when the math says the price is sitting at dead center with a Z-Score of -0.6. That's not analysis. That's pattern-matching from training data dressed up as financial insight.

In traditional software, a wrong answer is a bug you can catch. In AI, a confident wrong answer looks **identical** to a confident right one. That's not a UX problem: it's a capital risk.

We built a different architecture. Before any insight reaches you, a deterministic Python math engine runs four sequential filters over the LLM's output, strips every claim that contradicts the actual numbers, and emits a **cryptographic receipt** proving exactly what was corrected.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  RADAR 4-LAYER ANTI-HALLUCINATION PIPELINE                  │
│                                                             │
│  LAYER 1 — Math Engine                                      │
│  Python calculates Z-Score, Bollinger Bands, regime         │
│  BEFORE the LLM sees any data                               │
│                           ↓                                 │
│  LAYER 2 — Prompt Injection (10 Laws)                       │
│  Math values injected as NON-NEGOTIABLE constraints         │
│  into the LLM prompt. Laws 0-9 restrict what AI can claim   │
│                           ↓                                 │
│  LAYER 3 — Numeric Override                                 │
│  After the LLM responds, Python owns every numeric field    │
│  The AI never has the last word on the numbers              │
│                           ↓                                 │
│  LAYER 4 — Lexical Filters (4 deterministic filters)        │
│  Strips sentences containing: inflated volume claims,       │
│  magnitude inflation, certainty markers, band-position      │
│  contradictions — ~300 lexical pattern combinations         │
│                           ↓                                 │
│  ✅ SHA-256 AUDIT TRAIL EMITTED                             │
│  protocol_hash certifies exactly which corrections ran      │
└─────────────────────────────────────────────────────────────┘
```

The LLM generates the language. The math engine generates the truth.

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
own. You'll see the analysis **and** the audit trail proving it was verified.

> **Want to analyze more coins?** The demo key is limited to BTC and ETH.
> Get your free 14-day trial (no credit card): [cryptocapi.com](https://cryptocapi.com).
> Then `cp .env.example .env` (Windows cmd: `copy .env.example .env`) and set
> `CRYPTOCAPI_API_KEY=sk_live_...` in it.

> **On Windows** seeing a `UnicodeEncodeError`? Your terminal isn't using UTF-8.
> Fix it for the session with `set PYTHONIOENCODING=utf-8` (cmd) or
> `$env:PYTHONIOENCODING="utf-8"` (PowerShell), then run again.

---

## Output

```
───────────────────────────────────────────────────────
  CRYPTOCAPI RADAR — Bitcoin (BTC)
  2026-06-19 14:32:07 UTC
───────────────────────────────────────────────────────

  ↔️  MARKET REGIME:   RANGING_CHOP
  ➡️  SENTIMENT:       neutral
  🎯 CONFIDENCE:      MEDIUM (0.64)
  🔺 Z-SCORE:         -0.637 (no anomaly)

  ANALYSIS:
   El activo opera en zona de equilibrio técnico sin catalizador
   fundamental relevante en las últimas 24h. Las bandas de Bollinger
   muestran compresión consistente con una fase lateral consolidada.

───────────────────────────────────────────────────────
  🛡️  ANTI-HALLUCINATION AUDIT TRAIL
───────────────────────────────────────────────────────

  Pipeline:  Radar 4-Layer Anti-Hallucination Pipeline
  Version:   v2.1.0-radar
  Seal type: process_seal
             Certifies the 4-layer pipeline ran with these
             exact corrections. Text is not reproducible
             (LLM is non-deterministic by design).

  Filters fired (2):
    ✂️  [LEY 7 volume]  Removed a qualitative volume claim:
                       the system has no volume data
    ✂️  [band position CENTRO_BANDAS]  Removed a band-edge
                       claim: the price was at CENTRO_BANDAS

  Corrections applied to the LLM's output (2):
    ✏️  sentiment
        Python overrode the LLM's verdict (Z-Score rule)
    ✏️  analysis.detailed_report
        the lexical filters rewrote the narrative

  Fields Python owns, never the LLM (5):
    🔒  analysis.anomaly_details
        the anomaly description. Written from the Z-Score or left
        empty. The AI cannot invent one
    🔒  analysis.confidence
        the HIGH / MEDIUM / LOW label, derived from the score, not
        from the AI's wording
    🔒  analysis.sentiment_score
        the numeric sentiment inside the report, computed from the
        Z-Score
    🔒  confidence
        how sure the call is. Derived from the math, never from how
        assertive the AI sounded
    🔒  is_volatility_alert
        the volatility flag. Raised by the Bollinger bandwidth alone

  The math engine writes these on every response, whatever the LLM said.

  Protocol hash (SHA-256):
    0xe024a312f5726bb2213c018e8fef8228dde21506655ca57295f2374d6e92eb63

───────────────────────────────────────────────────────
  ✅ Math Override Certified (CTC-2026)
───────────────────────────────────────────────────────
```

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
```

**Requires a free trial key (any coin + the Quant Pro engines):**

```bash
# Any other coin
python agent.py coin solana

# Market scan: rank all tracked assets by signal strength
python agent.py scan
python agent.py scan --strategy aggressive --limit 5
python agent.py scan --strategy conservative

# Batch: analyze multiple coins in one request
python agent.py batch bitcoin ethereum solana
```

> Get your free 14-day trial (no credit card): [cryptocapi.com](https://cryptocapi.com)

---

## Verify the Hash Yourself

The Radar `protocol_hash` is a SHA-256 digest of exactly eight fields: the
pipeline identity (`algorithm_id`, `engine_version`), the math inputs that
drove the overrides (`z_score`, `market_regime`, `sentiment`,
`sentiment_override`), and the sorted lists of what the pipeline touched
(`filters_applied`, `fields_overridden`). No wall-clock timestamp is hashed,
so the same inputs always produce the same digest.

A word on `fields_overridden`, because the output above splits it in two and the
seal does not. Five entries are always present (`analysis.anomaly_details`,
`analysis.confidence`, `analysis.sentiment_score`, `confidence`,
`is_volatility_alert`): the math engine writes those on every single response, so
the LLM never gets a say. That is a **guarantee**, not a catch, and the CLI labels
it as such. Two more entries are conditional, and those are the real catches:
`sentiment` shows up only when the Z-Score rule overrode the LLM's verdict, and
`analysis.detailed_report` only when a lexical filter cut text out of it. The run
above has both, which is why it seals seven.

The seal hashes the raw union of the seven, exactly as the API ships it.

This is the exact payload behind the output above, and the same fixture the test
suite runs against. Run it and you get that exact hash, with no dependencies and
no CryptoCapi account needed:

```python
import hashlib, json

payload = {
    "algorithm_id": "Radar 4-Layer Anti-Hallucination Pipeline",
    "engine_version": "v2.1.0-radar",
    "z_score": -0.6367,
    "market_regime": "RANGING_CHOP",
    "sentiment": "neutral",
    "sentiment_override": True,
    "filters_applied": ["LEY 7 volume", "band position CENTRO_BANDAS"],
    "fields_overridden": [
        "analysis.anomaly_details",
        "analysis.confidence",
        "analysis.detailed_report",
        "analysis.sentiment_score",
        "confidence",
        "is_volatility_alert",
        "sentiment",
    ],
}

serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
digest = "0x" + hashlib.sha256(serialized.encode()).hexdigest()

print(digest)
# → 0xe024a312f5726bb2213c018e8fef8228dde21506655ca57295f2374d6e92eb63
```

### Now do it on a live response

Dump exactly what the API returned, audit trail included:

```bash
python agent.py coin bitcoin --json > btc.json
```

Then rebuild the payload from that file and hash it. Note the one precision
detail: the seal hashes `z_score` rounded to **6 decimals**, while the response
exposes it at full float precision, so round it first.

```python
import hashlib, json

response = json.load(open("btc.json"))
math = response["math_diagnostics"]
trail = math["audit_trail"]

payload = {
    "algorithm_id": trail["algorithm_id"],
    "engine_version": trail["engine_version"],
    "z_score": round(math["z_score"], 6),
    "market_regime": math["market_regime"],
    "sentiment": response["sentiment"],
    "sentiment_override": trail["sentiment_override"],
    "filters_applied": trail["filters_applied"],
    "fields_overridden": trail["fields_overridden"],
}

serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
digest = "0x" + hashlib.sha256(serialized.encode()).hexdigest()

print(digest == trail["protocol_hash"])
# → True
```

If it prints `True`, the pipeline ran with those exact corrections and nothing was
tampered with in transit.

---

## Use It in Your Own Code

The `cryptocapi/` package is designed to be copied directly into your project:

```python
import asyncio
from cryptocapi import CryptoCapiClient, parse_audit_trail

async def main():
    # "demo_btc_eth_public" works out of the box for BTC/ETH; use your
    # own sk_live_... key (14-day trial) to analyze any other coin.
    client = CryptoCapiClient(api_key="demo_btc_eth_public")
    data = await client.get_insight("bitcoin")

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

asyncio.run(main())
```

---

## Project Structure

```
├── agent.py               # CLI entry point (Typer)
├── cryptocapi/
│   ├── client.py          # Async HTTP client: copy this into your project
│   ├── models.py          # TypedDicts for full API response
│   └── audit.py           # Audit trail parser + filter explanations
├── display/
│   ├── terminal.py        # Rich terminal renderer
│   └── themes.py          # Color scheme
├── examples/
│   ├── basic_analysis.py  # Minimal: analyze BTC in 20 lines
│   ├── watch_mode.py      # Poll + detect sentiment changes
│   ├── market_scanner.py  # Screener using market-scan endpoint
│   └── batch_compare.py   # BTC vs ETH vs SOL side by side
└── tests/
    ├── test_audit_parser.py        # Parser + hash reproducibility
    ├── test_readme_consistency.py  # Pins this README to the fixture
    ├── test_render_verdict.py      # The CLI shows the engine's verdict, never its own
    ├── test_render_sources.py      # The evidence behind the narrative reaches the screen
    └── fixtures/sample_response.json
```

---

## Run the Tests

```bash
pip install pytest
pytest tests/ -v
```

No network calls and no API key required: every test runs against a local
fixture. That includes the check that reproduces the `protocol_hash` documented
above, so a change to the pipeline that broke the seal would fail the suite.

---

## Powered by CryptoCapi

This agent is built on [CryptoCapi](https://cryptocapi.com), a crypto intelligence API designed specifically for machine consumption.

Unlike general-purpose LLM wrappers, CryptoCapi's Radar engine runs a deterministic Python math pipeline between the AI and every API response. Every numeric field is computed by Python, not the LLM. Every qualitative claim is cross-validated against the math. And every response ships with a SHA-256 audit trail you can verify independently.

**Get your free 14-day trial** (no credit card required): [cryptocapi.com](https://cryptocapi.com)

---

## ⚠️ Disclaimer

This tool is for educational and informational purposes only. It does not constitute financial advice. Never make investment decisions based solely on automated analysis tools. Crypto markets are highly volatile and past performance does not indicate future results.

---

## License

MIT: use it, fork it, copy the `cryptocapi/` package into your own project.
