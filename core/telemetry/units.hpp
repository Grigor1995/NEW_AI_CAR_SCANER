#pragma once
#include <cmath>
#include <stdexcept>
#include <string_view>
namespace cda {
inline double convert(double value, std::string_view from, std::string_view to) {
    if (!std::isfinite(value))
        throw std::invalid_argument("Nonfinite measurement");
    if (from == to)
        return value;
    struct Scale {
        std::string_view unit, dimension;
        double scale, offset;
    };
    constexpr Scale units[] = {{"km/h", "speed", 1, 0},
                               {"mph", "speed", 1.609344, 0},
                               {"km", "distance", 1, 0},
                               {"mi", "distance", 1.609344, 0},
                               {"C", "temperature", 1, 0},
                               {"F", "temperature", 5.0 / 9, -160.0 / 9},
                               {"kPa", "pressure", 1, 0},
                               {"bar", "pressure", 100, 0},
                               {"psi", "pressure", 6.894757293168, 0},
                               {"Nm", "torque", 1, 0},
                               {"lb-ft", "torque", 1.3558179483314, 0},
                               {"kW", "power", 1, 0},
                               {"hp", "power", 0.74569987158227, 0},
                               {"L", "volume", 1, 0},
                               {"gal-US", "volume", 3.785411784, 0},
                               {"cc", "displacement", 1, 0},
                               {"L-engine", "displacement", 1000, 0},
                               {"g/s", "airflow", 1, 0},
                               {"lb/min", "airflow", 7.559872833333, 0}};
    const Scale *a = nullptr, *b = nullptr;
    for (const auto &u : units) {
        if (u.unit == from)
            a = &u;
        if (u.unit == to)
            b = &u;
    }
    if (a && b && a->dimension == b->dimension)
        return (value * a->scale + a->offset - b->offset) / b->scale;
    auto factor = [](std::string_view u) -> double {
        if (u == "mpg-US")
            return 235.214583;
        if (u == "mpg-UK")
            return 282.480936;
        if (u == "km/L")
            return 100;
        return 0;
    };
    if ((from == "L/100km" || factor(from) > 0) && (to == "L/100km" || factor(to) > 0)) {
        if (value <= 0)
            throw std::invalid_argument("Reciprocal fuel conversion requires positive value");
        const double base = from == "L/100km" ? value : factor(from) / value;
        return to == "L/100km" ? base : factor(to) / base;
    }
    throw std::invalid_argument("Incompatible or unsupported units");
}
} // namespace cda
