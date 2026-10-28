#pragma once
#include "core/interfaces/contracts.hpp"
#include <chrono>
#include <string>
#include <vector>
namespace cda {
struct WriteContext {
    Mode mode = Mode::User;
    bool consent = false, confirmed = false, vehicleVerified = false, ecuVerified = false;
    bool adapterSupportsClear = false, ecuSupportsClear = false, ignitionOn = false,
         engineOff = false;
    bool stationary = false, voltageMeasured = false, auditAvailable = false;
    double voltage = 0;
    std::string account, vehicle, ecu, operation;
    std::chrono::system_clock::time_point measuredAt{};
};
struct SafetyDecision {
    bool allowed = false;
    std::vector<std::string> failures;
};
SafetyDecision validateWrite(const WriteContext &, std::chrono::system_clock::time_point now);
} // namespace cda
