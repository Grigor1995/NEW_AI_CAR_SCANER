#pragma once
#include "services/diagnostics/controller.hpp"
#include <QJsonObject>
#include <QObject>
#include <QSettings>
#include <QTranslator>
#include <QVariantList>
class AppModel final : public QObject {
    Q_OBJECT
    Q_PROPERTY(QStringList launcherOrder READ launcherOrder NOTIFY launcherOrderChanged)
    Q_PROPERTY(QString language READ language WRITE setLanguage NOTIFY settingsChanged)
    Q_PROPERTY(QString units READ units WRITE setUnits NOTIFY settingsChanged)
    Q_PROPERTY(QString theme READ theme WRITE setTheme NOTIFY settingsChanged)
    Q_PROPERTY(QString message READ message NOTIFY changed)
    Q_PROPERTY(QString email READ email NOTIFY changed)
    Q_PROPERTY(QStringList roles READ roles NOTIFY changed)
    Q_PROPERTY(QVariantList vehicles READ vehicles NOTIFY changed)
    Q_PROPERTY(QVariantList measurements READ measurements NOTIFY changed)
    Q_PROPERTY(QStringList dtcs READ dtcs NOTIFY changed)
    Q_PROPERTY(QString deviceStatus READ deviceStatus NOTIFY changed)
    Q_PROPERTY(bool connected READ connected NOTIFY changed)
    Q_PROPERTY(bool busy READ busy NOTIFY changed)
    QString database_, token_, message_;
    QJsonObject account_;
    QSettings settings_;
    QTranslator translator_;
    cda::DiagnosticController diagnostic_;
    bool busy_ = false;
    QTimer sessionCheck_;
    void error(const QString &);
    void authenticate(bool registration, const QString &, const QString &);

  public:
    explicit AppModel(const QString &database, QObject *p = nullptr);
    QStringList launcherOrder() const;
    Q_INVOKABLE void moveLauncherTile(int from, int to);
    QString language() const;
    QString units() const;
    QString theme() const;
    QString message() const {
        return message_;
    }
    QString email() const {
        return account_["email"].toString();
    }
    QStringList roles() const;
    QVariantList vehicles() const;
    QVariantList measurements() const;
    QStringList dtcs() const {
        return diagnostic_.dtcs();
    }
    QString deviceStatus() const {
        return diagnostic_.status();
    }
    bool connected() const {
        return diagnostic_.ready();
    }
    bool busy() const {
        return busy_;
    }
    void setLanguage(const QString &);
    void setUnits(const QString &);
    void setTheme(const QString &);
    Q_INVOKABLE void registerAccount(const QString &email, const QString &password);
    Q_INVOKABLE void login(const QString &email, const QString &password);
    Q_INVOKABLE void logout();
    Q_INVOKABLE void addVehicle(const QString &make, const QString &model, int year,
                                const QString &vin);
    Q_INVOKABLE void connectTcp(const QString &host, int port);
    Q_INVOKABLE void connectSerial(const QString &port);
    Q_INVOKABLE void disconnectDevice() {
        diagnostic_.disconnectDevice();
    }
    Q_INVOKABLE void scan();
    Q_INVOKABLE QString analyze(const QString &symptom) const;
    Q_INVOKABLE void savePreferences();
    Q_INVOKABLE void exportReport(const QString &filename);
  signals:
    void changed();
    void settingsChanged();
    void launcherOrderChanged();
};
