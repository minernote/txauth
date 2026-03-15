// TxAuth Protocol — C++ reference implementation
// See spec/TXAUTH_SPEC.md for full specification
#pragma once
#include <cstdint>
#include <string>
#include <vector>
#include <array>
#include <optional>

namespace txauth {

enum class ChainType   : uint8_t { EVM=0x01, CANTON=0x02, SOLANA=0x03, BITCOIN=0x04, GENERIC=0xFF };
enum class TxAuthStatus: uint8_t { PENDING=0x01, APPROVED=0x02, REJECTED=0x03, EXPIRED=0x04, BROADCAST=0x05 };

struct TxAuthRequest {
    std::array<uint8_t,16> request_id{};
    ChainType chain{ChainType::GENERIC};
    std::vector<uint8_t> tx_payload;
    std::string description;
    uint64_t amount_usd_cents{0};
    uint64_t expires_at_ms{0};
    std::string initiator_wallet;
    std::string destination;
    enum class Risk : uint8_t { LOW=1,MEDIUM=2,HIGH=3,CRITICAL=4 } risk{Risk::MEDIUM};

    std::vector<uint8_t> serialise() const;
    static std::optional<TxAuthRequest> deserialise(const std::vector<uint8_t>&);
    bool is_expired() const;
};

struct TxAuthResponse {
    std::array<uint8_t,16> request_id{};
    TxAuthStatus status{TxAuthStatus::PENDING};
    std::vector<uint8_t> signature;
    std::string rejection_reason;
    uint64_t approved_at_ms{0};

    std::vector<uint8_t> serialise() const;
    static std::optional<TxAuthResponse> deserialise(const std::vector<uint8_t>&);
};

std::array<uint8_t,16> generate_request_id();

} // namespace txauth
