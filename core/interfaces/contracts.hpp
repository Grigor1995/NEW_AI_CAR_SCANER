#pragma once
#include <chrono>
#include <optional>
#include <string>
#include <vector>
namespace cda {
enum class Mode { User, Customer, Admin };
enum class Quality { Valid, Unavailable, Unsupported, Stale, Invalid };
enum class Provenance { UserReported, EcuReported, VehicleMeasured, Rule, Ml, Llm, HistoricalCase };
struct Measurement {
    std::string name;
    std::optional<double> value;
    std::string unit;
    Quality quality = Quality::Unavailable;
    Provenance provenance = Provenance::VehicleMeasured;
    std::chrono::system_clock::time_point at{};
};
struct IObdReader {
    virtual ~IObdReader() = default;
    virtual std::string read(std::string command) = 0;
};
struct IDeviceConnection {
    virtual ~IDeviceConnection() = default;
    virtual bool connected() const = 0;
    virtual void disconnect() = 0;
};
struct IProtocolDecoder {
    virtual ~IProtocolDecoder() = default;
    virtual std::vector<Measurement> decode(const std::string &) const = 0;
};
struct INotificationSender {
    virtual ~INotificationSender() = default;
    virtual std::string send(const std::string &destination, const std::string &message) = 0;
};
// Writer implementations may only consume a validated operation-specific permit.
struct WritePermit {
    std::string account, vehicle, ecu, operation, nonce;
};
struct IObdWriter {
    virtual ~IObdWriter() = default;
    virtual std::string execute(const WritePermit &) = 0;
};
} // namespace cda
