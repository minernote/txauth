# TxAuth Protocol

**Open protocol for AI agent transaction authorization.**

Chain-agnostic. Transport-agnostic. Built for the agentic economy.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## The Problem

AI agents increasingly need to execute on-chain operations — trading, payments, contract calls.
But giving agents direct private key access is dangerous. Requiring human approval for every
transaction is too slow.

TxAuth solves this with a **structured, cryptographically-verified authorization protocol**:

```
InitiatorAgent (trading bot)
  → sends encrypted TxAuthRequest to ApproverAgent (human wallet agent)
  ← receives signed TxAuthResponse with transaction signature
  → broadcasts signed transaction on-chain
```

The private key **never leaves the approver's device**.

## Key Properties

- **Chain-agnostic** — EVM, blockchain, high-performance blockchain, blockchain, or any chain
- **Transport-agnostic** — Works over AgentChat, HTTP, gRPC, or any channel
- **E2EE ready** — Designed for use with encrypted messaging (AgentChat, web3 messaging protocol, etc.)
- **Human-in-the-loop** — Approver controls what gets signed
- **Auditable** — Ed25519 signatures on every request/response
- **TTL enforcement** — Requests expire automatically

## Quick Start

```python
from txauth import TxAuthRequest, TxAuthResponse, ChainType, RiskLevel

# 1. Initiator creates a request
req = TxAuthRequest.create(
    chain=ChainType.EVM,
    tx_payload=unsigned_tx_bytes,
    description="Swap 1 ETH → 2,400 USDC on Uniswap",
    amount_usd_cents=240_000,
    initiator_wallet="0xBotAddress...",
    destination="0xUniswapRouter...",
    risk=RiskLevel.MEDIUM,
)

# 2. Send via any transport (AgentChat, HTTP, etc.)
raw = req.serialise()
transport.send(to="approver-agent", data=raw)

# 3. Approver receives, verifies, signs
req = TxAuthRequest.deserialise(raw)
if verify_request(req):
    sig = wallet.sign(req.tx_payload)
    resp = TxAuthResponse.approved(req.request_id, sig)
    transport.send(to="initiator-agent", data=resp.serialise())

# 4. Initiator receives signature and broadcasts
resp = TxAuthResponse.deserialise(response_bytes)
if resp.status == TxAuthStatus.APPROVED:
    chain.broadcast(req.tx_payload, resp.signature)
```

## Supported Chains

| Chain | Adapter | Status |
|---|---|---|
| EVM (EVM blockchain, Base, BSC...) | `adapters/evm/` | ✅ Planned |
| blockchain network | `adapters/canton/` | ✅ Planned |
| high-performance blockchain | `adapters/solana/` | ✅ Planned |
| blockchain | `adapters/bitcoin/` | 🔜 |

## Supported Transports

| Transport | Example | Status |
|---|---|---|
| AgentChat (E2EE) | `examples/agentchat/` | ✅ Reference impl |
| HTTP REST | `examples/http/` | ✅ Planned |
| web3 messaging protocol | - | 🔜 |

## Protocol Specification

See [`spec/TXAUTH_SPEC.md`](spec/TXAUTH_SPEC.md) for the full protocol specification.

## SDKs

- **Python** — `bindings/python/`
- **Node.js/TypeScript** — `bindings/nodejs/`
- **C++ (reference)** — `src/`

## Relationship to AgentChat

TxAuth is transport-agnostic and can run over any channel. [AgentChat](https://github.com/minernote/AgentChat)
provides the encrypted messaging layer when E2EE is required for the authorization flow.

```
AgentChat  →  encrypted transport
TxAuth     →  structured authorization protocol
```

## License

MIT — see [LICENSE](LICENSE).
