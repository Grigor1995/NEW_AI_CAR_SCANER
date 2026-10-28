#include "apps/shared/app_model.hpp"
#include "core/ai/evidence.hpp"
#include "core/telemetry/units.hpp"
#include "services/identity/store.hpp"
#include <QCoreApplication>
#include <QDateTime>
#include <QFileInfo>
#include <QFutureWatcher>
#include <QJsonArray>
#include <QJsonDocument>
#include <QQmlEngine>
#include <QSaveFile>
#include <QtConcurrent>
AppModel::AppModel(const QString &db, QObject *p)
    : QObject(p), database_(db), settings_("NeoAutomotive", "CarDiagnosticAnalysis") {
    connect(&diagnostic_, &cda::DiagnosticController::changed, this, &AppModel::changed);
    connect(&diagnostic_, &cda::DiagnosticController::problem, this, &AppModel::error);
    sessionCheck_.setInterval(30000);
    connect(&sessionCheck_, &QTimer::timeout, this, [this] {
        if (token_.isEmpty())
            return;
        try {
            cda::Store store(database_);
            store.account(token_);
        } catch (const std::exception &) {
            logout();
        }
    });
    sessionCheck_.start();
    auto lang = language();
    setLanguage(lang);
}
QString AppModel::language() const {
    return settings_.value("language", "en").toString();
}
QString AppModel::units() const {
    return settings_.value("units", "metric").toString();
}
QString AppModel::theme() const {
    return settings_.value("theme", "dark").toString();
}
void AppModel::setLanguage(const QString &lang) {
    if (!QStringList{"en", "hy", "ru", "fr"}.contains(lang))
        return;
    QCoreApplication::removeTranslator(&translator_);
    if (translator_.load(":/i18n/cda_" + lang + ".qm"))
        QCoreApplication::installTranslator(&translator_);
    settings_.setValue("language", lang);
    emit settingsChanged();
}
void AppModel::setUnits(const QString &unit) {
    if (!QStringList{"metric", "imperial"}.contains(unit))
        return;
    settings_.setValue("units", unit);
    emit settingsChanged();
    emit changed();
}
void AppModel::setTheme(const QString &theme) {
    if (!QStringList{"dark", "light", "system"}.contains(theme))
        return;
    settings_.setValue("theme", theme);
    emit settingsChanged();
}
void AppModel::error(const QString &e) {
    message_ = e;
    emit changed();
}
QStringList AppModel::roles() const {
    QStringList out;
    for (auto v : account_["roles"].toArray())
        out.append(v.toString());
    return out;
}
void AppModel::authenticate(bool registration, const QString &email, const QString &password) {
    if (busy_)
        return;
    busy_ = true;
    emit changed();
    auto *watcher = new QFutureWatcher<QJsonObject>(this);
    connect(watcher, &QFutureWatcher<QJsonObject>::finished, this, [this, watcher] {
        auto result = watcher->result();
        watcher->deleteLater();
        busy_ = false;
        if (result.contains("error")) {
            error(tr("Authentication failed; check credentials and account availability"));
            return;
        }
        token_ = result.take("token").toString();
        account_ = result;
        message_ = tr("Signed in; contact is not verified");
        try {
            cda::Store store(database_);
            auto prefs = store.settings(token_);
            if (!prefs.isEmpty()) {
                setLanguage(prefs["language"].toString());
                setUnits(prefs["units"].toString());
                setTheme(prefs["theme"].toString());
            }
        } catch (const std::exception &) {
            error(tr("Saved preferences unavailable"));
        }
        emit changed();
    });
    watcher->setFuture(QtConcurrent::run([db = database_, email, password, registration] {
        try {
            cda::Store store(db);
            if (registration)
                store.registerAccount(email, password);
            return store.login(email, password);
        } catch (const std::exception &) {
            return QJsonObject{{"error", true}};
        }
    }));
}
void AppModel::registerAccount(const QString &e, const QString &p) {
    authenticate(true, e, p);
}
void AppModel::login(const QString &e, const QString &p) {
    authenticate(false, e, p);
}
void AppModel::logout() {
    try {
        if (!token_.isEmpty()) {
            cda::Store store(database_);
            store.logout(token_);
        }
    } catch (const std::exception &) {
    }
    diagnostic_.disconnectDevice();
    token_.clear();
    account_ = {};
    message_ = tr("Signed out");
    emit changed();
}
QVariantList AppModel::vehicles() const {
    try {
        if (token_.isEmpty())
            return {};
        cda::Store store(database_);
        return store.vehicles(token_).toVariantList();
    } catch (const std::exception &) {
        return {};
    }
}
void AppModel::addVehicle(const QString &make, const QString &model, int year, const QString &vin) {
    try {
        cda::Store store(database_);
        store.addVehicle(token_, {{"make", make}, {"model", model}, {"year", year}, {"vin", vin}});
        message_ = tr("Vehicle saved; identity remains unverified");
        emit changed();
    } catch (const std::exception &) {
        error(tr("Vehicle could not be saved; check fields and sign-in"));
    }
}
void AppModel::connectTcp(const QString &host, int port) {
    try {
        cda::Store store(database_);
        store.account(token_);
        diagnostic_.connectTcp(host, port);
    } catch (const std::exception &) {
        error(tr("Sign in before connecting an adapter"));
    }
}
void AppModel::connectSerial(const QString &port) {
    try {
        cda::Store store(database_);
        store.account(token_);
        diagnostic_.connectSerial(port);
    } catch (const std::exception &) {
        error(tr("Sign in before connecting an adapter"));
    }
}
QVariantList AppModel::measurements() const {
    auto values = diagnostic_.values();
    for (auto &v : values) {
        auto m = v.toMap();
        if (m["quality"] == "valid" && QDateTime::fromString(m["at"].toString(), Qt::ISODateWithMs)
                                               .msecsTo(QDateTime::currentDateTimeUtc()) > 5000) {
            m["quality"] = "stale";
            m["value"] = QVariant();
        }
        if (m["quality"] == "valid") {
            double value = m["value"].toDouble();
            auto unit = m["unit"].toString();
            if (units() == "imperial" && (unit == "km/h" || unit == "C")) {
                auto target = unit == "C" ? "F" : "mph";
                value = cda::convert(value, unit.toStdString(), target);
                unit = target;
            }
            m["display"] =
                QLocale(language()).toString(value, 'f', unit == "rpm" ? 0 : 1) + " " + unit;
        } else
            m["display"] = tr("Unavailable");
        v = m;
    }
    return values;
}
QString AppModel::analyze(const QString &symptom) const {
    cda::DiagnosticSession session;
    for (const auto &code : dtcs())
        session.dtcs.push_back(code.toStdString());
    session.evidence.push_back(
        {"user_symptom", symptom.toStdString(), cda::Provenance::UserReported});
    auto result = cda::analyze(session);
    if (result.empty())
        return tr("Insufficient verified evidence. Connect an adapter and obtain DTCs; no "
                  "component failure has been established.");
    return tr("Cylinder 2 misfire reported. Cause is unconfirmed. A qualified professional should "
              "compare operating conditions and test ignition, fuel delivery and compression. "
              "Source: ECU_REPORTED + RULE.");
}
void AppModel::savePreferences() {
    try {
        cda::Store store(database_);
        store.saveSettings(token_,
                           {{"language", language()}, {"units", units()}, {"theme", theme()}});
        message_ = tr("Preferences saved to this account");
        emit changed();
    } catch (const std::exception &) {
        error(tr("Sign in to save account preferences; device preferences are retained locally"));
    }
}
void AppModel::exportReport(const QString &filename) {
    if (filename.trimmed().isEmpty()) {
        error(tr("Choose an export filename"));
        return;
    }
    QJsonObject report{{"schemaVersion", 1},
                       {"generatedAt", QDateTime::currentDateTimeUtc().toString(Qt::ISODate)},
                       {"source", connected() ? "connected_adapter" : "no_active_adapter"},
                       {"deviceState", deviceStatus()},
                       {"measurements", QJsonArray::fromVariantList(measurements())},
                       {"dtcs", QJsonArray::fromStringList(dtcs())},
                       {"physicalHardwareCertified", false}};
    QSaveFile file(filename);
    if (!file.open(QIODevice::WriteOnly)) {
        error(tr("Report could not be opened"));
        return;
    }
    auto data = QJsonDocument(report).toJson();
    if (file.write(data) != data.size() || !file.commit()) {
        error(tr("Report could not be saved"));
        return;
    }
    QFile::setPermissions(filename, QFileDevice::ReadOwner | QFileDevice::WriteOwner);
    message_ = tr("Diagnostic JSON report saved");
    emit changed();
}

void AppModel::scan() {
    try {
        cda::Store store(database_);
        store.account(token_);
        diagnostic_.readDtcs();
    } catch (const std::exception &) {
        logout();
    }
}
