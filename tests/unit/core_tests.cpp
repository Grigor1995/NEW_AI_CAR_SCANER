#include "core/ai/evidence.hpp"
#include "core/protocols/elm.hpp"
#include "core/security/crypto.hpp"
#include "core/security/write_policy.hpp"
#include "core/telemetry/units.hpp"
#include "services/monitoring/eligibility.hpp"
#include "services/updates/manifest.hpp"
#include <cmath>
#include <functional>
#include <iostream>
#include <limits>
#include <openssl/evp.h>
#include <random>
#include <stdexcept>
using namespace cda;
namespace {
int passed = 0, failed = 0;
void check(bool b) {
    if (!b)
        throw std::runtime_error("Assertion failed");
}
void near(double a, double b) {
    check(std::abs(a - b) < 1e-6);
}
void test(const char *name, const std::function<void()> &f) {
    try {
        f();
        ++passed;
        std::cout << "PASS " << name << '\n';
    } catch (const std::exception &e) {
        ++failed;
        std::cerr << "FAIL " << name << ": " << e.what() << '\n';
    }
}
void rejects(const std::function<void()> &f) {
    bool caught = false;
    try {
        f();
    } catch (const std::invalid_argument &) {
        caught = true;
    }
    check(caught);
}
} // namespace
int main() {
    test("headerless RPM and engineering values", [] {
        near(*decodePid(12, "41 0C 1A F8>").value, 1726);
        near(*decodePid(5, "41057B>").value, 83);
        near(*decodePid(13, "410D32>").value, 50);
    });
    test("11 and 29 bit framed PID responses", [] {
        near(*decodePid(12, "7E8 04 41 0C 1A F8 00 00 00>").value, 1726);
        near(*decodePid(12, "7E804410C1AF8000000>").value, 1726);
        near(*decodePid(12, "18DAF11004410C1AF8000000>").value, 1726);
        near(*decodePid(12, "18DAF110 04 41 0C 1A F8 00 00 00>").value, 1726);
    });
    test("malformed and wrong-PID responses are never valid measurements", [] {
        for (auto s : {"410C1A>", "420C1AF8>", "410D32>", "410CGGFF>", "7E8 07 41 0C 1A>"}) {
            auto m = decodePid(12, s);
            check(!m.value && m.quality == Quality::Invalid);
        }
    });
    test("availability is separate from unsupported", [] {
        check(decodePid(12, "NO DATA>").quality == Quality::Unavailable);
        check(decodePid(0xff, "").quality == Quality::Unsupported);
    });
    test("multi ECU DTCs deduplicate", [] {
        auto codes = troubleCodes("7E8 03 43 03 02 00 00 00\r7E9 05 43 03 02 01 71 00 00>");
        check(codes == std::vector<std::string>{"P0302", "P0171"});
    });
    test("wrong service and truncated DTC rejected", [] {
        rejects([] { troubleCodes("440000>"); });
        rejects([] { troubleCodes("4303>"); });
    });
    test("ISO-TP reassembly with sequence validation", [] {
        auto p = parseElm("7E8 10 0A 49 02 01 41 42 43\r7E8 21 44 45 46 47 00 00 00>");
        check(p[0].size() == 10 && p[0][9] == 'G');
        rejects([] { parseElm("7E8 10 0A 49 02 01 41 42 43\r7E8 22 44 45 46 47>"); });
        rejects([] { parseElm("7E8 10 0A 49 02 01 41 42 43>"); });
    });
    test("empty adapter errors and limits", [] {
        for (auto s : {"", ">", "?", "CAN ERROR", "NO DATA", "7E8 00", "7E8 2F 01"})
            rejects([&] { parseElm(s); });
        rejects([] { parseElm(std::string(65537, 'A')); });
    });
    test("bitmap PID boundaries", [] {
        check(supportedPids(0, {0x80, 0, 0, 1}) == std::vector<unsigned>{1, 32});
        check(supportedPids(32, {0x80, 0, 0, 0}) == std::vector<unsigned>{33});
        rejects([] { supportedPids(1, {0, 0, 0, 0}); });
        rejects([] { supportedPids(0, {0}); });
    });
    test("read allowlist excludes injection and ECU modification", [] {
        for (auto c : {"010C", "0202", "0902", "03", "07", "0A", "ATSP6", "ATCAF1"})
            check(allowedReadCommand(c));
        for (auto c : {"04", "2E123400", "3101", "ATSH7E0", "010C\r04", "010G", "ATSPZ"})
            check(!allowedReadCommand(c));
    });
    test("unit conversion dimensions and round trips", [] {
        for (const auto &p : std::vector<std::pair<std::string, std::string>>{{"km/h", "mph"},
                                                                              {"km", "mi"},
                                                                              {"C", "F"},
                                                                              {"kPa", "psi"},
                                                                              {"kPa", "bar"},
                                                                              {"Nm", "lb-ft"},
                                                                              {"kW", "hp"},
                                                                              {"L", "gal-US"},
                                                                              {"cc", "L-engine"},
                                                                              {"g/s", "lb/min"},
                                                                              {"L/100km", "mpg-US"},
                                                                              {"L/100km", "mpg-UK"},
                                                                              {"L/100km", "km/L"}})
            near(convert(convert(17, p.first, p.second), p.second, p.first), 17);
        near(convert(0, "C", "F"), 32);
        near(convert(100, "km/h", "mph"), 62.1371192237);
        near(convert(10, "L/100km", "mpg-US"), 23.5214583);
    });
    test("invalid conversions rejected", [] {
        rejects([] { convert(1, "C", "km"); });
        rejects([] { convert(0, "L/100km", "mpg-US"); });
        rejects([] { convert(std::numeric_limits<double>::infinity(), "km", "mi"); });
    });
    test("safe clear policy requires every prerequisite", [] {
        const auto now = std::chrono::system_clock::now();
        WriteContext good;
        good.mode = Mode::Customer;
        good.consent = good.confirmed = good.vehicleVerified = good.ecuVerified =
            good.adapterSupportsClear = good.ecuSupportsClear = good.ignitionOn = good.engineOff =
                good.stationary = good.voltageMeasured = good.auditAvailable = true;
        good.voltage = 13;
        good.account = "actor";
        good.vehicle = "verified-vehicle";
        good.ecu = "verified-ecu";
        good.operation = "clear_dtcs";
        good.measuredAt = now;
        check(validateWrite(good, now).allowed);
        std::vector<std::function<void(WriteContext &)>> unsafe = {
            [](auto &c) { c.mode = Mode::User; },
            [](auto &c) { c.mode = Mode::Admin; },
            [](auto &c) { c.consent = false; },
            [](auto &c) { c.confirmed = false; },
            [](auto &c) { c.vehicleVerified = false; },
            [](auto &c) { c.ecuVerified = false; },
            [](auto &c) { c.adapterSupportsClear = false; },
            [](auto &c) { c.ecuSupportsClear = false; },
            [](auto &c) { c.ignitionOn = false; },
            [](auto &c) { c.engineOff = false; },
            [](auto &c) { c.stationary = false; },
            [](auto &c) { c.voltageMeasured = false; },
            [](auto &c) { c.voltage = 11.9; },
            [](auto &c) { c.voltage = 15.1; },
            [](auto &c) { c.voltage = NAN; },
            [](auto &c) { c.auditAvailable = false; },
            [](auto &c) { c.account.clear(); },
            [](auto &c) { c.vehicle.clear(); },
            [](auto &c) { c.ecu.clear(); },
            [](auto &c) { c.operation = "flash"; },
            [](auto &c) { c.measuredAt -= std::chrono::seconds(6); },
            [](auto &c) { c.measuredAt += std::chrono::seconds(1); }};
        for (auto &mutate : unsafe) {
            auto context = good;
            mutate(context);
            auto d = validateWrite(context, now);
            check(!d.allowed && !d.failures.empty());
        }
        check(!validateWrite(WriteContext{}, now).allowed);
    });
    test("scrypt salts, wrong password and bounded input", [] {
        auto salt = randomBytes(16);
        auto a = passwordKey("a long test password", salt);
        check(constantEqual(a, passwordKey("a long test password", salt)));
        check(!constantEqual(a, passwordKey("a wrong test password", salt)));
        check(!constantEqual(a, passwordKey("a long test password", randomBytes(16))));
        rejects([] { passwordKey("short", Blob(16)); });
        rejects([] { randomBytes(0); });
        check(sha256(Blob{}).size() == 32);
    });
    test("real Ed25519 signature verification and tamper denial", [] {
        EVP_PKEY_CTX *ctx = EVP_PKEY_CTX_new_id(EVP_PKEY_ED25519, nullptr);
        EVP_PKEY *key = nullptr;
        check(ctx && EVP_PKEY_keygen_init(ctx) == 1 && EVP_PKEY_keygen(ctx, &key) == 1);
        EVP_PKEY_CTX_free(ctx);
        Blob publicKey(32), sig(64), payload = {'v', '1'};
        size_t n = publicKey.size();
        check(EVP_PKEY_get_raw_public_key(key, publicKey.data(), &n) == 1);
        auto *md = EVP_MD_CTX_new();
        check(EVP_DigestSignInit(md, nullptr, nullptr, nullptr, key) == 1);
        n = sig.size();
        check(EVP_DigestSign(md, sig.data(), &n, payload.data(), payload.size()) == 1);
        EVP_MD_CTX_free(md);
        EVP_PKEY_free(key);
        check(verifyEd25519(publicKey, payload, sig));
        payload[0] ^= 1;
        check(!verifyEd25519(publicKey, payload, sig));
        check(!verifyEd25519(Blob(1), payload, sig));
    });
    test("strict version ordering", [] {
        check(newerVersion("1.9.9", "2.0.0"));
        check(!newerVersion("1.0.0", "1.0.0"));
        check(!newerVersion("2.0.0", "1.0.0"));
        for (auto s : {"1.0", "1.0.0.1", "01.0.0", "1.a.0", "1.0.-1"})
            rejects([&] { version(s); });
    });
    test("scheduled scans are never fabricated", [] {
        check(eligibleScan({}) == ScanState::Deferred);
        check(eligibleScan({true, true, true, true}) == ScanState::Scheduled);
        check(eligibleScan({true, true, false, true}) == ScanState::Deferred);
    });
    test("golden LPG P0302 evidence and recalculation", [] {
        DiagnosticSession s;
        s.vehicle = "Mercedes W211 E350 M272";
        s.dtcs = {"P0302"};
        s.evidence = {{"symptom", "petrol_normal_lpg_misfire", Provenance::UserReported},
                      {"dtc", "P0302", Provenance::EcuReported}};
        auto h = analyze(s);
        check(h.size() == 1 && h[0].label.find("LPG") != std::string::npos &&
              h[0].evidenceIds.size() == 2);
        s.record({"compare_fuel_modes", TestResult::Pass});
        h = analyze(s);
        check(std::find(h[0].nextTests.begin(), h[0].nextTests.end(), "compare_fuel_modes") ==
              h[0].nextTests.end());
        s.record({"compare_fuel_modes", TestResult::Fail});
        check(s.results.size() == 1 && analyze(s)[0].label.find("broaden") != std::string::npos);
        check(analyze({}).empty());
    });
    test("bounded malformed protocol stress", [] {
        std::mt19937 rng(7);
        for (int i = 0; i < 1000; ++i) {
            std::string s;
            for (unsigned j = 0, n = rng() % 128; j < n; ++j)
                s += char(rng() % 128);
            try {
                for (auto &p : parseElm(s))
                    check(!p.empty() && p.size() <= 32768);
            } catch (const std::invalid_argument &) {
            }
        }
    });
    std::cout << "RESULT " << passed << " passed, " << failed << " failed\n";
    return failed ? 1 : 0;
}
