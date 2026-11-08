# BTC market read, three assistants, 2026-07-20

Captured 2026-07-20 in plain conversational mode, with no live-data tools or
browsing enabled. This archive preserves the comparison context; it is not a
controlled accuracy benchmark.

Models:

- **GPT-5.5** (ChatGPT) -> `chatgpt.txt`
- **Gemini 3.1 Pro** -> `gemini.txt`
- **CryptoCapi Radar agent** -> `radar.json` (full API response, including the
  `math_diagnostics` block and the SHA-256 audit trail)

## The prompt (identical for all three)

```
You're a crypto market analyst. Give me a short read on Bitcoin (BTC) right now:
- Is trading volume currently high, moderate, or low?
- Where is the price relative to its Bollinger Bands (near the upper band, the lower band, or the middle)?
- What's the short-term sentiment: bullish, neutral, or bearish?
- How confident are you in this call?
Keep it to a few sentences.
```

## Limits of the comparison

The Radar response reports a volume filter because a single 24h total cannot
establish a volume trend. The models' answers are preserved in `chatgpt.txt`
and `gemini.txt`. The archive does not include the raw price series needed
to recalculate Radar's indicators or establish which narrative is correct.

## Verify the Radar side

The `protocol_hash` in `radar.json` is reproducible from the payload: run the
"Now do it on a live response" recipe from the repo README on the file's `data`
object, since `radar.json` keeps the whole envelope and the recipe reads the
`--json` dump, which is `data` alone. It is a `v2.1.0-radar` seal, so the
recipe hashes its `z_score` as a plain number.

`python agent.py coin bitcoin --json` gives you today's Radar read, not this
one: the engine and the market have both moved since 2026-07-20.

## Notes on fidelity

The two raw replies are transcribed as rendered (Gemini's LaTeX for the band
sigmas is written out as plain text). Model versions are pinned above on purpose:
model behavior drifts over time, and that is the point of the comparison. The raw
answers are not reproducible. Only the eight fields covered by Radar's process
seal can be compared with its digest here; its narrative and source contents
are outside that coverage.
