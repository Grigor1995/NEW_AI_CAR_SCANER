#pragma once
namespace cda {
enum class ScanState { Scheduled, Deferred, Running, Completed, Failed, Missed };
struct ScanEligibility {
    bool consent = false, deviceAvailable = false, ignitionOn = false, osAllowsBackground = false;
};
inline ScanState eligibleScan(const ScanEligibility &e) {
    return e.consent && e.deviceAvailable && e.ignitionOn && e.osAllowsBackground
               ? ScanState::Scheduled
               : ScanState::Deferred;
}
} // namespace cda
