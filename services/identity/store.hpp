#pragma once
#include <QJsonObject>
#include <QSqlDatabase>
#include <QString>
#include <QVariantList>
namespace cda {
class Store final {
    QString connection_;
    QSqlDatabase db_;
    void run(const QString &sql, const QVariantList &args = {}) const;

  public:
    explicit Store(const QString &filename);
    ~Store();
    Store(const Store &) = delete;
    Store &operator=(const Store &) = delete;
    QJsonObject registerAccount(QString email, const QString &password);
    QJsonObject login(QString email, const QString &password);
    QJsonObject account(const QString &bearer) const;
    void logout(const QString &bearer);
    QJsonObject addVehicle(const QString &bearer, const QJsonObject &vehicle);
    QJsonArray vehicles(const QString &bearer) const;
    QJsonObject settings(const QString &bearer) const;
    void saveSettings(const QString &bearer, const QJsonObject &settings);
    void provisionRole(const QString &accountId, const QString &role);
    void appendAudit(const QString &actor, const QString &action, const QString &subject);
};
} // namespace cda
