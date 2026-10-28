#include "services/identity/store.hpp"
#include "core/security/crypto.hpp"
#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QRegularExpression>
#include <QSqlError>
#include <QSqlQuery>
#include <QUuid>
#include <stdexcept>
namespace cda {
namespace {
QByteArray bytes(const Blob &b) {
    return QByteArray(reinterpret_cast<const char *>(b.data()), static_cast<qsizetype>(b.size()));
}
std::span<const unsigned char> span(const QByteArray &b) {
    return {reinterpret_cast<const unsigned char *>(b.constData()), static_cast<size_t>(b.size())};
}
QString tokenHash(const QString &s) {
    return QString::fromLatin1(bytes(sha256(span(s.toUtf8()))).toHex());
}
QString normalized(QString email) {
    email = email.trimmed().toLower();
    if (email.size() > 254 ||
        !QRegularExpression("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$").match(email).hasMatch())
        throw std::invalid_argument("Invalid email address");
    return email;
}
QString id() {
    return QUuid::createUuid().toString(QUuid::WithoutBraces);
}
QSqlQuery query(QSqlDatabase db, const QString &sql, const QVariantList &args = {}) {
    QSqlQuery q(db);
    if (!q.prepare(sql))
        throw std::runtime_error("Database statement failed");
    for (const auto &a : args)
        q.addBindValue(a);
    if (!q.exec())
        throw std::runtime_error("Database operation failed");
    return q;
}
} // namespace
void Store::run(const QString &sql, const QVariantList &args) const {
    query(db_, sql, args);
}
Store::Store(const QString &file) : connection_(id()) {
    QDir().mkpath(QFileInfo(file).absolutePath());
    db_ = QSqlDatabase::addDatabase("QSQLITE", connection_);
    db_.setDatabaseName(file);
    if (!db_.open())
        throw std::runtime_error("SQLite unavailable");
    QFile::setPermissions(file, QFileDevice::ReadOwner | QFileDevice::WriteOwner);
    run("PRAGMA foreign_keys=ON");
    run("PRAGMA busy_timeout=5000");
    // Version 1 is an atomic additive schema. Never auto-downgrade an unknown schema.
    auto v = query(db_, "PRAGMA user_version");
    v.next();
    int schema = v.value(0).toInt();
    v.finish();
    if (schema > 1)
        throw std::runtime_error("Database schema is newer than this application");
    if (schema == 1)
        return;
    if (!db_.transaction())
        throw std::runtime_error("Migration transaction unavailable");
    try {
        run("CREATE TABLE IF NOT EXISTS accounts(id TEXT PRIMARY KEY,email TEXT UNIQUE NOT "
            "NULL,salt BLOB NOT NULL,password BLOB NOT NULL,active INTEGER NOT NULL DEFAULT 1)");
        run("CREATE TABLE IF NOT EXISTS roles(account TEXT NOT NULL REFERENCES accounts(id),role "
            "TEXT CHECK(role IN ('USER','CUSTOMER','ADMIN','MARKET')),PRIMARY KEY(account,role))");
        run("CREATE TABLE IF NOT EXISTS tokens(hash TEXT PRIMARY KEY,account TEXT NOT NULL "
            "REFERENCES accounts(id),expires INTEGER NOT NULL)");
        run("CREATE TABLE IF NOT EXISTS vehicles(id TEXT PRIMARY KEY,owner TEXT NOT NULL "
            "REFERENCES accounts(id),payload TEXT NOT NULL)");
        run("CREATE INDEX IF NOT EXISTS vehicles_owner ON vehicles(owner)");
        run("CREATE TABLE IF NOT EXISTS settings(account TEXT PRIMARY KEY REFERENCES "
            "accounts(id),payload TEXT NOT NULL)");
        run("CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,actor TEXT NOT NULL,action "
            "TEXT NOT NULL,subject TEXT NOT NULL,at INTEGER NOT NULL)");
        run("PRAGMA user_version=1");
        if (!db_.commit())
            throw std::runtime_error("Migration commit failed");
    } catch (...) {
        db_.rollback();
        throw;
    }
}
Store::~Store() {
    db_.close();
    db_ = QSqlDatabase();
    QSqlDatabase::removeDatabase(connection_);
}
void Store::appendAudit(const QString &actor, const QString &action, const QString &subject) {
    run("INSERT INTO audit(actor,action,subject,at) VALUES(?,?,?,?)",
        {actor, action, subject, QDateTime::currentSecsSinceEpoch()});
}
QJsonObject Store::registerAccount(QString email, const QString &password) {
    email = normalized(email);
    auto salt = randomBytes(16);
    auto key = passwordKey(password.toUtf8().toStdString(), salt);
    auto accountId = id();
    if (!db_.transaction())
        throw std::runtime_error("Registration transaction unavailable");
    try {
        run("INSERT INTO accounts(id,email,salt,password) VALUES(?,?,?,?)",
            {accountId, email, bytes(salt), bytes(key)});
        run("INSERT INTO roles(account,role) VALUES(?,'USER')", {accountId});
        appendAudit(accountId, "account_registered", accountId);
        if (!db_.commit())
            throw std::runtime_error("Registration commit failed");
    } catch (...) {
        db_.rollback();
        throw std::invalid_argument("Unable to register account");
    }
    return {{"id", accountId}, {"email", email}, {"emailVerified", false}};
}
QJsonObject Store::login(QString email, const QString &password) {
    email = normalized(email);
    auto q = query(db_, "SELECT id,salt,password,active FROM accounts WHERE email=?", {email});
    bool exists = q.next();
    QByteArray salt = exists ? q.value(1).toByteArray() : QByteArray(16, '\0');
    const auto key = passwordKey(password.toUtf8().toStdString(), span(salt));
    if (!exists || !q.value(3).toBool() || !constantEqual(key, span(q.value(2).toByteArray())))
        throw std::invalid_argument("Invalid credentials");
    const QString accountId = q.value(0).toString();
    q.finish();
    QString bearer = QString::fromLatin1(bytes(randomBytes(32)).toHex());
    if (!db_.transaction())
        throw std::runtime_error("Login transaction unavailable");
    try {
        run("DELETE FROM tokens WHERE expires<=?", {QDateTime::currentSecsSinceEpoch()});
        run("INSERT INTO tokens(hash,account,expires) VALUES(?,?,?)",
            {tokenHash(bearer), accountId, QDateTime::currentSecsSinceEpoch() + 3600});
        appendAudit(accountId, "login", accountId);
        if (!db_.commit())
            throw std::runtime_error("Login commit failed");
    } catch (...) {
        db_.rollback();
        throw;
    }
    auto result = account(bearer);
    result["token"] = bearer;
    return result;
}
QJsonObject Store::account(const QString &bearer) const {
    if (bearer.size() != 64)
        throw std::invalid_argument("Authentication required");
    auto q = query(db_,
                   "SELECT a.id,a.email FROM accounts a JOIN tokens t ON t.account=a.id WHERE "
                   "t.hash=? AND t.expires>? AND a.active=1",
                   {tokenHash(bearer), QDateTime::currentSecsSinceEpoch()});
    if (!q.next())
        throw std::invalid_argument("Authentication required");
    const auto accountId = q.value(0).toString(), email = q.value(1).toString();
    q.finish();
    auto r = query(db_, "SELECT role FROM roles WHERE account=? ORDER BY role", {accountId});
    QJsonArray roles;
    while (r.next())
        roles.append(r.value(0).toString());
    return {{"id", accountId}, {"email", email}, {"emailVerified", false}, {"roles", roles}};
}
void Store::logout(const QString &bearer) {
    auto a = account(bearer);
    run("DELETE FROM tokens WHERE hash=?", {tokenHash(bearer)});
    appendAudit(a["id"].toString(), "logout", a["id"].toString());
}
QJsonObject Store::addVehicle(const QString &bearer, const QJsonObject &v) {
    auto a = account(bearer);
    QString make = v["make"].toString().trimmed(), model = v["model"].toString().trimmed();
    int year = v["year"].toInt();
    if (make.isEmpty() || model.isEmpty() || make.size() > 80 || model.size() > 80 || year < 1886 ||
        year > QDate::currentDate().year() + 1)
        throw std::invalid_argument("Invalid vehicle fields");
    QString vin = v["vin"].toString().toUpper();
    if (!vin.isEmpty() && !QRegularExpression("^[A-HJ-NPR-Z0-9]{17}$").match(vin).hasMatch())
        throw std::invalid_argument("Invalid VIN");
    QJsonObject data{{"id", id()},   {"make", make}, {"model", model},
                     {"year", year}, {"vin", vin},   {"identityVerified", false}};
    run("INSERT INTO vehicles(id,owner,payload) VALUES(?,?,?)",
        {data["id"].toString(), a["id"].toString(),
         QString::fromUtf8(QJsonDocument(data).toJson(QJsonDocument::Compact))});
    return data;
}
QJsonArray Store::vehicles(const QString &bearer) const {
    const auto a = account(bearer);
    auto q = query(db_, "SELECT payload FROM vehicles WHERE owner=? ORDER BY rowid",
                   {a["id"].toString()});
    QJsonArray out;
    while (q.next())
        out.append(QJsonDocument::fromJson(q.value(0).toByteArray()).object());
    return out;
}
QJsonObject Store::settings(const QString &bearer) const {
    auto a = account(bearer);
    auto q = query(db_, "SELECT payload FROM settings WHERE account=?", {a["id"].toString()});
    return q.next() ? QJsonDocument::fromJson(q.value(0).toByteArray()).object() : QJsonObject{};
}
void Store::saveSettings(const QString &bearer, const QJsonObject &s) {
    auto a = account(bearer);
    if (!QStringList{"en", "hy", "ru", "fr"}.contains(s["language"].toString()) ||
        !QStringList{"metric", "imperial"}.contains(s["units"].toString()) ||
        !QStringList{"dark", "light", "system"}.contains(s["theme"].toString()))
        throw std::invalid_argument("Invalid settings");
    // Whitelist persisted fields; never accept arbitrary credential fields.
    QJsonObject allowed{{"language", s["language"]}, {"units", s["units"]}, {"theme", s["theme"]}};
    run("INSERT INTO settings(account,payload) VALUES(?,?) ON CONFLICT(account) DO UPDATE SET "
        "payload=excluded.payload",
        {a["id"].toString(),
         QString::fromUtf8(QJsonDocument(allowed).toJson(QJsonDocument::Compact))});
}
void Store::provisionRole(const QString &accountId, const QString &role) {
    if (!QStringList{"USER", "CUSTOMER", "ADMIN", "MARKET"}.contains(role))
        throw std::invalid_argument("Invalid role");
    // Operator-only local CLI path, never a self-service HTTP endpoint.
    run("INSERT OR IGNORE INTO roles(account,role) VALUES(?,?)", {accountId, role});
    appendAudit("local_operator", "role_provisioned", accountId + ":" + role);
}
} // namespace cda
