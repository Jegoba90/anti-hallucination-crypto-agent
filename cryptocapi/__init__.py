from .audit import AuditSummary, parse_audit_trail
from .client import (
    DEMO_API_KEY,
    CryptoCapiClient,
    DemoCoinRestricted,
    ProEngineRequired,
    UnexpectedResponse,
    resolve_api_key,
)
from .models import AuditTrail, InsightData, ScanResult, SignalResult

__all__ = [
    "CryptoCapiClient",
    "DEMO_API_KEY",
    "InsightData",
    "AuditTrail",
    "ScanResult",
    "SignalResult",
    "parse_audit_trail",
    "resolve_api_key",
    "AuditSummary",
    # The three things the client raises. This package is meant to be copied into
    # someone else's project, so the errors they have to catch belong on the front
    # door: reaching into cryptocapi.client for them is a hole, not a design.
    "DemoCoinRestricted",
    "ProEngineRequired",
    "UnexpectedResponse",
]
