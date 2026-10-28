#include "core/security/crypto.hpp"
#include <memory>
#include <openssl/crypto.h>
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <stdexcept>
namespace cda {
Blob randomBytes(size_t size) {
    if (size == 0 || size > 4096)
        throw std::invalid_argument("Invalid entropy request");
    Blob b(size);
    if (RAND_bytes(b.data(), static_cast<int>(size)) != 1)
        throw std::runtime_error("Secure random unavailable");
    return b;
}
Blob sha256(std::span<const unsigned char> input) {
    Blob out(32);
    unsigned n = 0;
    if (EVP_Digest(input.data(), input.size(), out.data(), &n, EVP_sha256(), nullptr) != 1 ||
        n != 32)
        throw std::runtime_error("SHA256 unavailable");
    return out;
}
Blob passwordKey(const std::string &password, std::span<const unsigned char> salt) {
    if (password.size() < 12 || password.size() > 256 || salt.size() != 16)
        throw std::invalid_argument("Password requires 12-256 UTF-8 bytes and valid salt");
    Blob key(32);
    if (EVP_PBE_scrypt(password.data(), password.size(), salt.data(), salt.size(), 16384, 8, 1,
                       64 * 1024 * 1024, key.data(), key.size()) != 1)
        throw std::runtime_error("Password hashing unavailable");
    return key;
}
bool constantEqual(std::span<const unsigned char> a, std::span<const unsigned char> b) {
    return a.size() == b.size() && CRYPTO_memcmp(a.data(), b.data(), a.size()) == 0;
}
bool verifyEd25519(std::span<const unsigned char> key, std::span<const unsigned char> payload,
                   std::span<const unsigned char> signature) {
    if (key.size() != 32 || signature.size() != 64)
        return false;
    std::unique_ptr<EVP_PKEY, decltype(&EVP_PKEY_free)> p(
        EVP_PKEY_new_raw_public_key(EVP_PKEY_ED25519, nullptr, key.data(), key.size()),
        EVP_PKEY_free);
    std::unique_ptr<EVP_MD_CTX, decltype(&EVP_MD_CTX_free)> c(EVP_MD_CTX_new(), EVP_MD_CTX_free);
    return p && c && EVP_DigestVerifyInit(c.get(), nullptr, nullptr, nullptr, p.get()) == 1 &&
           EVP_DigestVerify(c.get(), signature.data(), signature.size(), payload.data(),
                            payload.size()) == 1;
}
} // namespace cda
