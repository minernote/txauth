"""
agentchat.tx_auth — Chain Transaction Authorization via E2EE AgentChat messages

Example usage (blockchain network Featured App scenario):

    from agentchat import AgentChatClient
    from txauth import TxAuthRequest, TxAuthClient, ChainType

    # Initiator agent requests approval from human-controlled approver agent
    client = AgentChatClient(server="localhost:8765", agent_id="perpdex-bot")

    tx_client = TxAuthClient(client)
    response = tx_client.request_approval(
        peer_agent_id="owner-wallet-agent",
        chain=ChainType.CANTON,
        tx_payload=daml_command_bytes,
        description="Open USDC/ETH perpetual position — $5,000 notional",
        amount_usd_cents=500_000,  # $5,000
        ttl_seconds=300,           # 5 minute expiry
        risk="HIGH",
    )

    if response.status == "APPROVED":
        # Broadcast the signed transaction on-chain
        broadcast(response.signature)
"""

from __future__ import annotations
import os
import struct
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional


class ChainType(IntEnum):
    EVM     = 0x01
    CANTON  = 0x02
    SOLANA  = 0x03
    BITCOIN = 0x04
    GENERIC = 0xFF


class TxAuthStatus(IntEnum):
    PENDING   = 0x01
    APPROVED  = 0x02
    REJECTED  = 0x03
    EXPIRED   = 0x04
    BROADCAST = 0x05


class RiskLevel(IntEnum):
    LOW      = 1
    MEDIUM   = 2
    HIGH     = 3
    CRITICAL = 4


@dataclass
class TxAuthRequest:
    request_id: bytes          # 16 bytes random
    chain: ChainType
    tx_payload: bytes          # raw unsigned transaction
    description: str
    amount_usd_cents: int = 0
    expires_at_ms: int = 0
    initiator_wallet: str = ""
    destination: str = ""
    risk: RiskLevel = RiskLevel.MEDIUM

    @staticmethod
    def create(
        chain: ChainType,
        tx_payload: bytes,
        description: str,
        amount_usd_cents: int = 0,
        ttl_seconds: int = 300,
        initiator_wallet: str = "",
        destination: str = "",
        risk: RiskLevel = RiskLevel.MEDIUM,
    ) -> "TxAuthRequest":
        request_id = os.urandom(16)
        expires_at_ms = int((time.time() + ttl_seconds) * 1000) if ttl_seconds > 0 else 0
        return TxAuthRequest(
            request_id=request_id,
            chain=chain,
            tx_payload=tx_payload,
            description=description,
            amount_usd_cents=amount_usd_cents,
            expires_at_ms=expires_at_ms,
            initiator_wallet=initiator_wallet,
            destination=destination,
            risk=risk,
        )

    def is_expired(self) -> bool:
        if self.expires_at_ms == 0:
            return False
        return int(time.time() * 1000) > self.expires_at_ms

    def serialise(self) -> bytes:
        """Serialise to bytes for E2EE transmission."""
        def pack_str(s: str) -> bytes:
            b = s.encode("utf-8")
            return struct.pack(">H", len(b)) + b

        def pack_bytes(b: bytes) -> bytes:
            return struct.pack(">I", len(b)) + b

        return (
            bytes([self.chain.value])
            + self.request_id
            + pack_bytes(self.tx_payload)
            + pack_str(self.description)
            + struct.pack(">Q", self.amount_usd_cents)
            + struct.pack(">Q", self.expires_at_ms)
            + pack_str(self.initiator_wallet)
            + pack_str(self.destination)
            + bytes([self.risk.value])
        )

    @classmethod
    def deserialise(cls, data: bytes) -> "TxAuthRequest":
        off = 0
        chain = ChainType(data[off]); off += 1
        request_id = data[off:off+16]; off += 16

        def read_bytes() -> bytes:
            nonlocal off
            length = struct.unpack_from(">I", data, off)[0]; off += 4
            b = data[off:off+length]; off += length
            return b

        def read_str() -> str:
            nonlocal off
            length = struct.unpack_from(">H", data, off)[0]; off += 2
            s = data[off:off+length].decode("utf-8"); off += length
            return s

        tx_payload = read_bytes()
        description = read_str()
        amount_usd_cents = struct.unpack_from(">Q", data, off)[0]; off += 8
        expires_at_ms = struct.unpack_from(">Q", data, off)[0]; off += 8
        initiator_wallet = read_str()
        destination = read_str()
        risk = RiskLevel(data[off])

        return cls(
            request_id=request_id,
            chain=chain,
            tx_payload=tx_payload,
            description=description,
            amount_usd_cents=amount_usd_cents,
            expires_at_ms=expires_at_ms,
            initiator_wallet=initiator_wallet,
            destination=destination,
            risk=risk,
        )


