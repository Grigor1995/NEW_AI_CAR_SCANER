#include "services/identity/store.hpp"
#include <QCommandLineParser>
#include <QCoreApplication>
#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QHash>
#include <QHttpServer>
#include <QHttpServerRequest>
#include <QHttpServerResponse>
#include <QJsonArray>
#include <QJsonDocument>
#include <QRegularExpression>
#include <QStandardPaths>
#include <QTcpServer>
#include <QTimer>
#include <iostream>
using Response = QHttpServerResponse;
using Status = QHttpServerResponse::StatusCode;
namespace {
Response error(Status status, const QString &code) {
    return Response(QJsonObject{{"error", code}}, status);
}
QJsonObject body(const QHttpServerRequest &r) {
    if (r.body().size() > 16384)
        throw std::invalid_argument("Body limit");
    QJsonParseError e;
    auto doc = QJsonDocument::fromJson(r.body(), &e);
    if (e.error != QJsonParseError::NoError || !doc.isObject())
        throw std::invalid_argument("JSON object required");
    return doc.object();
}
QString bearer(const QHttpServerRequest &r) {
    auto h = r.value("Authorization");
    return h.startsWith("Bearer ") ? QString::fromLatin1(h.mid(7)) : QString();
}
} // namespace
int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    QCoreApplication::setApplicationName("cda_backend");
    QCommandLineParser args;
    args.addHelpOption();
    args.addOptions({{{"d", "database"}, "SQLite file", "path", "local/backend.sqlite"},
                     {{"p", "port"}, "Loopback port", "port", "8081"},
                     {"provision-account", "Local operator account ID", "id"},
                     {"provision-role", "Local operator role", "role"}});
    args.addOption({"docs", "Documentation directory", "path", "docs"});
    args.process(app);
    try {
        cda::Store store(args.value("database"));
        if (args.isSet("provision-account")) {
            store.provisionRole(args.value("provision-account"), args.value("provision-role"));
            std::cout << "Role provisioned locally\n";
            return 0;
        }
        QHttpServer server;
        QTcpServer tcp;
        // This initial host is deliberately loopback-only. Remote deployment needs TLS and
        // operational hardening.
        bool valid = false;
        auto port = args.value("port").toUShort(&valid);
        if (!valid || port == 0)
            throw std::invalid_argument("Invalid port");
        auto protectedCall = [&](const QHttpServerRequest &r, auto fn) -> Response {
            QString token = bearer(r);
            try {
                store.account(token);
            } catch (const std::exception &) {
                return error(Status::Unauthorized, "authentication_required");
            }
            try {
                return fn(token);
            } catch (const std::invalid_argument &) {
                return error(Status::UnprocessableEntity, "invalid_request");
            } catch (const std::exception &) {
                return error(Status::InternalServerError, "operation_failed");
            }
        };
        server.route("/api/v1/health", QHttpServerRequest::Method::Get, [] {
            return QJsonObject{{"status", "ok"},
                               {"version", "0.1.0"},
                               {"database", "sqlite_open"},
                               {"obd", "UNKNOWN"},
                               {"aiProvider", "UNAVAILABLE"},
                               {"notifications", "UNAVAILABLE"}};
        });
        int authAttempts = 0;
        QTimer reset;
        reset.start(60000);
        QObject::connect(&reset, &QTimer::timeout, &app, [&] { authAttempts = 0; });
        auto auth = [&](const QHttpServerRequest &r, bool registration) -> Response {
            if (++authAttempts > 20)
                return error(Status::TooManyRequests, "rate_limited");
            try {
                auto b = body(r);
                auto email = b["email"].toString(), password = b["password"].toString();
                if (registration)
                    return Response(store.registerAccount(email, password), Status::Created);
                return Response(store.login(email, password));
            } catch (const std::invalid_argument &) {
                return error(registration ? Status::UnprocessableEntity : Status::Unauthorized,
                             "invalid_credentials_or_registration");
            } catch (const std::exception &) {
                return error(Status::InternalServerError, "operation_failed");
            }
        };
        server.route("/api/v1/accounts", QHttpServerRequest::Method::Post,
                     [&](const QHttpServerRequest &r) { return auth(r, true); });
        server.route("/api/v1/sessions", QHttpServerRequest::Method::Post,
                     [&](const QHttpServerRequest &r) { return auth(r, false); });
        server.route("/api/v1/me", QHttpServerRequest::Method::Get,
                     [&](const QHttpServerRequest &r) {
                         return protectedCall(
                             r, [&](const QString &t) { return Response(store.account(t)); });
                     });
        server.route("/api/v1/sessions/current", QHttpServerRequest::Method::Delete,
                     [&](const QHttpServerRequest &r) {
                         return protectedCall(r, [&](const QString &t) {
                             store.logout(t);
                             return Response(Status::NoContent);
                         });
                     });
        server.route("/api/v1/vehicles", QHttpServerRequest::Method::Get,
                     [&](const QHttpServerRequest &r) {
                         return protectedCall(
                             r, [&](const QString &t) { return Response(store.vehicles(t)); });
                     });
        server.route("/api/v1/vehicles", QHttpServerRequest::Method::Post,
                     [&](const QHttpServerRequest &r) {
                         return protectedCall(r, [&](const QString &t) {
                             return Response(store.addVehicle(t, body(r)), Status::Created);
                         });
                     });
        server.route("/api/v1/settings", QHttpServerRequest::Method::Get,
                     [&](const QHttpServerRequest &r) {
                         return protectedCall(
                             r, [&](const QString &t) { return Response(store.settings(t)); });
                     });
        server.route("/api/v1/settings", QHttpServerRequest::Method::Put,
                     [&](const QHttpServerRequest &r) {
                         return protectedCall(r, [&](const QString &t) {
                             store.saveSettings(t, body(r));
                             return Response(store.settings(t));
                         });
                     });
        server.route("/api/v1/capabilities", QHttpServerRequest::Method::Get, [] {
            return QJsonObject{{"primaryModes", QJsonArray{"USER", "CUSTOMER", "ADMIN"}},
                               {"merchantPortal", "MARKET"},
                               {"physicalHardwareValidated", false},
                               {"ecuWrites", "LOCKED"},
                               {"payments", "NOT_IMPLEMENTED"},
                               {"distributedDeployment", "NOT_READY"}};
        });
        const QString docRoot = QFileInfo(args.value("docs")).absoluteFilePath();
        auto staticFile = [](const QString &path, const QByteArray &mime) -> Response {
            QFile file(path);
            if (!file.open(QIODevice::ReadOnly))
                return error(Status::NotFound, "document_unavailable");
            if (file.size() > 4 * 1024 * 1024)
                return error(Status::PayloadTooLarge, "document_limit");
            return Response(mime, file.readAll());
        };
        server.route("/architecture/<arg>", QHttpServerRequest::Method::Get,
                     [&](const QString &name) -> Response {
                         const QHash<QString, QByteArray> allowed{
                             {"interactive_architecture.html", "text/html; charset=utf-8"},
                             {"dashboard.css", "text/css"},
                             {"dashboard.js", "application/javascript"},
                             {"data.js", "application/javascript"},
                             {"data.json", "application/json"}};
                         if (!allowed.contains(name))
                             return error(Status::NotFound, "document_unavailable");
                         return staticFile(docRoot + "/architecture/" + name, allowed[name]);
                     });
        server.route("/assets/app_icon/canonical.svg", QHttpServerRequest::Method::Get, [&]() {
            return staticFile(docRoot + "/../assets/app_icon/canonical.svg", "image/svg+xml");
        });
        server.route("/<arg>", QHttpServerRequest::Method::Get,
                     [&](const QString &name) -> Response {
                         if (!QRegularExpression("^[A-Z_]+\\.md$").match(name).hasMatch())
                             return error(Status::NotFound, "document_unavailable");
                         return staticFile(docRoot + "/" + name, "text/plain; charset=utf-8");
                     });
        if (!tcp.listen(QHostAddress::LocalHost, port) || !server.bind(&tcp))
            throw std::runtime_error("Cannot bind loopback backend");
        std::cout << "CDA backend listening on loopback port " << port << std::endl;
        return app.exec();
    } catch (const std::exception &e) {
        std::cerr << "Backend startup failed: " << e.what() << '\n';
        return 1;
    }
}
