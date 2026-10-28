#pragma once
#include "core/transport/qt_elm.hpp"
#include <QStringList>
#include <QTimer>
#include <QVariantList>
namespace cda {
class DiagnosticController final : public QObject {
    Q_OBJECT
    QtElm transport_;
    QTimer poll_;
    QStringList queue_, polling_, dtcs_;
    QString current_, status_;
    QVariantList values_;
    int pollIndex_ = 0;
    bool ready_ = false;
    void advance();
    void response(const QString &);

  public:
    explicit DiagnosticController(QObject *p = nullptr);
    void connectTcp(const QString &, int);
    void connectSerial(const QString &);
    void disconnectDevice();
    void readDtcs();
    QVariantList values() const {
        return values_;
    }
    QStringList dtcs() const {
        return dtcs_;
    }
    QString status() const {
        return status_;
    }
    bool ready() const {
        return ready_;
    }
  signals:
    void changed();
    void problem(QString);
};
} // namespace cda
