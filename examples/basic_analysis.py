"""Minimal example — analyze Bitcoin and print the audit trail.

Usage:
    pip install -r requirements.txt
    python examples/basic_analysis.py

Runs on the public demo key (bitcoin & ethereum) with no setup. To analyze any
other coin, set CRYPTOCAPI_API_KEY in .env to your own sk_live_... key.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from cryptocapi.client import CryptoCapiClient, resolve_api_key
from cryptocapi.audit import parse_audit_trail
from display.terminal import render_insight


async def main() -> None:
    client = CryptoCapiClient(api_key=resolve_api_key())

    data = await client.get_insight("bitcoin")
    render_insight(data, "bitcoin")

    # Access the audit trail directly if you want to process it in code
    math = data.get("math_diagnostics")
    if math:
        audit = parse_audit_trail(math.get("audit_trail"))
        if audit.is_pro and audit.filters:
            print(f"\nFilters that fired: {[f[0] for f in audit.filters]}")
            print(f"Protocol hash: {audit.protocol_hash[:20]}...")


if __name__ == "__main__":
    asyncio.run(main())
