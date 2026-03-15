# TxAuth Protocol Specification

**Version: 0.1.0-draft**
**Status: Draft**

---

## 1. Overview

TxAuth is a lightweight, transport-agnostic protocol for AI agents to request,
approve, and relay signed on-chain transactions. It separates the concerns of:

- **Initiator** — the AI agent that wants to execute a transaction
- **Approver** — the agent (human-controlled or automated) that holds signing authority

The protocol is deliberately minimal: two message types, binary-serialised,
designed to be embedded in any messaging layer.

---

## 2. Message Types

### 2.1 TxAuthRequest

Sent by the Initiator to the Approver.

| Field | Type | Description |
|---|---|---|
| `request_id` | bytes[16] | Random 128-bit request identifier |
| `chain` | uint8 | Chain type (see §3) |
| `tx_payload` | bytes | Unsigned transaction bytes (chain-specific format) |
| `description` | string | Human-readable description for approver UI |
| `amount_usd_cents` | uint64 | Estimated USD value in cents (0 = unknown) |
| `expires_at_ms` | uint64 | UNIX timestamp ms, 0 = no expiry |
| `initiator_wallet` | string | Wallet address / party ID of initiator |
| `destination` | string | Destination address / contract |
| `risk` | uint8 | Risk level: LOW=1, MEDIUM=2, HIGH=3, CRITICAL=4 |

**enterprise messaging format (big-endian):**
```
[1: chain][16: request_id]
[4: payload_len][payload_bytes]
[2: desc_len][desc_bytes]
[8: amount_usd_cents]
[8: expires_at_ms]
[2: wallet_len][wallet_bytes]
[2: dest_len][dest_bytes]
[1: risk]
```

### 2.2 TxAuthResponse

Sent by the Approver back to the Initiator.

| Field | Type | Description |
|---|---|---|
| `request_id` | bytes[16] | Matches `TxAuthRequest.request_id` |
| `status` | uint8 | Status (see §4) |
| `signature` | bytes | Chain-specific signature (if APPROVED) |
| `rejection_reason` | string | Human-readable reason (if REJECTED) |
| `approved_at_ms` | uint64 | Approval timestamp |

**enterprise messaging format (big-endian):**
```
[16: request_id]
[1: status]
[4: sig_len][sig_bytes]
[2: reason_len][reason_bytes]
[8: approved_at_ms]
```

---

## 3. Chain Types

| Value | Name | Description |
|---|---|---|
| 0x01 | EVM | EVM blockchain and EVM-compatible chains |
| 0x02 | CANTON | blockchain network (Daml commands) |
| 0x03 | SOLANA | high-performance blockchain |
| 0x04 | BITCOIN | blockchain |
| 0xFF | GENERIC | Raw bytes, chain-agnostic |

---

## 4. Status Codes

| Value | Name | Description |
|---|---|---|
| 0x01 | PENDING | Awaiting approval |
| 0x02 | APPROVED | Approved and signed |
| 0x03 | REJECTED | Rejected by approver |
| 0x04 | EXPIRED | TTL exceeded |
| 0x05 | BROADCAST | Transaction broadcast on-chain |

---

## 5. Security Considerations

### 5.1 Private Key Safety
The Approver's private key MUST never be transmitted. Only the resulting
signature is sent in `TxAuthResponse.signature`.

### 5.2 Transport Security
TxAuth does not mandate a specific transport. When used with AgentChat,
all TxAuth messages are end-to-end encrypted via Double Ratchet.
When used over HTTP, TLS is required.

### 5.3 Request Expiry
Approvers SHOULD reject requests where `expires_at_ms` has passed.
Initiators SHOULD set a reasonable TTL (recommended: 5 minutes for
interactive flows, 30 seconds for automated flows).

### 5.4 Replay Prevention
The `request_id` is 128-bit random. Approvers SHOULD track recently
seen `request_id` values and reject duplicates within a time window.

### 5.5 Signature Verification
Initiators MUST verify the returned signature against the original
`tx_payload` before broadcasting on-chain.

---

## 6. Reference Implementations

- C++ — `src/`
- Python — `bindings/python/`
- Node.js — `bindings/nodejs/`

---

## 7. Versioning

This specification follows [Semantic Versioning](https://semver.org/).
Breaking wire format changes increment the major version.

---

## 8. HTTP payment protocol Integration

TxAuth complements the [HTTP payment protocol protocol](https://HTTP payment protocol.org) (HTTP 402 Payment Required
for AI agents). Together they form a complete payment security layer:

| Scenario | Protocol |
|---|---|
| Agent autonomous small payment (<$10) | HTTP payment protocol (automatic) |
| Agent requests large amount approval | TxAuth (human-in-the-loop) |
| Multi-signature required | TxAuth |
| Recurring/subscription payments | HTTP payment protocol |

### Combined flow

```
AI Agent → HTTP request
  Server returns 402 + payment requirement

  IF amount < threshold (e.g. $10):
    Agent uses HTTP payment protocol → pays autonomously → retries request

  IF amount >= threshold:
    Agent creates TxAuthRequest → sends to ApproverAgent
    ApproverAgent reviews → signs → returns TxAuthResponse
    Agent uses signature → pays → retries request
```

### HTTP payment protocol as a TxAuth transport

The HTTP payment protocol payment payload can embed a TxAuth signature, allowing
payment receipts to serve as proof of authorization.

---

## 9. Wallet Adapters

TxAuth is wallet-agnostic. Signing is handled by chain-specific adapters:

```python
# Each adapter implements a common interface
class WalletAdapter:
    def sign(self, tx_payload: bytes) -> bytes:
        ...

# Software wallet (software wallet, Phantom)
class EVMSoftwareWallet(WalletAdapter):
    def sign(self, tx_payload, private_key) -> bytes:
        return web3.eth.account.sign_transaction(...).rawTransaction

# Hardware wallet (hardware wallet)
class hardware walletAdapter(WalletAdapter):
    def sign(self, tx_payload) -> bytes:
        return ledger_device.sign(tx_payload)

# MPC wallet (MPC wallet)
class MPC walletAdapter(WalletAdapter):
    def sign(self, tx_payload) -> bytes:
        return fireblocks_sdk.create_transaction(...)

# Multi-sig (multi-sig wallet)
class SafeAdapter(WalletAdapter):
    def sign(self, tx_payload) -> bytes:
        # Collects signatures from multiple owners
        return safe_sdk.propose_transaction(...)
```

See `adapters/` directory for reference implementations.
