#pragma once
#include <QElapsedTimer>
#include <QIODevice>
#include <QObject>
#include <QTimer>
#include <memory>
namespace cda {
class QtElm final : public QObject {
    Q_OBJECT
    std::unique_ptr<QIODevice> device_;
    QTimer deadline_;
    QByteArray buffer_;
    bool busy_ = false;

  public:
    explicit QtElm(QObject *parent = nullptr);
    bool connected() const;
    void connectTcp(const QString &host, quint16 port);
    void connectSerial(const QString &port, int baud = 38400);
    void readCommand(const QString &command, int timeoutMs = 3000);
    void disconnectDevice();
  signals:
    void ready();
    void closed();
    void reply(QString);
    void failed(QString);

  private:
    void attach();
    void fail(const QString &);
};
} // namespace cda
