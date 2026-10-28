#pragma once
#include "core/interfaces/contracts.hpp"
#include <cstdint>
#include <map>
#include <string>
#include <vector>
namespace cda {
using Bytes = std::vector<uint8_t>;
std::vector<Bytes> parseElm(const std::string &reply);
Bytes pidData(uint8_t pid, const std::string &reply);
Measurement decodePid(uint8_t pid, const std::string &reply);
std::vector<std::string> troubleCodes(const std::string &reply, uint8_t service = 0x43);
std::vector<unsigned> supportedPids(unsigned page, const Bytes &data);
bool allowedReadCommand(const std::string &command);
} // namespace cda
