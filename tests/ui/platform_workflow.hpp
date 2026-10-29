#pragma once
#include "apps/shared/platform_client.hpp"
#include <QElapsedTimer>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QQuickWindow>
#include <QtTest/QTest>
#include <iostream>
inline bool runPlatformWorkflow(PlatformClient &client, QQuickWindow *window,
                                const QString &screenshot) {
    int passed = 0;
    auto send = [&](const QString &method, const QString &path, const QJsonObject &body) {
        client.request(method, path, QString::fromUtf8(QJsonDocument(body).toJson()));
        QElapsedTimer timer;
        timer.start();
        while (client.busy() && timer.elapsed() < 15000)
            QTest::qWait(10);
        QJsonParseError error;
        auto response = QJsonDocument::fromJson(client.response().toUtf8(), &error);
        bool ok = !client.busy() && error.error == QJsonParseError::NoError && !response.isNull();
        std::cout << (ok ? "PASS " : "FAIL ") << method.toStdString() << " " << path.toStdString()
                  << "\n";
        if (ok)
            ++passed;
        return response;
    };
    if (client.operations().size() < 119)
        return false;
    if (!send("GET", "/api/v1/migration/runtime", {})
             .object()["native"]
             .toObject()["available"]
             .toBool())
        return false;
    send("POST", "/api/v1/sessions", {});
    if (client.sessionId().isEmpty())
        return false;
    auto sid = client.sessionId();
    send("POST", "/api/v1/sessions/" + sid + "/symptoms",
         {{"raw_text", "Misfire on LPG; normal on petrol"}});
    send("POST", "/api/v1/sessions/" + sid + "/dtcs",
         {{"code", "P0302"}, {"source", "USER_REPORTED"}});
    auto analysis = send("POST", "/api/v1/intelligence/sessions/" + sid + "/analyze", {});
    if (analysis.object()["hypotheses"].toArray().isEmpty())
        return false;
    send("GET", "/api/v1/decision/sessions/" + sid + "/plan", {});
    send("GET", "/api/v1/network-discovery/sessions/" + sid + "/map", {});
    send("POST", "/api/v1/ai/knowledge",
         {{"document_id", "native-ui-regression"},
          {"title", "LPG misfire reference"},
          {"text", "Compare petrol and LPG fuel delivery; inspect ignition."},
          {"metadata", QJsonObject{}}});
    if (send("POST", "/api/v1/ai/knowledge/search", {{"query", "LPG misfire"}, {"top_k", 5}})
            .array()
            .isEmpty())
        return false;
    client.request("POST", "/api/v1/sessions", "invalid-json");
    if (client.busy() || !client.response().contains("valid JSON"))
        return false;
    ++passed;
    std::cout << "PASS malformed JSON rejected locally\n";
    window->setProperty("page", "platform");
    QTest::qWait(150);
    if (!screenshot.isEmpty() && !window->grabWindow().save(screenshot))
        return false;
    std::cout << "PLATFORM UI WORKFLOW " << passed << " passed\n";
    return passed == 10;
}
