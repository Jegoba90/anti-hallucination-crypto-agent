from .audit import AuditSummary, parse_audit_trail
from .client import (
    DEMO_API_KEY,
    ApiError,
    CryptoCapiClient,
    DemoCoinRestricted,
    ProEngineRequired,
    UnexpectedResponse,
    resolve_api_key,
)
from .seal import SealCheck, SealStatus, check_seal
from .models import (
    AuditTrail,
    InsightData,
    MarketSummary,
    PriceItem,
    ScanResult,
    SignalResult,
)

__all__ = [
    "CryptoCapiClient",
    "DEMO_API_KEY",
    "InsightData",
    "AuditTrail",
    "ScanResult",
    "SignalResult",
    "PriceItem",
    "MarketSummary",
    "parse_audit_trail",
    "check_seal",
    "SealCheck",
    "SealStatus",
    "resolve_api_key",
    "AuditSummary",
    # The four things the client raises. This package is meant to be copied into
    # someone else's project, so the errors they have to catch belong on the front
    # door: reaching into cryptocapi.client for them is a hole, not a design.
    "DemoCoinRestricted",
    "ProEngineRequired",
    "ApiError",
    "UnexpectedResponse",
]
