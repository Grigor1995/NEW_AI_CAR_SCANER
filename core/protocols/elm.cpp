#include "core/protocols/elm.hpp"
#include <algorithm>
#include <cctype>
#include <iomanip>
#include <sstream>
#include <stdexcept>
namespace cda {
namespace {
Bytes hex(const std::string &s) {
    if (s.empty() || s.size() % 2)
        throw std::invalid_argument("Malformed hex response");
    Bytes out;
    out.reserve(s.size() / 2);
    for (size_t i = 0; i < s.size(); i += 2) {
        if (!std::isxdigit(static_cast<unsigned char>(s[i])) ||
            !std::isxdigit(static_cast<unsigned char>(s[i + 1])))
            throw std::invalid_argument("Invalid hex digit");
        out.push_back(static_cast<uint8_t>(std::stoul(s.substr(i, 2), nullptr, 16)));
    }
    return out;
}
} // namespace
std::vector<Bytes> parseElm(const std::string &raw) {
    if (raw.size() > 65536)
        throw std::invalid_argument("Response limit exceeded");
    std::string text = raw;
    for (char &c : text) {
        if (c == '\r' || c == '>')
            c = '\n';
        else
            c = static_cast<char>(std::toupper(static_cast<unsigned char>(c)));
    }
    for (auto error : {"NO DATA", "ERROR", "STOPPED", "UNABLE TO CONNECT", "BUFFER FULL", "?"})
        if (text.find(error) != std::string::npos)
            throw std::invalid_argument("Adapter reports unavailable data");
    struct Segment {
        size_t size;
        Bytes bytes;
        unsigned sequence = 1;
    };
    std::map<std::string, Segment> segments;
    std::vector<Bytes> result;
    std::istringstream lines(text);
    std::string line;
    while (std::getline(lines, line)) {
        std::istringstream words(line);
        std::vector<std::string> tokens;
        std::string token;
        while (words >> token)
            tokens.push_back(token);
        if (tokens.empty())
            continue;
        if (tokens.size() == 1 && (tokens[0] == "OK" || tokens[0].starts_with("SEARCHING")))
            continue;
        std::string ecu;
        if (tokens.size() > 1 && (tokens[0].size() == 3 || tokens[0].size() == 8)) {
            ecu = tokens.front();
            tokens.erase(tokens.begin());
        }
        std::string compact;
        for (const auto &t : tokens)
            compact += t;
        if ((compact.size() == 4 && compact.starts_with("01")) || compact == "03" ||
            compact == "07" || compact == "0A" || compact == "0902")
            continue;
        if (ecu.empty() && compact.size() > 3 && compact.size() % 2) {
            ecu = compact.substr(0, 3);
            compact.erase(0, 3);
        }
        if (!ecu.empty())
            for (char c : ecu)
                if (!std::isxdigit(static_cast<unsigned char>(c)))
                    throw std::invalid_argument("Invalid ECU header");
        if (ecu.empty() && compact.size() > 10 &&
            (compact.starts_with("18DA") || compact.starts_with("18DB"))) {
            ecu = compact.substr(0, 8);
            compact.erase(0, 8);
        }
        Bytes bytes = hex(compact);
        if (ecu.empty()) {
            result.push_back(std::move(bytes));
            continue;
        }
        if (bytes.size() > 8)
            throw std::invalid_argument("CAN classic frame exceeds 8 bytes");
        const unsigned kind = bytes[0] >> 4;
        if (kind == 0) {
            unsigned size = bytes[0] & 15;
            if (size == 0 || size > 7 || size >= bytes.size())
                throw std::invalid_argument("Invalid single frame length");
            result.emplace_back(bytes.begin() + 1, bytes.begin() + 1 + size);
        } else if (kind == 1 && bytes.size() >= 3) {
            size_t size = ((bytes[0] & 15) << 8) | bytes[1];
            if (size <= bytes.size() - 2 || size > 4095 || segments.contains(ecu))
                throw std::invalid_argument("Invalid first frame");
            segments.emplace(ecu, Segment{size, Bytes(bytes.begin() + 2, bytes.end()), 1});
        } else if (kind == 2 && segments.contains(ecu)) {
            auto &s = segments.at(ecu);
            if ((bytes[0] & 15) != s.sequence || s.bytes.size() >= s.size)
                throw std::invalid_argument("ISO-TP sequence error");
            s.bytes.insert(s.bytes.end(), bytes.begin() + 1, bytes.end());
            s.sequence = (s.sequence + 1) % 16;
        } else
            throw std::invalid_argument("Unsupported or unordered ISO-TP frame");
    }
    for (auto &[ecu, s] : segments) {
        if (s.bytes.size() < s.size)
            throw std::invalid_argument("Incomplete ISO-TP");
        s.bytes.resize(s.size);
        result.push_back(std::move(s.bytes));
    }
    if (result.empty())
        throw std::invalid_argument("Empty ECU response");
    return result;
}
Bytes pidData(uint8_t pid, const std::string &reply) {
    for (auto &p : parseElm(reply))
        if (p.size() >= 2 && p[0] == 0x41 && p[1] == pid)
            return Bytes(p.begin() + 2, p.end());
    throw std::invalid_argument("Requested PID absent");
}
const std::vector<PidDefinition> &livePids() {
    static const std::vector<PidDefinition> pids{{0x0c, "rpm", "rpm", 2, 0.25, 0},
                                                 {0x0d, "speed", "km/h", 1, 1, 0},
                                                 {0x05, "coolant", "C", 1, 1, -40},
                                                 {0x04, "engine_load", "%", 1, 100.0 / 255, 0},
                                                 {0x0f, "intake_air", "C", 1, 1, -40},
                                                 {0x10, "maf", "g/s", 2, 0.01, 0},
                                                 {0x0b, "map", "kPa", 1, 1, 0},
                                                 {0x11, "throttle", "%", 1, 100.0 / 255, 0},
                                                 {0x06, "stft", "%", 1, 100.0 / 128, -100},
                                                 {0x07, "ltft", "%", 1, 100.0 / 128, -100}};
    return pids;
}
Measurement decodePid(uint8_t pid, const std::string &reply) {
    Measurement m;
    m.at = std::chrono::system_clock::now();
    const auto &pids = livePids();
    auto it = std::find_if(pids.begin(), pids.end(), [pid](const auto &p) { return p.pid == pid; });
    if (it == pids.end()) {
        m.name = "unknown";
        m.quality = Quality::Unsupported;
        return m;
    }
    m.name = it->name;
    m.unit = it->unit;
    try {
        const auto data = pidData(pid, reply);
        if (data.size() != it->length)
            throw std::invalid_argument("Invalid PID size");
        unsigned value = 0;
        for (auto byte : data)
            value = (value << 8) | byte;
        m.value = value * it->scale + it->offset;
        m.quality = Quality::Valid;
    } catch (const std::invalid_argument &) {
        m.quality =
            reply.find("NO DATA") != std::string::npos ? Quality::Unavailable : Quality::Invalid;
    }
    return m;
}
std::vector<std::string> troubleCodes(const std::string &reply, uint8_t service) {
    std::vector<std::string> result;
    bool matched = false;
    for (const auto &p : parseElm(reply)) {
        if (p[0] != service)
            continue;
        matched = true;
        if ((p.size() - 1) % 2)
            throw std::invalid_argument("Truncated DTC pair");
        for (size_t i = 1; i + 1 < p.size(); i += 2) {
            if (p[i] == 0 && p[i + 1] == 0)
                continue;
            std::ostringstream out;
            out << "PCBU"[p[i] >> 6] << std::uppercase << std::hex << std::setfill('0')
                << std::setw(2) << (p[i] & 63) << std::setw(2) << unsigned(p[i + 1]);
            if (std::find(result.begin(), result.end(), out.str()) == result.end())
                result.push_back(out.str());
        }
    }
    if (!matched)
        throw std::invalid_argument("DTC service absent");
    return result;
}
std::vector<unsigned> supportedPids(unsigned page, const Bytes &data) {
    if (data.size() != 4 || page > 0xe0 || page % 0x20)
        throw std::invalid_argument("Invalid supported PID bitmap");
    std::vector<unsigned> result;
    for (unsigned i = 0; i < 32; ++i)
        if (data[i / 8] & (1u << (7 - i % 8)))
            result.push_back(page + i + 1);
    return result;
}
bool allowedReadCommand(const std::string &c) {
    if (c == "ATZ" || c == "ATE0" || c == "ATL0" || c == "ATS0" || c == "ATH0" || c == "ATCAF1" ||
        c == "ATDPN" || c == "ATRV" || c == "03" || c == "07" || c == "0A")
        return true;
    if (c.size() == 5 && c.starts_with("ATSP") && c[4] >= '0' && c[4] <= '9')
        return true;
    return c.size() == 4 && (c.starts_with("01") || c.starts_with("02") || c.starts_with("09")) &&
           c.find_first_not_of("0123456789ABCDEF") == std::string::npos;
}
} // namespace cda
