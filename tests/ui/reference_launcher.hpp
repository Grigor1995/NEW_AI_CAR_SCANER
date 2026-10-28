#pragma once
#include "apps/shared/app_model.hpp"
#include <QColor>
#include <QDir>
#include <QQuickItem>
#include <QQuickWindow>
#include <QTest>
#include <cmath>
#include <iostream>

inline QQuickItem *namedItem(QQuickItem *root, const QString &name) {
    if (root->objectName() == name)
        return root;
    for (auto *child : root->childItems())
        if (auto *found = namedItem(child, name))
            return found;
    return nullptr;
}
inline double textContrast(const QColor &a, const QColor &b) {
    auto luminance = [](const QColor &c) {
        auto linear = [](double n) {
            return n <= 0.04045 ? n / 12.92 : std::pow((n + 0.055) / 1.055, 2.4);
        };
        return 0.2126 * linear(c.redF()) + 0.7152 * linear(c.greenF()) + 0.0722 * linear(c.blueF());
    };
    double x = luminance(a), y = luminance(b);
    return (std::max(x, y) + 0.05) / (std::min(x, y) + 0.05);
}
inline bool runReferenceUiChecks(AppModel &model, QQuickWindow *window, const QString &output) {
    int passed = 0, failed = 0;
    auto check = [&](const char *name, bool ok) {
        std::cout << (ok ? "PASS " : "FAIL ") << name << '\n';
        ok ? ++passed : ++failed;
    };
    auto tick = []() {
        QCoreApplication::processEvents();
        QTest::qWait(80);
    };
    auto *root = window->contentItem();
    const auto originalOrder = model.launcherOrder();
    const auto originalLanguage = model.language(), originalTheme = model.theme(),
               originalUnits = model.units();
    model.setLanguage("en");
    model.setTheme("dark");
    model.setUnits("metric");
    window->resize(1405, 860);
    window->setProperty("page", "home");
    tick();
    QDir().mkpath(output);
    const QStringList expected{"vehicles", "diagnostics", "devices",   "symptoms",
                               "live",     "guided",      "ai",        "dtc",
                               "reports",  "teach",       "dashboard", "network"};
    // Reset only this isolated test profile; restore the original order below.
    for (int i = 0; i < expected.size(); ++i)
        model.moveLauncherTile(model.launcherOrder().indexOf(expected[i]), i);
    tick();
    check("reference has exactly twelve expected workflows", model.launcherOrder() == expected);
    auto *first = namedItem(root, "launcherTile_vehicles");
    auto *second = namedItem(root, "launcherTile_diagnostics");
    auto *rowTwo = namedItem(root, "launcherTile_live");
    auto *fourth = namedItem(root, "launcherTile_symptoms");
    check("four column reference layout",
          first && second && rowTwo && fourth &&
              std::abs(first->mapToScene({0, 0}).y() - fourth->mapToScene({0, 0}).y()) < 2 &&
              rowTwo->mapToScene({0, 0}).y() > first->mapToScene({0, 0}).y() + 100);
    auto *background = namedItem(root, "launcherBackground");
    check("reference background loaded", background && background->property("status").toInt() == 1);
    bool artwork = true;
    for (const auto &key : expected) {
        auto *image = namedItem(root, "launcherIcon_" + key);
        artwork = artwork && image && image->property("status").toInt() == 1;
    }
    check("all twelve 3D/reference images loaded", artwork);
    check("home screenshot", window->grabWindow().save(output + "/reference-home.png"));
    if (first && second) {
        const auto a = first->mapToScene({first->width() / 2, first->height() / 2}).toPoint();
        const auto b = second->mapToScene({second->width() / 2, second->height() / 2}).toPoint();
        QTest::mousePress(window, Qt::LeftButton, Qt::NoModifier, a);
        QTest::mouseMove(window, a + QPoint(30, 0), 40);
        QTest::mouseMove(window, b, 40);
        QTest::mouseRelease(window, Qt::LeftButton, Qt::NoModifier, b);
        tick();
        check("pointer drag reorders tiles",
              model.launcherOrder()[0] == "diagnostics" && model.launcherOrder()[1] == "vehicles");
        model.moveLauncherTile(model.launcherOrder().indexOf("vehicles"), 0);
        tick();
    }
    auto *devices = namedItem(root, "launcherTile_devices");
    if (devices) {
        QTest::mouseClick(
            window, Qt::LeftButton, Qt::NoModifier,
            devices->mapToScene({devices->width() / 2, devices->height() / 2}).toPoint());
        tick();
    }
    check("VCI card navigates to device connection",
          window->property("page").toString() == "devices");
    window->setProperty("page", "home");
    tick();
    QTest::mouseMove(window, {42, 13});
    QTest::qWait(40);
    QTest::mouseClick(window, Qt::LeftButton, Qt::NoModifier, {42, 13});
    QTest::qWait(250);
    tick();
    auto *settingsMenu = namedItem(root, "settingsMenuItem");
    if (!settingsMenu)
        settingsMenu = window->findChild<QQuickItem *>("settingsMenuItem");
    window->grabWindow().save(output + "/application-menu.png");
    if (settingsMenu && settingsMenu->isVisible())
        QTest::mouseClick(
            window, Qt::LeftButton, Qt::NoModifier,
            settingsMenu->mapToScene({settingsMenu->width() / 2, settingsMenu->height() / 2})
                .toPoint());
    tick();
    check("Application menu opens Settings", window->property("page").toString() == "settings");
    // Continue validating controls even if a platform menu interaction failed.
    window->setProperty("page", "settings");
    tick();
    const QStringList controls{"settingsLanguageCombo", "settingsUnitsCombo", "settingsThemeCombo",
                               "savePreferencesButton"};
    for (const auto &theme : {"dark", "light"}) {
        model.setTheme(theme);
        tick();
        bool contrast = true;
        for (const auto &name : controls) {
            auto *control = namedItem(root, name);
            if (!control) {
                contrast = false;
                continue;
            }
            auto *text = control->property("contentItem").value<QQuickItem *>();
            auto *bg = control->property("background").value<QQuickItem *>();
            contrast = contrast && text && bg &&
                       textContrast(text->property("color").value<QColor>(),
                                    bg->property("color").value<QColor>()) >= 4.5;
        }
        check(QString("Settings controls readable in %1 theme").arg(theme).toUtf8().constData(),
              contrast);
        auto *safety = namedItem(root, "readOnlySafetyStatus");
        check("safety status text readable",
              safety &&
                  textContrast(safety->property("color").value<QColor>(), window->color()) >= 4.5);
        check("settings screenshot",
              window->grabWindow().save(output + "/settings-" + theme + ".png"));
    }
    model.setTheme("dark");
    tick();
    auto *units = namedItem(root, "settingsUnitsCombo");
    if (units) {
        QTest::mouseClick(window, Qt::LeftButton, Qt::NoModifier,
                          units->mapToScene({units->width() / 2, units->height() / 2}).toPoint());
        tick();
        QTest::keyClick(window, Qt::Key_Down);
        QTest::keyClick(window, Qt::Key_Return);
        tick();
    }
    check("unit dropdown can be changed with keyboard", model.units() == "imperial");
    model.setUnits("metric");
    window->setProperty("page", "vehicles");
    tick();
    auto *field = namedItem(root, "vehicleMakeField");
    if (field) {
        QTest::mouseClick(window, Qt::LeftButton, Qt::NoModifier,
                          field->mapToScene({field->width() / 2, field->height() / 2}).toPoint());
        QTest::keyClick(window, Qt::Key_A);
        tick();
    }
    check("text input visible and editable",
          field && field->property("text").toString() == "a" &&
              textContrast(field->property("color").value<QColor>(), field->property("background")
                                                                         .value<QQuickItem *>()
                                                                         ->property("color")
                                                                         .value<QColor>()) >= 4.5);
    window->resize(390, 844);
    window->setProperty("page", "home");
    tick();
    first = namedItem(root, "launcherTile_vehicles");
    second = namedItem(root, "launcherTile_diagnostics");
    rowTwo = namedItem(root, "launcherTile_devices");
    check("mobile launcher uses two columns",
          first && second && rowTwo &&
              std::abs(first->mapToScene({0, 0}).y() - second->mapToScene({0, 0}).y()) < 2 &&
              rowTwo->mapToScene({0, 0}).y() > first->mapToScene({0, 0}).y() + 100);
    check("mobile screenshot", window->grabWindow().save(output + "/reference-mobile.png"));
    for (int i = 0; i < originalOrder.size(); ++i)
        model.moveLauncherTile(model.launcherOrder().indexOf(originalOrder[i]), i);
    model.setLanguage(originalLanguage);
    model.setTheme(originalTheme);
    model.setUnits(originalUnits);
    std::cout << "UI REGRESSION RESULT " << passed << " passed, " << failed << " failed\n";
    return failed == 0;
}