@dataclass
class TxAuthResponse:
    request_id: bytes
    status: TxAuthStatus
    signature: bytes = b""
    rejection_reason: str = ""
    approved_at_ms: int = 0

    def serialise(self) -> bytes:
        def pack_bytes(b: bytes) -> bytes:
            return struct.pack(">I", len(b)) + b

        def pack_str(s: str) -> bytes:
            b = s.encode("utf-8")
            return struct.pack(">H", len(b)) + b

        return (
            self.request_id
            + bytes([self.status.value])
            + pack_bytes(self.signature)
            + pack_str(self.rejection_reason)
            + struct.pack(">Q", self.approved_at_ms)
        )

    @classmethod
    def deserialise(cls, data: bytes) -> "TxAuthResponse":
        off = 0
        request_id = data[off:off+16]; off += 16
        status = TxAuthStatus(data[off]); off += 1

        length = struct.unpack_from(">I", data, off)[0]; off += 4
        signature = data[off:off+length]; off += length

        str_len = struct.unpack_from(">H", data, off)[0]; off += 2
        rejection_reason = data[off:off+str_len].decode("utf-8"); off += str_len

        approved_at_ms = struct.unpack_from(">Q", data, off)[0]

        return cls(
            request_id=request_id,
            status=status,
            signature=signature,
            rejection_reason=rejection_reason,
            approved_at_ms=approved_at_ms,
        )


class TxAuthClient:
    """
    High-level client for chain transaction authorization via AgentChat E2EE.

    Wraps the AgentChatClient to send/receive TxAuthRequest and TxAuthResponse
    messages with automatic serialisation and E2EE encryption.
    """

    # AgentChat MessageType for TxAuth (uses AGENT_COMMAND = 0x04)
    TX_AUTH_PREFIX = b"\x00TXAUTH\x00"

    def __init__(self, client):
        """client: an agentchat.AgentChatClient instance"""
        self.client = client
        self._pending: dict[bytes, TxAuthRequest] = {}

    def send_request(
        self,
        peer_agent_id: str,
        request: TxAuthRequest,
    ) -> bool:
        """Send a TxAuthRequest to the peer agent via E2EE."""
        payload = self.TX_AUTH_PREFIX + b"REQ" + request.serialise()
        self._pending[request.request_id] = request
        return self.client.send_command(
            recipient_id=peer_agent_id,
            message=payload.hex(),  # hex-encode for transport
        )

    def send_response(self, peer_agent_id: str, response: TxAuthResponse) -> bool:
        """Send a TxAuthResponse back to the initiator via E2EE."""
        payload = self.TX_AUTH_PREFIX + b"RSP" + response.serialise()
        return self.client.send_command(
            recipient_id=peer_agent_id,
            message=payload.hex(),
        )

    def parse_message(self, raw: str) -> Optional[TxAuthRequest | TxAuthResponse]:
        """Parse an incoming AgentChat message as TxAuth payload."""
        try:
            data = bytes.fromhex(raw)
        except ValueError:
            return None

        if not data.startswith(self.TX_AUTH_PREFIX):
            return None

        kind = data[len(self.TX_AUTH_PREFIX):len(self.TX_AUTH_PREFIX)+3]
        payload = data[len(self.TX_AUTH_PREFIX)+3:]

        if kind == b"REQ":
            return TxAuthRequest.deserialise(payload)
        elif kind == b"RSP":
            return TxAuthResponse.deserialise(payload)
        return None

    def approve_request(self, request: TxAuthRequest, signature: bytes) -> TxAuthResponse:
        """Create an approval response with a chain signature."""
        return TxAuthResponse(
            request_id=request.request_id,
            status=TxAuthStatus.APPROVED,
            signature=signature,
            approved_at_ms=int(time.time() * 1000),
        )

    def reject_request(self, request: TxAuthRequest, reason: str = "") -> TxAuthResponse:
        """Create a rejection response."""
        return TxAuthResponse(
            request_id=request.request_id,
            status=TxAuthStatus.REJECTED,
            rejection_reason=reason,
            approved_at_ms=int(time.time() * 1000),
        )
