# BTC market read, three assistants, 2026-07-20

Captured 2026-07-20 in plain conversational mode, with no live-data tools or
browsing enabled. This is the raw evidence behind the comparison table in the
repo README.

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

## Why volume is not a row in the comparison

The prompt above asks four things; the table in the repo README compares only
three. Volume is left out on purpose: the Radar engine has no volume feed (that
is the Quant Plus engine's job), so putting it in a row would not be a
like-for-like comparison. The models' volume answers are preserved, untouched,
in `chatgpt.txt` and `gemini.txt`.

## Reproduce the Radar side

```bash
python agent.py coin bitcoin --json
```

The `protocol_hash` in `radar.json` is reproducible from the payload; see
"Verify the Hash Yourself" in the repo README for the exact recipe.

## Notes on fidelity

The two raw replies are transcribed as rendered (Gemini's LaTeX for the band
sigmas is written out as plain text). Model versions are pinned above on purpose:
model behavior drifts over time, and that is the point of the comparison. The raw
answers are not reproducible, the sealed one is.
