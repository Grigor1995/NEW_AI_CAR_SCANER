#include "core/transport/qt_elm.hpp"
#include "core/protocols/elm.hpp"
#include <QHostAddress>
#if !defined(Q_OS_ANDROID) && !defined(Q_OS_IOS)
#include <QSerialPort>
#endif
#include <QTcpSocket>
namespace cda {
QtElm::QtElm(QObject *p) : QObject(p) {
    deadline_.setSingleShot(true);
    connect(&deadline_, &QTimer::timeout, this, [this] { fail(tr("Device operation timed out")); });
}
bool QtElm::connected() const {
    if (auto *socket = qobject_cast<QTcpSocket *>(device_.get()))
        return socket->state() == QAbstractSocket::ConnectedState;
    return device_ && device_->isOpen();
}
void QtElm::fail(const QString &message) {
    disconnectDevice();
    emit failed(message);
}
void QtElm::disconnectDevice() {
    deadline_.stop();
    busy_ = false;
    buffer_.clear();
    if (device_) {
        device_->disconnect(this);
        device_->close();
        device_.release()->deleteLater();
    }
    emit closed();
}
void QtElm::attach() {
    connect(device_.get(), &QIODevice::readyRead, this, [this] {
        if (!device_)
            return;
        buffer_ += device_->readAll();
        if (buffer_.size() > 65536) {
            fail(tr("Device response exceeds limit"));
            return;
        }
        if (!busy_) {
            if (!buffer_.isEmpty())
                fail(tr("Unexpected device data"));
            return;
        }
        auto end = buffer_.indexOf('>');
        if (end < 0)
            return;
        auto data = buffer_.left(end + 1);
        buffer_.remove(0, end + 1);
        busy_ = false;
        deadline_.stop();
        if (!buffer_.trimmed().isEmpty()) {
            fail(tr("Unsolicited trailing device response"));
            return;
        }
        buffer_.clear();
        emit reply(QString::fromLatin1(data));
    });
}
void QtElm::connectTcp(const QString &host, quint16 port) {
    disconnectDevice();
    QHostAddress address;
    if (!address.setAddress(host) || port == 0) {
        emit failed(tr("Numeric adapter IP and valid port required"));
        return;
    }
    auto socket = std::make_unique<QTcpSocket>();
    auto *ptr = socket.get();
    device_ = std::move(socket);
    attach();
    connect(ptr, &QTcpSocket::connected, this, [this] {
        deadline_.stop();
        emit ready();
    });
    connect(ptr, &QTcpSocket::errorOccurred, this,
            [this] { fail(tr("TCP adapter connection failed")); });
    connect(ptr, &QTcpSocket::disconnected, this, [this] { fail(tr("Adapter disconnected")); });
    deadline_.start(5000);
    ptr->connectToHost(address, port);
}
void QtElm::connectSerial(const QString &port, int baud) {
#if defined(Q_OS_ANDROID) || defined(Q_OS_IOS)
    Q_UNUSED(port);
    Q_UNUSED(baud);
    emit failed(tr("USB / serial transport unavailable on this platform"));
#else

    disconnectDevice();
    if (port.isEmpty() || baud < 1200 || baud > 1000000) {
        emit failed(tr("Invalid serial port settings"));
        return;
    }
    auto serial = std::make_unique<QSerialPort>();
    serial->setPortName(port);
    serial->setBaudRate(baud);
    auto *ptr = serial.get();
    device_ = std::move(serial);
    if (!ptr->open(QIODevice::ReadWrite)) {
        fail(tr("Serial adapter could not be opened"));
        return;
    }
    attach();
    connect(ptr, &QSerialPort::errorOccurred, this, [this](QSerialPort::SerialPortError e) {
        if (e != QSerialPort::NoError)
            fail(tr("Serial adapter failed"));
    });
    emit ready();
#endif
}
void QtElm::readCommand(const QString &command, int timeoutMs) {
    if (!connected() || busy_) {
        emit failed(tr("Device unavailable or command in progress"));
        return;
    }
    if (!allowedReadCommand(command.toStdString()) || timeoutMs < 1 || timeoutMs > 35000) {
        emit failed(tr("Command outside read-only allowlist"));
        return;
    }
    busy_ = true;
    buffer_.clear();
    auto bytes = command.toLatin1() + "\r";
    if (device_->write(bytes) != bytes.size()) {
        fail(tr("Device command write failed"));
        return;
    }
    deadline_.start(timeoutMs);
}
} // namespace cda
