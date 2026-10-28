#pragma once
#include "core/security/crypto.hpp"
#include <array>
#include <charconv>
#include <stdexcept>
#include <string_view>
namespace cda {
inline std::array<unsigned, 3> version(std::string_view s) {
    std::array<unsigned, 3> out{};
    for (unsigned i = 0; i < 3; ++i) {
        const auto pos = s.find('.');
        auto part = s.substr(0, pos);
        if (part.empty() || (part.size() > 1 && part[0] == '0'))
            throw std::invalid_argument("Invalid version");
        auto r = std::from_chars(part.data(), part.data() + part.size(), out[i]);
        if (r.ec != std::errc{} || r.ptr != part.data() + part.size())
            throw std::invalid_argument("Invalid version");
        if (i < 2) {
            if (pos == std::string_view::npos)
                throw std::invalid_argument("Invalid version");
            s.remove_prefix(pos + 1);
        } else if (pos != std::string_view::npos)
            throw std::invalid_argument("Invalid version");
    }
    return out;
}
inline bool newerVersion(std::string_view installed, std::string_view released) {
    return version(released) > version(installed);
}
} // namespace cda
