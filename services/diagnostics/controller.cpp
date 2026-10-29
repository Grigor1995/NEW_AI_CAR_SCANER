#include "services/diagnostics/controller.hpp"
#include "core/protocols/elm.hpp"
#include <QDateTime>
namespace cda {
DiagnosticController::DiagnosticController(QObject *p) : QObject(p) {
    for (const auto &definition : livePids())
        values_.append(QVariantMap{{"name", definition.name},
                                   {"quality", "unavailable"},
                                   {"value", QVariant()},
                                   {"unit", QString()},
                                   {"at", QString()}});
    status_ = tr("No adapter connected");
    // One outstanding command at a time; schedule up to ten requests/second.
    poll_.setInterval(100);
    connect(&transport_, &QtElm::ready, this, [this] {
        queue_ = {"ATZ", "ATE0", "ATL0", "ATS0", "ATH0", "ATCAF1", "ATSP0", "0100"};
        status_ = tr("Detecting supported PIDs");
        advance();
        emit changed();
    });
    connect(&transport_, &QtElm::reply, this, &DiagnosticController::response);
    connect(&transport_, &QtElm::closed, this, [this] {
        poll_.stop();
        ready_ = false;
        current_.clear();
        queue_.clear();
        polling_.clear();
        dtcs_.clear();
        for (auto &v : values_) {
            auto m = v.toMap();
            m["quality"] = m["value"].isValid() ? "stale" : "unavailable";
            m["value"] = QVariant();
            m.remove("history");
            v = m;
        }
        status_ = tr("Adapter disconnected");
        emit changed();
    });
    connect(&transport_, &QtElm::failed, this, [this](const QString &e) {
        status_ = e;
        emit problem(e);
        emit changed();
    });
    connect(&poll_, &QTimer::timeout, this, [this] {
        if (ready_ && current_.isEmpty() && !polling_.isEmpty()) {
            queue_.append(polling_[pollIndex_]);
            pollIndex_ = (pollIndex_ + 1) % polling_.size();
            advance();
        }
    });
}
void DiagnosticController::connectTcp(const QString &host, int port) {
    if (port < 1 || port > 65535) {
        emit problem(tr("Invalid port"));
        return;
    }
    transport_.connectTcp(host, static_cast<quint16>(port));
}
void DiagnosticController::connectSerial(const QString &port) {
    transport_.connectSerial(port);
}
void DiagnosticController::disconnectDevice() {
    transport_.disconnectDevice();
}
void DiagnosticController::advance() {
    if (!current_.isEmpty() || queue_.isEmpty())
        return;
    current_ = queue_.takeFirst();
    transport_.readCommand(current_, current_ == "0100" ? 35000 : 3000);
}
void DiagnosticController::response(const QString &raw) {
    const QString command = current_;
    current_.clear();
    try {
        if (command.startsWith("AT")) {
            if (raw.contains('?') || raw.contains("ERROR"))
                throw std::invalid_argument("Adapter rejected initialization");
        } else if (command == "0100") {
            std::vector<unsigned> supported;
            bool completeBitmap = false;
            for (const auto &frame : parseElm(raw.toStdString()))
                if (frame.size() == 6 && frame[0] == 0x41 && frame[1] == 0) {
                    completeBitmap = true;
                    auto page = supportedPids(0, Bytes(frame.begin() + 2, frame.end()));
                    supported.insert(supported.end(), page.begin(), page.end());
                }
            if (!completeBitmap)
                throw std::invalid_argument("Complete supported PID bitmap required");
            polling_.clear();
            pollIndex_ = 0;
            for (const auto &definition : livePids()) {
                auto pid = definition.pid;
                bool present =
                    std::find(supported.begin(), supported.end(), unsigned(pid)) != supported.end();
                if (present)
                    polling_.append(QString("01%1").arg(pid, 2, 16, QChar('0')).toUpper());
                else
                    for (auto &v : values_) {
                        auto m = v.toMap();
                        QString name = definition.name;
                        if (m["name"] == name) {
                            m["quality"] = "unsupported";
                            v = m;
                        }
                    }
            }
            ready_ = true;
            status_ = polling_.isEmpty() ? tr("Connected; displayed PIDs unsupported")
                                         : tr("Connected — read only");
            poll_.start();
        } else if (command == "03") {
            dtcs_.clear();
            for (const auto &c : troubleCodes(raw.toStdString()))
                dtcs_.append(QString::fromStdString(c));
            status_ = tr("Stored DTC response received");
        } else {
            bool valid = false;
            auto pid = command.mid(2).toUInt(&valid, 16);
            if (!valid)
                throw std::invalid_argument("Invalid PID");
            auto m = decodePid(static_cast<uint8_t>(pid), raw.toStdString());
            for (auto &v : values_)
                if (v.toMap()["name"] == QString::fromStdString(m.name)) {
                    auto history = v.toMap().value("history").toList();
                    if (m.value)
                        history.append(QVariantMap{{"at", QDateTime::currentMSecsSinceEpoch()},
                                                   {"value", *m.value}});
                    while (history.size() > 60)
                        history.removeFirst();
                    v = QVariantMap{
                        {"history", history},
                        {"name", QString::fromStdString(m.name)},
                        {"value", m.value ? QVariant(*m.value) : QVariant()},
                        {"unit", QString::fromStdString(m.unit)},
                        {"quality", m.quality == Quality::Valid         ? "valid"
                                    : m.quality == Quality::Unavailable ? "unavailable"
                                                                        : "invalid"},
                        {"at", QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs)},
                        {"provenance", "VEHICLE_MEASURED"}};
                }
        }
    } catch (const std::exception &e) {
        status_ = tr("Adapter response invalid or unsupported");
        if (command == "0100" || command.startsWith("AT")) {
            transport_.disconnectDevice();
        }
        emit problem(status_);
    }
    emit changed();
    advance();
}
void DiagnosticController::readDtcs() {
    if (!ready_) {
        emit problem(tr("Connect an eligible adapter first"));
        return;
    }
    queue_.append("03");
    advance();
}
} // namespace cda
