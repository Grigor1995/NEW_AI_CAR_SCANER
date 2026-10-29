#include "core/protocols/elm.hpp"
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <algorithm>
#include <cmath>
#include <vector>
#ifdef _WIN32
#define CDA_EXPORT __declspec(dllexport)
#else
#define CDA_EXPORT __attribute__((visibility("default")))
#endif
namespace {
QJsonObject snapshot(const QJsonObject &request) {
    static const std::map<std::string, QString> keys{{"rpm", "rpm"},
                                                     {"speed", "speed_kmh"},
                                                     {"coolant", "coolant_c"},
                                                     {"engine_load", "engine_load_percent"},
                                                     {"intake_air", "intake_air_c"},
                                                     {"maf", "maf_gps"},
                                                     {"map", "map_kpa"},
                                                     {"throttle", "throttle_percent"},
                                                     {"stft", "short_fuel_trim_percent"},
                                                     {"ltft", "long_fuel_trim_percent"}};
    QJsonObject values, units, errors;
    for (const auto &pid : cda::livePids()) {
        const auto command = QString("01%1").arg(pid.pid, 2, 16, QChar('0')).toUpper();
        const auto m =
            cda::decodePid(pid.pid, request.value(command).toString("NO DATA").toStdString());
        const auto key = keys.at(pid.name);
        values[key] = m.value ? QJsonValue(*m.value) : QJsonValue();
        units[key] = QString::fromUtf8(pid.unit);
        if (!m.value)
            errors[command] = "PID response unavailable or invalid";
    }
    return {{"values", values},
            {"units", units},
            {"errors", errors},
            {"source", "native_transport_bridge"},
            {"hardware_verified", false}};
}
QJsonObject stats(const QJsonObject &request) {
    struct Sample {
        qint64 at;
        qint64 sequence;
        double value;
    };
    std::vector<Sample> samples;
    for (const auto &item : request["samples"].toArray()) {
        const auto s = item.toObject();
        const auto value = s["value"].toDouble(NAN);
        if (s["quality"].toString() != "INVALID" && std::isfinite(value))
            samples.push_back({s["timestamp_ms"].toInteger(), s["sequence"].toInteger(-1), value});
    }
    std::stable_sort(samples.begin(), samples.end(), [](auto a, auto b) {
        return a.at != b.at ? a.at < b.at : a.sequence < b.sequence;
    });
    QJsonObject out{{"session_id", request["session_id"]},
                    {"pid", request["pid"]},
                    {"count", qint64(samples.size())}};
    if (samples.empty())
        return out;
    double mean = 0, m2 = 0, minimum = samples.front().value, maximum = minimum, deltaSum = 0,
           deltaMax = 0;
    for (size_t i = 0; i < samples.size(); ++i) {
        const double value = samples[i].value, d = value - mean;
        mean += d / double(i + 1);
        m2 += d * (value - mean);
        minimum = std::min(minimum, value);
        maximum = std::max(maximum, value);
        if (i) {
            const auto delta = std::abs(value - samples[i - 1].value);
            deltaSum += delta;
            deltaMax = std::max(deltaMax, delta);
        }
    }
    const auto duration = samples.back().at - samples.front().at;
    out["start_ms"] = samples.front().at;
    out["end_ms"] = samples.back().at;
    out["duration_ms"] = duration;
    out["min_value"] = minimum;
    out["max_value"] = maximum;
    out["mean"] = mean;
    out["stddev"] = samples.size() > 1 ? std::sqrt(m2 / double(samples.size() - 1)) : 0;
    out["mean_abs_delta"] = samples.size() > 1 ? deltaSum / double(samples.size() - 1) : 0;
    out["max_abs_delta"] = deltaMax;
    out["slope_per_second"] =
        duration > 0
            ? QJsonValue((samples.back().value - samples.front().value) * 1000 / double(duration))
            : QJsonValue();
    out["sample_rate_hz"] = duration > 0
                                ? QJsonValue(double(samples.size() - 1) * 1000 / double(duration))
                                : QJsonValue();
    return out;
}
} // namespace
// The result is owned by this thread and valid until its next call. No allocation crosses the ABI.
extern "C" CDA_EXPORT const char *cda_engine_json(const char *operation,
                                                  const char *input) noexcept {
    thread_local QByteArray output;
    try {
        if (!operation || !input)
            throw std::invalid_argument("Null input");
        const QByteArray data(input);
        if (data.size() > 16 * 1024 * 1024)
            throw std::invalid_argument("Input limit exceeded");
        QJsonParseError error;
        const auto doc = QJsonDocument::fromJson(data, &error);
        if (error.error != QJsonParseError::NoError || !doc.isObject())
            throw std::invalid_argument("JSON object required");
        QJsonObject result;
        if (QByteArray(operation) == "decode_snapshot")
            result = snapshot(doc.object());
        else if (QByteArray(operation) == "compute_stats")
            result = stats(doc.object());
        else
            throw std::invalid_argument("Unknown native operation");
        output = QJsonDocument(result).toJson(QJsonDocument::Compact);
    } catch (const std::exception &e) {
        output = QJsonDocument(QJsonObject{{"error", e.what()}}).toJson(QJsonDocument::Compact);
    } catch (...) {
        output = "{\"error\":\"Native operation failed\"}";
    }
    return output.constData();
}

// Packed numeric ABI avoids JSON parsing for high-volume telemetry batches.
extern "C" CDA_EXPORT int cda_stats_binary(const int64_t *times, const int64_t *sequences,
                                           const double *values, size_t count, double *out,
                                           int64_t *bounds) noexcept {
    if ((!times || !sequences || !values) && count)
        return -1;
    if (!out || !bounds || count > 1000000)
        return -1;
    try {
        std::vector<size_t> order(count);
        for (size_t i = 0; i < count; ++i) {
            if (!std::isfinite(values[i]))
                return -2;
            order[i] = i;
        }
        std::stable_sort(order.begin(), order.end(), [&](size_t a, size_t b) {
            return times[a] != times[b] ? times[a] < times[b] : sequences[a] < sequences[b];
        });
        std::fill(out, out + 9, 0.0);
        bounds[0] = bounds[1] = 0;
        if (!count)
            return 0;
        double mean = 0, m2 = 0, minimum = values[order[0]], maximum = minimum, deltaSum = 0,
               deltaMax = 0;
        for (size_t i = 0; i < count; ++i) {
            auto value = values[order[i]];
            auto delta = value - mean;
            mean += delta / double(i + 1);
            m2 += delta * (value - mean);
            minimum = std::min(minimum, value);
            maximum = std::max(maximum, value);
            if (i) {
                auto change = std::abs(value - values[order[i - 1]]);
                deltaSum += change;
                deltaMax = std::max(deltaMax, change);
            }
        }
        bounds[0] = times[order[0]];
        bounds[1] = times[order.back()];
        auto duration = double(bounds[1] - bounds[0]);
        out[0] = minimum;
        out[1] = maximum;
        out[2] = mean;
        out[3] = count > 1 ? std::sqrt(m2 / double(count - 1)) : 0;
        out[4] = count > 1 ? deltaSum / double(count - 1) : 0;
        out[5] = deltaMax;
        out[6] = duration > 0 ? (values[order.back()] - values[order[0]]) * 1000 / duration : 0;
        out[7] = duration > 0 ? double(count - 1) * 1000 / duration : 0;
        out[8] = duration;
        return 0;
    } catch (...) {
        return -3;
    }
}
