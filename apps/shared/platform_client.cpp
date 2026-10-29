#include "apps/shared/platform_client.hpp"
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkReply>
#include <QNetworkRequest>
PlatformClient::PlatformClient(QObject *parent) : QObject(parent) {
    QFile file(":/qt/qml/CarDiagnostic/assets/platform-operations.json");
    if (file.open(QIODevice::ReadOnly))
        operations_ = QJsonDocument::fromJson(file.readAll()).array().toVariantList();
}
void PlatformClient::request(const QString &method, const QString &path, const QString &json) {
    if (busy_)
        return;
    auto fail = [this](const QString &message) {
        response_ = message;
        emit changed();
    };
    if (!QStringList{"GET", "POST", "PUT", "DELETE", "PATCH"}.contains(method) ||
        (!path.startsWith("/api/v1/") && !path.startsWith("/api/v2/ecosystem/") &&
         path != "/health") ||
        path.contains("..") || path.contains("#") || path.contains("\\")) {
        fail(tr("Invalid platform operation"));
        return;
    }
    QByteArray payload;
    if (method != "GET" && !json.trimmed().isEmpty()) {
        QJsonParseError error;
        const auto doc = QJsonDocument::fromJson(json.toUtf8(), &error);
        if (error.error != QJsonParseError::NoError || (!doc.isObject() && !doc.isArray())) {
            fail(tr("Request must contain valid JSON"));
            return;
        }
        payload = doc.toJson(QJsonDocument::Compact);
    }
    if (payload.size() > 8 * 1024 * 1024) {
        fail(tr("Request too large"));
        return;
    }
    const QUrl url("http://127.0.0.1:8001" + path);
    if (url.host() != "127.0.0.1" || url.port() != 8001) {
        fail(tr("Loopback API required"));
        return;
    }
    QNetworkRequest request(url);
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    if (!bearer_.isEmpty())
        request.setRawHeader("Authorization", "Bearer " + bearer_.toUtf8());
    request.setTransferTimeout(45000);
    request.setAttribute(QNetworkRequest::RedirectPolicyAttribute,
                         QNetworkRequest::ManualRedirectPolicy);
    busy_ = true;
    emit changed();
    auto *reply = network_.sendCustomRequest(request, method.toLatin1(), payload);
    connect(reply, &QNetworkReply::finished, this, [this, reply] {
        busy_ = false;
        const auto bytes = reply->readAll();
        const auto doc = QJsonDocument::fromJson(bytes);
        if (reply->error() != QNetworkReply::NoError)
            response_ = tr("Platform request failed: ") + reply->errorString() + "\n" +
                        QString::fromUtf8(bytes);
        else if (!doc.isNull()) {
            response_ = QString::fromUtf8(doc.toJson(QJsonDocument::Indented));
            if (doc.object().contains("hypotheses"))
                analysis_ = doc.object().toVariantMap();
            if (doc.isArray())
                searchResults_ = doc.array().toVariantList();
            const auto token = doc.object().value("access_token").toString();
            if (!token.isEmpty())
                bearer_ = token;
            const auto session = doc.object().value("session_id").toString();
            if (!session.isEmpty())
                sessionId_ = session;
        } else
            response_ = QString::fromUtf8(bytes);
        reply->deleteLater();
        emit changed();
    });
}
