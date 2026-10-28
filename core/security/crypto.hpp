#pragma once
#include <span>
#include <string>
#include <vector>
namespace cda {
using Blob = std::vector<unsigned char>;
Blob randomBytes(size_t size);
Blob sha256(std::span<const unsigned char> input);
Blob passwordKey(const std::string &password, std::span<const unsigned char> salt);
bool constantEqual(std::span<const unsigned char> a, std::span<const unsigned char> b);
bool verifyEd25519(std::span<const unsigned char> publicKey, std::span<const unsigned char> payload,
                   std::span<const unsigned char> signature);
} // namespace cda
