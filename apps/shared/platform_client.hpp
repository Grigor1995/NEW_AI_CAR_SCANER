#pragma once
#include <QJsonArray>
#include <QNetworkAccessManager>
#include <QObject>
#include <QVariantList>
class PlatformClient final : public QObject {
    Q_OBJECT
    Q_PROPERTY(QVariantList operations READ operations CONSTANT)
    Q_PROPERTY(QVariantMap analysis READ analysis NOTIFY changed)
    Q_PROPERTY(QVariantList searchResults READ searchResults NOTIFY changed)
    Q_PROPERTY(QString response READ response NOTIFY changed)
    Q_PROPERTY(QString sessionId READ sessionId NOTIFY changed)
    Q_PROPERTY(bool busy READ busy NOTIFY changed)
    QNetworkAccessManager network_;
    QVariantList operations_, searchResults_;
    QVariantMap analysis_;
    QString response_, sessionId_, bearer_;
    bool busy_ = false;

  public:
    explicit PlatformClient(QObject *parent = nullptr);
    QVariantList operations() const {
        return operations_;
    }
    QVariantMap analysis() const {
        return analysis_;
    }
    QVariantList searchResults() const {
        return searchResults_;
    }
    QString response() const {
        return response_;
    }
    QString sessionId() const {
        return sessionId_;
    }
    bool busy() const {
        return busy_;
    }
    Q_INVOKABLE void setBearerToken(const QString &token) {
        bearer_ = token.trimmed();
    }
    Q_INVOKABLE void request(const QString &method, const QString &path, const QString &json);
  signals:
    void changed();
};
