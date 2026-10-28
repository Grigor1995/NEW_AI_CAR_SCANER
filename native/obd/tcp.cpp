#include <pybind11/pybind11.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <poll.h>
#include <fcntl.h>
#include <unistd.h>
#include <cerrno>
#include <chrono>
#include <cmath>
#include <stdexcept>
#include <string>
#include <string_view>

namespace py = pybind11;
using Clock = std::chrono::steady_clock;

// One owner per adapter. Python serializes calls; blocking methods release the GIL.
class TcpTransport {
    int fd_ = -1;
    std::string pending_;
    static constexpr size_t limit = 65536;
    static Clock::time_point deadline(double seconds) {
        if (!std::isfinite(seconds) || seconds <= 0 || seconds > 120)
            throw std::invalid_argument("Timeout must be in (0,120] seconds");
        return Clock::now() + std::chrono::milliseconds(static_cast<int>(seconds * 1000));
    }
    void wait(short events, Clock::time_point end) {
        while (true) {
            auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(end - Clock::now()).count();
            if (ms <= 0) throw std::runtime_error("OBD TCP timeout");
            pollfd p{fd_, events, 0};
            int r = ::poll(&p, 1, static_cast<int>(ms));
            if (r < 0 && errno == EINTR) continue;
            if (r < 0) throw std::runtime_error("OBD TCP poll failed");
            if (r == 0) throw std::runtime_error("OBD TCP timeout");
            if (p.revents & events) return;
            throw std::runtime_error("OBD TCP disconnected");
        }
    }
    void require_connected() const {
        if (fd_ < 0) throw std::runtime_error("OBD TCP is not connected");
    }
public:
    TcpTransport() = default;
    TcpTransport(const TcpTransport&) = delete;
    TcpTransport& operator=(const TcpTransport&) = delete;
    ~TcpTransport() { disconnect(); }
    bool connected() const { return fd_ >= 0; }
    void disconnect() {
        if (fd_ >= 0) { ::close(fd_); fd_ = -1; }
        pending_.clear();
    }
    void connect(const std::string& host, int port, double timeout) {
        if (connected()) throw std::runtime_error("OBD TCP already connected");
        auto end = deadline(timeout);
        sockaddr_in address{};
        address.sin_family = AF_INET;
        if (port < 1 || port > 65535 || ::inet_pton(AF_INET, host.c_str(), &address.sin_addr) != 1)
            throw std::invalid_argument("Native OBD requires a numeric IPv4 address and valid port");
        address.sin_port = htons(static_cast<uint16_t>(port));
        fd_ = ::socket(AF_INET, SOCK_STREAM, 0);
        if (fd_ < 0) throw std::runtime_error("OBD TCP socket failed");
        try {
            if (::fcntl(fd_, F_SETFL, O_NONBLOCK) < 0)
                throw std::runtime_error("Cannot configure nonblocking socket");
#ifdef SO_NOSIGPIPE
            int no_sigpipe = 1;
            ::setsockopt(fd_, SOL_SOCKET, SO_NOSIGPIPE, &no_sigpipe, sizeof(no_sigpipe));
#endif
            if (::connect(fd_, reinterpret_cast<sockaddr*>(&address), sizeof(address)) < 0) {
                if (errno != EINPROGRESS) throw std::runtime_error("OBD TCP connect failed");
                wait(POLLOUT, end);
                int error = 0;
                socklen_t size = sizeof(error);
                if (::getsockopt(fd_, SOL_SOCKET, SO_ERROR, &error, &size) < 0 || error)
                    throw std::runtime_error("OBD TCP connect failed");
            }
        } catch (...) { disconnect(); throw; }
    }
    void write(const std::string& data, double timeout) {
        require_connected();
        auto end = deadline(timeout);
        if (data.size() > 64) throw std::invalid_argument("Command exceeds 64 bytes");
        // Deliberately narrow first milestone: generic read services and adapter setup only.
        std::string command;
        for (char c : data) {
            if (c == ' ') continue;
            command.push_back(c);
        }
        if (command.empty() || command.back() != '\r') throw std::invalid_argument("One CR-terminated command required");
        command.pop_back();
        bool allowed = command == "ATZ" || command == "ATE0" || command == "ATL0" ||
            command == "ATS0" || command == "ATH0" || command == "ATDPN" ||
            command == "ATCAF1" || command == "ATRV" || command == "03" || command == "07" || command == "0A";
        if (command.size() == 5 && command.starts_with("ATSP") && command[4] >= '0' && command[4] <= '9') allowed = true;
        if (command.size() == 4 && (command.starts_with("01") || command.starts_with("09"))) {
            allowed = command.find_first_not_of("0123456789ABCDEF") == std::string::npos;
        }
        if (!allowed) throw std::invalid_argument("Command outside native read-only allowlist");
        try {
            size_t offset = 0;
            while (offset < data.size()) {
                wait(POLLOUT, end);
#ifdef MSG_NOSIGNAL
                constexpr int flags = MSG_NOSIGNAL;
#else
                constexpr int flags = 0;
#endif
                auto n = ::send(fd_, data.data() + offset, data.size() - offset, flags);
                if (n < 0 && (errno == EAGAIN || errno == EINTR)) continue;
                if (n <= 0) throw std::runtime_error("OBD TCP send failed");
                offset += static_cast<size_t>(n);
            }
        } catch (...) { disconnect(); throw; }
    }
    std::string read_until(const std::string& terminator, double timeout) {
        require_connected();
        if (terminator.empty() || terminator.size() > 16) throw std::invalid_argument("Invalid terminator");
        auto end = deadline(timeout);
        try {
            while (true) {
                auto at = pending_.find(terminator);
                if (at != std::string::npos) {
                    auto result = pending_.substr(0, at + terminator.size());
                    pending_.erase(0, result.size());
                    return result;
                }
                wait(POLLIN, end);
                char buffer[4096];
                auto n = ::recv(fd_, buffer, sizeof(buffer), 0);
                if (n < 0 && (errno == EAGAIN || errno == EINTR)) continue;
                if (n <= 0) throw std::runtime_error("OBD TCP peer disconnected");
                if (pending_.size() + static_cast<size_t>(n) > limit)
                    throw std::runtime_error("OBD TCP response exceeds 64 KiB");
                pending_.append(buffer, static_cast<size_t>(n));
            }
        } catch (...) { disconnect(); throw; }
    }
};
PYBIND11_MODULE(_obd_native, m) {
    py::class_<TcpTransport>(m, "TcpTransport")
        .def(py::init<>())
        .def("connect", &TcpTransport::connect, py::call_guard<py::gil_scoped_release>())
        .def("disconnect", &TcpTransport::disconnect)
        .def_property_readonly("connected", &TcpTransport::connected)
        .def("write", [](TcpTransport& self, py::bytes data, double timeout) {
            std::string bytes = data;
            py::gil_scoped_release release;
            self.write(bytes, timeout);
        })
        .def("read_until", [](TcpTransport& self, py::bytes term, double timeout) {
            std::string marker = term, result;
            { py::gil_scoped_release release; result = self.read_until(marker, timeout); }
            return py::bytes(result);
        });
}
