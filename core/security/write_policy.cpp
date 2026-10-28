#include "core/security/write_policy.hpp"
#include <cmath>
namespace cda {
SafetyDecision validateWrite(const WriteContext &c, std::chrono::system_clock::time_point now) {
    SafetyDecision d;
    auto require = [&](bool b, const char *reason) {
        if (!b)
            d.failures.emplace_back(reason);
    };
    require(c.mode == Mode::Customer, "Professional CUSTOMER permission required");
    require(c.consent && c.confirmed,
            "Explicit operation-specific consent and confirmation required");
    require(c.vehicleVerified && !c.vehicle.empty(), "Verified vehicle required");
    require(c.ecuVerified && !c.ecu.empty(), "Verified ECU required");
    require(!c.account.empty(), "Authenticated account required");
    require(c.operation == "clear_dtcs", "Operation not whitelisted");
    require(c.adapterSupportsClear && c.ecuSupportsClear, "Adapter and ECU capability required");
    require(c.ignitionOn && c.engineOff && c.stationary,
            "Stationary ignition-on engine-off state required");
    require(c.voltageMeasured && std::isfinite(c.voltage) && c.voltage >= 12.0 && c.voltage <= 15.0,
            "Verified safe voltage required");
    require(c.measuredAt <= now && now - c.measuredAt <= std::chrono::seconds(5),
            "Operating state missing, future or stale");
    require(c.auditAvailable, "Durable audit required");
    d.allowed = d.failures.empty();
    return d;
}
} // namespace cda
