![Anti-Hallucination Crypto Agent](assets/banner.svg)

A Python client for CryptoCapi market analysis. It validates API data, displays
the corrections reported by the service, and recomputes supported Radar process
seals. **The market calculation engine and lexical filters run on the remote
service; their implementation and input price series are absent from this repo.**

![Python](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
[![Tests](https://github.com/Jegoba90/anti-hallucination-crypto-agent/actions/workflows/tests.yml/badge.svg)](https://github.com/Jegoba90/anti-hallucination-crypto-agent/actions/workflows/tests.yml)

What `python agent.py coin bitcoin` prints for the archived bitcoin analysis of
2026-10-17 14:02 UTC, rendered by the current client. The relative age changes
when you run it. The capture records a volume filter and a rewritten report;
those are the API's claims about its own processing.

```

───────────────────────────────────────────────────────
  CRYPTOCAPI RADAR — Bitcoin (BTC)
  Analysis computed 2026-10-17 14:02:25 UTC (21 d ago)
───────────────────────────────────────────────────────

  ↔️  MARKET REGIME:   RANGING_CHOP
  ➡️  SENTIMENT:       neutral
  🎯 CONFIDENCE:      MEDIUM (0.63)
  DATA QUALITY:     OPTIMAL
  🔺 Z-SCORE:         -0.428 (no anomaly (API verdict))
  📏 BANDWIDTH:       0.0686 (band width / 20-period mean)

  ANALYSIS:
   Tensión Latente: La reciente publicación sobre el avance de Google en chips cuánticos plantea una amenaza teórica a la seguridad
   de las billeteras, pero el impacto inmediato en el precio es limitado. El análisis técnico muestra que el activo opera en la zona
   inferior de las Bandas de Bollinger, manteniéndose en rango sin ruptura clara. El régimen de mercado se caracteriza por
   lateralización, con una expansión gradual de las bandas que indica una ligera apertura de volatilidad, pero sin señales de
   ruptura.

  SOURCES REPORTED BY API (2), window 24h:
    [Tier 1] Satoshi-era bitcoin faces a bigger quantum threat after Google’s new Willow breakthrough
             https://www.coindesk.com/tech/2026/10/16/satoshi-era-bitcoin-faces-a-bigger-quantum-threat-after-google-s-new-willow-breakthrough
    [Tier 2] Bitcoin Treasury Giant Strategy Faces Index Removal Under Finalized MSCI Rules
             https://decrypt.co/381168/bitcoin-treasury-giant-strategy-faces-index-removal-under-finalized-msci-rules

  Article contents and narrative claims were not independently verified by this client.

───────────────────────────────────────────────────────
  🛡️  ANTI-HALLUCINATION AUDIT TRAIL
───────────────────────────────────────────────────────

  Pipeline:  Radar 4-Layer Anti-Hallucination Pipeline
  Version:   v2.4.0-radar
  Seal type: process_seal
             Hashes selected values and 4-layer pipeline metadata. Narrative, confidence, sources, timestamps and other diagnostics
             are not covered.

  Filters fired (1):
    ✂️  [LEY 7 volume]  Removed a volume claim: Radar has no volume trend to back it

  Corrections reported by API (1):
    ✏️  analysis.detailed_report
        the lexical filters rewrote the narrative

  Python-owned fields reported by API (5):
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

  Ownership is reported by the API; this client does not execute the engine's calculations.

  Protocol hash (SHA-256):
    0x53e6680028c78b24e111fbca63639039f087dadd8e9925284bba72fbceec4138
    ✓ recomputed here from this response: it matches (only covered fields match; an unkeyed hash cannot say who sealed it)
    The seal does not cover the narrative, confidence, bandwidth, sources, or timestamps. It does not verify market calculations.

───────────────────────────────────────────────────────
  ✅ Process seal verified · covered fields match
───────────────────────────────────────────────────────

```

## What this client checks

| Check | What it establishes | What it cannot establish |
|---|---|---|
| Response validation | Supported fields have the expected types and numeric ranges; provided asset IDs match requested IDs | Whether upstream prices or news are accurate |
| Radar process seal | Eight covered fields match a digest under a known algorithm and version | Who issued it, whether the filters actually ran, or whether the market math is correct |
| Audit display | The API reports these overrides and filters | That a reported correction removed every factual error |
| Missing data | Unknown readings remain visibly unknown | A replacement measurement or inferred verdict |

Source links and credibility tiers are supplied by the API. This client does
not fetch the articles or independently verify their contents. A missing audit
trail does not establish the subscription plan that produced the response.
Scan and batch results are supplied by Quant Plus and are not recomputed here.

## Quick Start

Requires **Python 3.11+**.

```bash
pip install -r requirements.txt
python agent.py coin bitcoin
python agent.py coin ethereum
```

With no `CRYPTOCAPI_API_KEY`, the client uses the public BTC/ETH demo key.
Set your own key in `.env` for other assets or engine access. An explicitly empty
key omits authentication; an Alpha request may fall back to Pulse, which may
lack diagnostics and a seal.
`CRYPTOCAPI_BASE_URL` changes the CLI's API address.

```bash
# Continuous polling; interval is in minutes and must be at least 1
python agent.py coin bitcoin --watch --interval 15

# JSON data for inspection; cannot be combined with --watch
python agent.py coin bitcoin --json > btc.json

# Require a matching supported process seal; fail if absent or unsupported
python agent.py coin bitcoin --require-verified-seal

# Quant Plus routes; access depends on the API key
python agent.py batch bitcoin ethereum
python agent.py scan --strategy balanced --limit 10
```

A known seal mismatch exits with status 1 in single-run and JSON modes. JSON
mode preserves the returned data for inspection, so check the exit status before
using it. Watch mode displays a mismatch and continues polling, without using
that reading for sentiment alerts. An absent or unsupported seal is shown as
unchecked; exit status 0 alone does not mean a seal was verified.
Use `--require-verified-seal` when your script requires that check: missing,
unsupported and mismatched seals then fail in single-run and JSON modes. In
watch mode they never update sentiment alerts. This option checks only seal
coverage; it adds no independent validation of the market calculations.

`data: null` means the API returned no analysis. It prints `null` in JSON mode
and exits successfully. An unknown coin can produce that same answer.

## Verify the Hash Yourself

Radar's process seal covers exactly these fields:
`algorithm_id`, `engine_version`, `z_score`, `market_regime`, `sentiment`,
`sentiment_override`, `filters_applied`, and `fields_overridden`.
The lists are hashed in their received order. JSON object keys are sorted.

The offline example below reproduces the seal in
[`tests/fixtures/radar_alpha_v2.2.0.json`](tests/fixtures/radar_alpha_v2.2.0.json).
The fixed-six-decimal representation is part of that version's recipe.

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

Create `btc.json` with `python agent.py coin bitcoin --json > btc.json`.
This independent recipe supports only the known Radar versions. Unknown
versions require a reviewed recipe; a plausible matching hash is insufficient.

```python
import hashlib
import json
import math

with open("btc.json", encoding="utf-8") as source:
    response = json.load(source)
diagnostics = response["math_diagnostics"]
trail = diagnostics["audit_trail"]
rules = {
    "v2.1.0-radar": "plain",
    "v2.2.0-radar": "fixed6",
    "v2.3.0-radar": "fixed6",
    "v2.4.0-radar": "fixed6",
}
if (trail["seal_type"] != "process_seal"
        or trail["algorithm_id"] != "Radar 4-Layer Anti-Hallucination Pipeline"):
    raise ValueError("Unsupported seal algorithm or type")
rule = rules.get(trail["engine_version"])
if rule is None:
    raise ValueError("Unsupported engine version")
z_score = diagnostics["z_score"]
if type(z_score) not in (int, float) or not math.isfinite(z_score):
    raise ValueError("Expected a finite numeric Z-Score")

payload = {
    "algorithm_id": trail["algorithm_id"],
    "engine_version": trail["engine_version"],
    "z_score": z_score,
    "market_regime": diagnostics["market_regime"],
    "sentiment": response["sentiment"],
    "sentiment_override": trail["sentiment_override"],
    "filters_applied": trail["filters_applied"],
    "fields_overridden": trail["fields_overridden"],
}
if rule == "fixed6":
    # Normalize signed zero before the engine's six-decimal formatting.
    payload["z_score"] = format(z_score + 0.0, ".6f")
serialized = json.dumps(
    payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
)
digest = "0x" + hashlib.sha256(serialized.encode("utf-8")).hexdigest()
print(digest == trail["protocol_hash"])
# True means these eight fields match their supplied digest.
```

The CLI uses [`cryptocapi/seal.py`](cryptocapi/seal.py). Tests run both recipes
above against archived responses across the serialization version boundary.

### What the seal does and does not prove

The digest is **unkeyed**, so it is a checksum, not a signature. Anyone who edits
the covered fields can also recompute it. Retaining a digest separately can
detect later changes to those covered fields.

**The narrative, summary, confidence, Bollinger bandwidth, anomaly flag, source
links and timestamps are outside this process seal.** Changing only those
fields leaves the digest unchanged. It cannot detect all edits to a response,
prove that the pipeline executed, or certify any market measurement.

The historical comparison capture in
[`docs/comparisons/2026-07-20-btc/`](docs/comparisons/2026-07-20-btc) carries
`0x8f96020d…83fd059`. Its seal can be reproduced. That does not reproduce its
underlying indicators or establish that its narrative is more accurate than
another model's reply; this capture is not a controlled accuracy benchmark.

## Use It in Your Own Code

```python
import asyncio
from cryptocapi import CryptoCapiClient, SealStatus, check_seal

async def main():
    client = CryptoCapiClient(api_key="demo_btc_eth_public")
    data = await client.get_insight("bitcoin")
    if data is None:
        print("No analysis available")
        return
    check = check_seal(data)
    if check.status is not SealStatus.VERIFIED:
        raise ValueError(f"Seal not verified: {check.reason}")
    # A matching process seal does not validate the unsealed narrative or math.
    print(data.get("sentiment"))

asyncio.run(main())
```

Client exceptions are available from `cryptocapi`:

| Exception | Meaning |
|---|---|
| `DemoCoinRestricted` | The API rejected a coin under the public demo key |
| `ProEngineRequired` | The API rejected access to a Quant route |
| `ApiError` | Other non-success HTTP response; includes `.status_code` |
| `UnexpectedResponse` | The response violates the supported data contract |

HTTP transport errors are propagated by `httpx`. Error text from the API is
data and is escaped before terminal rendering.

## Development

```bash
pip install -r requirements-dev.txt
pytest tests/ -q
mypy .
ruff check .
```

Tests use archived responses and mock HTTP transports; they do not require an
API key or live requests. They check local behavior and known seals, without
auditing the remote calculation engine or forecasting performance.

| Path | Purpose |
|---|---|
| `agent.py` | CLI, JSON output and polling |
| `cryptocapi/client.py` | HTTP requests and runtime data validation |
| `cryptocapi/models.py` | Response types |
| `cryptocapi/seal.py` | Known Radar process-seal recipes |
| `cryptocapi/audit.py` | Interpret known reported overrides |
| `display/terminal.py` | Terminal output and uncertainty labels |
| `examples/` | Single-asset, watch, scan and batch scripts |
| `tests/fixtures/` | Archived API data and contract examples |

MIT license. API access and upstream behavior are controlled by
[CryptoCapi](https://cryptocapi.com).
