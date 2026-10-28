#pragma once
#include "core/interfaces/contracts.hpp"
#include <algorithm>
#include <string>
#include <vector>
namespace cda {
struct Evidence {
    std::string id, observation;
    Provenance source;
};
struct TestResult {
    std::string id;
    enum Outcome { Pass, Fail, Unknown } outcome = Unknown;
};
struct Hypothesis {
    std::string label;
    std::vector<std::string> evidenceIds, nextTests;
};
struct DiagnosticSession {
    std::string vehicle;
    std::vector<Evidence> evidence;
    std::vector<std::string> dtcs;
    std::vector<TestResult> results;
    void record(TestResult r) {
        auto i = std::find_if(results.begin(), results.end(),
                              [&](const auto &t) { return t.id == r.id; });
        if (i == results.end())
            results.push_back(r);
        else
            *i = r;
    }
};
inline std::vector<Hypothesis> analyze(const DiagnosticSession &s) {
    std::vector<Hypothesis> out;
    if (std::find(s.dtcs.begin(), s.dtcs.end(), "P0302") != s.dtcs.end()) {
        Hypothesis h{"Cylinder 2 misfire: cause not yet established",
                     {},
                     {"compare_fuel_modes", "inspect_ignition_professionally"}};
        for (const auto &e : s.evidence) {
            h.evidenceIds.push_back(e.id);
            if (e.observation == "petrol_normal_lpg_misfire" &&
                e.source == Provenance::UserReported) {
                h.label = "Prioritize LPG delivery/calibration checks; ignition and mechanical "
                          "causes remain possible";
                h.nextTests = {"compare_fuel_modes", "lpg_cylinder_balance_professional"};
            }
        }
        for (const auto &r : s.results)
            if (r.outcome != TestResult::Unknown) {
                std::erase(h.nextTests, r.id);
                if (r.id == "compare_fuel_modes" && r.outcome == TestResult::Fail) {
                    h.label = "Fuel-mode comparison did not isolate LPG; broaden ignition and "
                              "mechanical tests";
                    h.nextTests = {"inspect_ignition_professionally",
                                   "compression_test_professional"};
                }
            }
        out.push_back(h);
    }
    return out; // No fault report is not a clean bill of vehicle health.
}
} // namespace cda
