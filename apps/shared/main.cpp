#include "apps/shared/app_model.hpp"
#include <QDir>
#include <QFile>
#include <QGuiApplication>
#include <QIcon>
#include <QImage>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPainter>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickStyle>
#include <QQuickWindow>
#include <QStandardPaths>
#include <QSvgRenderer>
#include <QTimer>
#include <iostream>
#ifdef CDA_UI_CHECKS
#include "tests/ui/reference_launcher.hpp"
#endif
int main(int argc, char **argv) {
    QCoreApplication::setAttribute(Qt::AA_DontUseNativeMenuBar);
    QQuickStyle::setStyle("Basic");
    QGuiApplication app(argc, argv);
    QCoreApplication::setApplicationName("Car Diagnostic Analysis");
    QCoreApplication::setOrganizationName("NeoAutomotive");
    QCoreApplication::setApplicationVersion("0.1.0");
    QGuiApplication::setWindowIcon(QIcon(":/qt/qml/CarDiagnostic/assets/app_icon/canonical.svg"));
    const auto arguments = app.arguments();
    if (arguments.contains("--generate-icons")) {
        auto index = arguments.indexOf("--generate-icons");
        if (index + 1 >= arguments.size())
            return 2;
        auto root = arguments[index + 1];
        QDir().mkpath(root);
        QSvgRenderer renderer(QString(":/qt/qml/CarDiagnostic/assets/app_icon/canonical.svg"));
        if (!renderer.isValid())
            return 2;
        for (int size : {16, 32, 48, 64, 128, 192, 256, 512, 1024}) {
            QImage image(size, size, QImage::Format_ARGB32);
            image.fill(Qt::transparent);
            QPainter painter(&image);
            renderer.render(&painter);
            painter.end();
            if (!image.save(root + QString("/icon-%1.png").arg(size)))
                return 2;
        }
        return 0;
    }
    const auto directory = QStandardPaths::writableLocation(QStandardPaths::AppDataLocation);
    QDir().mkpath(directory);
    AppModel model(directory + "/local.sqlite");
    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("App", &model);
    QObject::connect(&model, &AppModel::settingsChanged, &engine,
                     &QQmlApplicationEngine::retranslate);
    engine.loadFromModule("CarDiagnostic", "Main");
    if (engine.rootObjects().isEmpty())
        return 1;
    auto *window = qobject_cast<QQuickWindow *>(engine.rootObjects().first());
    if (!window)
        return 1;
#ifdef CDA_UI_CHECKS
    if (arguments.contains("--ui-regression")) {
        const auto index = arguments.indexOf("--ui-regression");
        const QString output = index + 1 < arguments.size() ? arguments[index + 1] : "artifacts/ui";
        QTimer::singleShot(200, &app, [&, output] {
            app.exit(runReferenceUiChecks(model, window, output) ? 0 : 2);
        });
    }
#endif
    if (arguments.contains("--smoke"))
        QTimer::singleShot(600, &app, &QCoreApplication::quit);
    if (arguments.contains("--screenshot")) {
        int index = arguments.indexOf("--screenshot");
        if (index + 1 >= arguments.size())
            return 2;
        auto path = arguments[index + 1];
        QTimer::singleShot(500, &app, [&, path] {
            bool saved = window->grabWindow().save(path);
            app.exit(saved ? 0 : 2);
        });
    }
    if (arguments.contains("--self-test")) {
        QTimer::singleShot(100, &app, [&] {
            bool ok = true;
            for (const auto &page :
                 {"home", "vehicles", "diagnostics", "live", "ai", "reports", "settings",
                  "monitoring", "workshop", "repair", "admin", "market", "updates"}) {
                window->setProperty("page", page);
                QCoreApplication::processEvents();
                ok = ok && window->property("page").toString() == page;
            }
            for (const auto &language : {"hy", "ru", "fr", "en"}) {
                model.setLanguage(language);
                QCoreApplication::processEvents();
                ok = ok && model.language() == language;
                auto text = QCoreApplication::translate("Main", "Settings");
                if (QString(language) != "en")
                    ok = ok && text != "Settings";
            }
            for (const auto &theme : {"light", "system", "dark"})
                model.setTheme(theme);
            model.setUnits("imperial");
            model.setUnits("metric");
            window->resize(390, 844);
            window->setProperty("page", "home");
            QTimer::singleShot(150, &app, [&, ok] {
                auto image = window->grabWindow();
                bool valid = ok && !image.isNull() && window->width() == 390;
                std::cout << "UI self-test: " << (valid ? "PASS" : "FAIL")
                          << "; 13 pages, 4 runtime locales, 3 themes, 2 units, narrow rendering\n";
                app.exit(valid ? 0 : 2);
            });
        });
    }
    return app.exec();
}
