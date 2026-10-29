#include "core/transport/qt_elm.hpp"
#include "services/diagnostics/controller.hpp"
#include "services/identity/store.hpp"
#include <QJsonArray>
#include <QSignalSpy>
#include <QSqlDatabase>
#include <QSqlQuery>
#include <QTcpServer>
#include <QTcpSocket>
#include <QTemporaryDir>
#include <QtTest>
class ServiceTests : public QObject {
    Q_OBJECT
  private slots:
    void ownershipAndRevocation() {
        QTemporaryDir dir;
        QVERIFY(dir.isValid());
        auto path = dir.filePath("identity.sqlite");
        QString token;
        {
            cda::Store store(path);
            auto a = store.registerAccount("Owner@example.org", "long correct password");
            QVERIFY(!a["emailVerified"].toBool());
            auto first = store.login("owner@example.org", "long correct password");
            token = first["token"].toString();
            QCOMPARE(first["roles"].toArray(), QJsonArray{"USER"});
            store.registerAccount("other@example.org", "long other password");
            auto second = store.login("other@example.org", "long other password");
            auto v = store.addVehicle(
                token, {{"make", "Mercedes-Benz"}, {"model", "E350"}, {"year", 2006}});
            QVERIFY(!v["identityVerified"].toBool());
            QCOMPARE(store.vehicles(token).size(), 1);
            QCOMPARE(store.vehicles(second["token"].toString()).size(), 0);
            QVERIFY_EXCEPTION_THROWN(store.login("owner@example.org", "wrong but long password"),
                                     std::invalid_argument);
            QVERIFY_EXCEPTION_THROWN(
                store.registerAccount("owner@example.org", "long correct password"),
                std::invalid_argument);
            QVERIFY_EXCEPTION_THROWN(store.account("not a bearer"), std::invalid_argument);
            QVERIFY_EXCEPTION_THROWN(
                store.addVehicle(token, {{"make", ""}, {"model", "X"}, {"year", 2000}}),
                std::invalid_argument);
            QVERIFY_EXCEPTION_THROWN(
                store.addVehicle(
                    token, {{"make", "A"}, {"model", "B"}, {"year", 2000}, {"vin", "INVALID"}}),
                std::invalid_argument);
            store.saveSettings(token, {{"language", "fr"},
                                       {"units", "imperial"},
                                       {"theme", "light"},
                                       {"token", "must_not_persist"}});
            QVERIFY(!store.settings(token).contains("token"));
            QVERIFY_EXCEPTION_THROWN(
                store.saveSettings(token,
                                   {{"language", "de"}, {"units", "metric"}, {"theme", "dark"}}),
                std::invalid_argument);
            store.provisionRole(a["id"].toString(), "CUSTOMER");
            QVERIFY(store.account(token)["roles"].toArray().contains("CUSTOMER"));
        }
        {
            cda::Store store(path);
            QCOMPARE(store.vehicles(token).size(), 1);
            QCOMPARE(store.settings(token)["language"].toString(), QString("fr"));
            store.logout(token);
            QVERIFY_EXCEPTION_THROWN(store.account(token), std::invalid_argument);
        }
    }
    void expiryAndAccountDeactivation() {
        QTemporaryDir dir;
        const auto path = dir.filePath("policy.sqlite");
        cda::Store store(path);
        store.registerAccount("policy@example.org", "policy test password");
        auto token = store.login("policy@example.org", "policy test password")["token"].toString();
        auto db = QSqlDatabase::addDatabase("QSQLITE", "policy_fixture");
        db.setDatabaseName(path);
        QVERIFY(db.open());
        {
            QSqlQuery q(db);
            QVERIFY(q.exec("SELECT hash FROM tokens"));
            QVERIFY(q.next());
            QVERIFY(q.value(0).toString() != token);
            q.finish();
            QVERIFY(q.exec("UPDATE tokens SET expires=0"));
            QVERIFY_EXCEPTION_THROWN(store.account(token), std::invalid_argument);
            token = store.login("policy@example.org", "policy test password")["token"].toString();
            QVERIFY(q.exec("UPDATE accounts SET active=0"));
            QVERIFY_EXCEPTION_THROWN(store.account(token), std::invalid_argument);
            QVERIFY_EXCEPTION_THROWN(store.login("policy@example.org", "policy test password"),
                                     std::invalid_argument);
        }
        db.close();
        db = QSqlDatabase();
        QSqlDatabase::removeDatabase("policy_fixture");
        QVERIFY_EXCEPTION_THROWN(store.registerAccount("bad-email", "policy test password"),
                                 std::invalid_argument);
        QVERIFY_EXCEPTION_THROWN(store.registerAccount("new@example.org", "short"),
                                 std::invalid_argument);
    }
    void transportReadOnlyAndFragmentation() {
        QTcpServer server;
        QVERIFY(server.listen(QHostAddress::LocalHost));
        cda::QtElm transport;
        QSignalSpy ready(&transport, &cda::QtElm::ready), reply(&transport, &cda::QtElm::reply),
            error(&transport, &cda::QtElm::failed);
        transport.connectTcp("127.0.0.1", server.serverPort());
        QTRY_COMPARE(ready.size(), 1);
        QTRY_VERIFY(server.hasPendingConnections());
        auto *peer = server.nextPendingConnection();
        transport.readCommand("04");
        QCOMPARE(error.size(), 1);
        QCOMPARE(peer->bytesAvailable(), qint64(0));
        transport.readCommand("010C");
        QTRY_COMPARE(peer->bytesAvailable(), qint64(5));
        QCOMPARE(peer->readAll(), QByteArray("010C\r"));
        peer->write("410C");
        peer->flush();
        QTest::qWait(10);
        QCOMPARE(reply.size(), 0);
        peer->write("1AF8>");
        peer->flush();
        QTRY_COMPARE(reply.size(), 1);
        QCOMPARE(reply[0][0].toString(), QString("410C1AF8>"));
        transport.readCommand("010C", 30);
        QTRY_COMPARE(error.size(), 2);
        QVERIFY(!transport.connected());
        peer->deleteLater();
    }
    void controllerPollsAllNativeChannelsAcrossEcus() {
        QTcpServer server;
        QVERIFY(server.listen(QHostAddress::LocalHost));
        connect(&server, &QTcpServer::newConnection, &server, [&] {
            auto *peer = server.nextPendingConnection();
            auto buffer = std::make_shared<QByteArray>();
            connect(peer, &QTcpSocket::readyRead, peer, [peer, buffer] {
                *buffer += peer->readAll();
                while (buffer->contains('\r')) {
                    auto at = buffer->indexOf('\r');
                    auto cmd = buffer->left(at);
                    buffer->remove(0, at + 1);
                    QByteArray response = "OK";
                    if (cmd == "0100") {
                        quint32 mask = 0;
                        for (auto pid : {4, 5, 6, 7, 11, 13, 15, 16, 17})
                            mask |= quint32(1) << (32 - pid);
                        response = "410000100000\r4100" +
                                   QByteArray::number(mask, 16).rightJustified(8, '0');
                    } else if (cmd.startsWith("01")) {
                        response =
                            "41" + cmd.mid(2) + (cmd == "010C" || cmd == "0110" ? "0100" : "40");
                    }
                    peer->write(response + ">\r");
                }
            });
        });
        cda::DiagnosticController controller;
        controller.connectTcp("127.0.0.1", server.serverPort());
        QTRY_VERIFY(controller.ready());
        QCOMPARE(controller.values().size(), 10);
        auto allValid = [&] {
            for (const auto &value : controller.values())
                if (value.toMap()["quality"] != "valid")
                    return false;
            return true;
        };
        QTRY_VERIFY_WITH_TIMEOUT(allValid(), 15000);
        controller.disconnectDevice();
    }
    void controllerUsesCapabilityBitmap() {
        QTcpServer server;
        QVERIFY(server.listen(QHostAddress::LocalHost));
        connect(&server, &QTcpServer::newConnection, &server, [&] {
            auto *peer = server.nextPendingConnection();
            auto buffer = std::make_shared<QByteArray>();
            connect(peer, &QTcpSocket::readyRead, peer, [peer, buffer] {
                *buffer += peer->readAll();
                while (buffer->contains('\r')) {
                    auto at = buffer->indexOf('\r');
                    auto cmd = buffer->left(at);
                    buffer->remove(0, at + 1);
                    QByteArray response = cmd == "0100"   ? "410000100000"
                                          : cmd == "010C" ? "410C1AF8"
                                          : cmd == "03"   ? "430302"
                                                          : "OK";
                    peer->write(response + ">\r");
                }
            });
        });
        cda::DiagnosticController controller;
        controller.connectTcp("127.0.0.1", server.serverPort());
        QTRY_VERIFY(controller.ready());
        QTRY_COMPARE(controller.values()[0].toMap()["quality"].toString(), QString("valid"));
        QCOMPARE(controller.values()[0].toMap()["value"].toDouble(), 1726.0);
        QCOMPARE(controller.values()[1].toMap()["quality"].toString(), QString("unsupported"));
        controller.readDtcs();
        QTRY_COMPARE(controller.dtcs(), QStringList{"P0302"});
        controller.disconnectDevice();
        QVERIFY(!controller.ready());
        QVERIFY(controller.values()[0].toMap()["value"].isNull());
    }
};
QTEST_GUILESS_MAIN(ServiceTests)
#include "service_tests.moc"
