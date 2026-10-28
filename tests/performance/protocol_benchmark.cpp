#include "core/protocols/elm.hpp"
#include <algorithm>
#include <chrono>
#include <iostream>
#include <vector>
int main() {
    std::vector<double> microseconds;
    microseconds.reserve(10000);
    double result = 0;
    for (int i = 0; i < 10000; ++i) {
        auto start = std::chrono::steady_clock::now();
        auto m = cda::decodePid(12, "7E8 04 41 0C 1A F8 00 00 00>");
        result += *m.value;
        auto end = std::chrono::steady_clock::now();
        microseconds.push_back(std::chrono::duration<double, std::micro>(end - start).count());
    }
    if (result != 17260000)
        return 1;
    std::sort(microseconds.begin(), microseconds.end());
    std::cout << "{\"workload\":\"10000 fixed framed RPM decodes; no "
                 "hardware/network/AI\",\"unit\":\"microseconds\",\"p50\":"
              << microseconds[5000] << ",\"p95\":" << microseconds[9500]
              << ",\"p99\":" << microseconds[9900] << "}\n";
    return 0;
}
