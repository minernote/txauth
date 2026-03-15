"""
txauth — Open protocol for AI agent transaction authorization.

Chain-agnostic. Transport-agnostic.
"""

from .tx_auth import (
    TxAuthRequest,
    TxAuthResponse,
    TxAuthStatus,
    ChainType,
    RiskLevel,
    TxAuthClient,
)

__version__ = "0.1.0"
__all__ = [
    "TxAuthRequest",
    "TxAuthResponse",
    "TxAuthStatus",
    "ChainType",
    "RiskLevel",
    "TxAuthClient",
]
