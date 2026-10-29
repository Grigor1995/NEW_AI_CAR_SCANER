"""Static cross-platform UI issue contracts (no Qt/Android/iOS runtime required).

These protect requested navigation, layout and image precedence. Actual Qt,
Compose and SwiftUI rendering still require their native runtimes.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "apps/desktop/ui.py"
DESKTOP_ART = ROOT / "apps/desktop/vehicle_artwork.py"
ANDROID_NAV = ROOT / "apps/mobile-android/app/src/main/java/com/aicarscaner/mobile/presentation/DashboardNavigation.kt"
ANDROID_SCREEN = ROOT / "apps/mobile-android/app/src/main/java/com/aicarscaner/mobile/presentation/DiagnosticScreen.kt"
IOS_SCREEN = ROOT / "apps/mobile-ios/AICarScanner/DiagnosticScreen.swift"
IOS_ART = ROOT / "apps/mobile-ios/AICarScanner/VehicleModelArtwork.swift"
IOS_THEME = ROOT / "apps/mobile-ios/AICarScanner/AutomotiveTheme.swift"


def test_issue_21_live_data_has_numeric_inputs_but_no_slider_widgets():
    code = DESKTOP.read_text(encoding="utf-8")
    assert "QSlider" not in code
    assert "self.sim_sliders" not in code
    for channel in ("rpm", "coolant_c", "speed_kmh", "throttle_percent"):
        assert f'("{channel}",' in code
    assert "QDoubleSpinBox()" in code
    assert 'self.app.settings_store.value("unit_system", "metric")' in code


def test_issue_20_desktop_settings_have_one_application_menu_entry():
    code = DESKTOP.read_text(encoding="utf-8")
    menu = code.split("def _build_menu(self):", 1)[1].split("def run_worker(", 1)[0]
    assert 'addMenu("Application")' in menu
    assert 'QAction("Settings…", self)' in menu
    assert "settings_action.triggered.connect(self._open_settings)" in menu
    header = code.split("def _build_pages(self):", 1)[1].split("def _decorate_page(", 1)[0]
    assert "QPushButton(\"Settings\")" not in header
    assert "Settings…" not in header


def test_issue_20_mobile_settings_are_inside_overflow_application_menu():
    android = ANDROID_NAV.read_text(encoding="utf-8")
    ios = IOS_SCREEN.read_text(encoding="utf-8")
    assert 'contentDescription="Application menu"' in android
    assert "DropdownMenuItem(text={Text(text.settings)}" in android
    assert "Menu { Button(t.settings){settingsOpen=true} }" in ios
    assert '.accessibilityLabel("Application menu")' in ios


def test_issue_18_android_icon_caller_controls_size_and_neon_tiles_are_compact():
    text = ANDROID_NAV.read_text(encoding="utf-8")
    assert "modifier: Modifier = Modifier.size(24.dp)" in text
    assert "Image(bitmap=icon,contentDescription=null,modifier=modifier)" in text
    assert "Modifier.size(44.dp)" not in text
    assert "LauncherTileContent(id,dashboardLabel(title))" in text
    assert ".heightIn(min=112.dp)" in text


def test_issue_19_vehicle_tiles_use_app_artwork_not_model_specific_brand_car():
    desktop = DESKTOP.read_text(encoding="utf-8")
    android = ANDROID_NAV.read_text(encoding="utf-8")
    ios = IOS_THEME.read_text(encoding="utf-8")
    assert 'return QIcon(str(root / "assets" / "launcher" / "brand-car.png"))' in desktop
    assert "if(kind==1 || kind==11) BitmapFactory.decodeResource(resources,R.drawable.launcher_car)" in android
    assert "result[0]=car;result[12]=car" in ios


def test_issues_22_23_real_vehicle_photos_have_cross_platform_neon_framing():
    desktop = DESKTOP_ART.read_text(encoding="utf-8")
    android = ANDROID_SCREEN.read_text(encoding="utf-8")
    ios = IOS_ART.read_text(encoding="utf-8")
    assert "class NeonVehiclePreview(QLabel)" in desktop
    assert "border: 2px solid #26BFFF" in desktop
    assert 'Color(0xFF35C8FF)' in android
    assert "Brush.linearGradient(listOf(Color(0xFF03070E)" in android
    assert "stroke(AutomotivePalette.cyan.opacity(0.9)" in ios
    assert "if let remoteURL {" in ios
    assert "val remote = withContext(Dispatchers.IO)" in android
    assert "load_backend_portrait" in desktop


def test_vehicle_photo_sources_not_destroyed_or_replaced_by_styling():
    android = ANDROID_SCREEN.read_text(encoding="utf-8")
    ios = IOS_ART.read_text(encoding="utf-8")
    assert "context.assets.open(file)" in android
    assert '"api/v1/vehicle-reference/image?"' in android
    assert "AsyncImage(url: remoteURL)" in ios
    assert "Bundle.main.url(forResource: name" in ios


def test_desktop_uses_only_responsive_top_navigation_including_main_menu():
    code = DESKTOP.read_text(encoding="utf-8")
    screen = code.split("def _build_pages(self):", 1)[1].split("def _decorate_page(", 1)[0]
    assert '("Main menu", 12)' in screen
    assert '("Symptoms", 11)' in screen
    assert '("Diagnostics", 3)' in screen
    assert len(screen.split("button.setAccessibleName(title)")) == 2
    assert "self.top_navigation_buttons[target] = button" in screen
    assert "self.header_navigation = ResponsiveControls(" in screen
    assert "self.content = QStackedWidget()" in screen
    assert "self.navigate_page(12)" in screen
    assert "sideNav" not in screen
    assert "CompactNavigation()" not in screen
    assert "self.nav" not in code.replace("self.navigate_page", "")
    assert "self.content.setCurrentIndex(page_id)" in code
    assert "button.setChecked(target == page_id or (target == 12 and page_id not in self.top_navigation_buttons))" in code


def test_main_menu_restores_3d_icons_on_all_native_clients():
    desktop = DESKTOP.read_text(encoding="utf-8")
    android = ANDROID_NAV.read_text(encoding="utf-8")
    ios = IOS_SCREEN.read_text(encoding="utf-8")
    assert "class MovableMenuTile(AdaptiveMenuTile)" in desktop
    assert "tile.setIcon(_page_icon(page_id))" in desktop
    assert "tile.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)" in desktop
    card = android.split("private fun LauncherTileContent(",1)[1].split("/** Persistent actions",1)[0]
    assert "DashboardIcon(id,Modifier.size(56.dp))" in card
    assert "Text(title,style=MaterialTheme.typography.titleMedium" in card
    launcher = ios.split("private var desktopMenu:",1)[1].split("private var demoHome:",1)[0]
    assert "DesktopIcon(page:id).frame(width:64,height:64)" in launcher
    assert "Text(pageTitle(id))" in launcher


def test_top_nav_uses_original_sidebar_style_icons_and_hides_on_main_menu():
    source = DESKTOP.read_text(encoding="utf-8")
    top = source.split("top_sections = [", 1)[1].split("self.content = QStackedWidget()", 1)[0]
    assert "button = QToolButton()" in top
    assert "setIconSize(QSize(30, 30))" in top
    assert "Qt.ToolButtonTextBesideIcon" in top
    assert "setFixedHeight(54)" in top
    assert "widget.minimumHeight(), widget.sizeHint().height()" in source
    assert "self.header_navigation.setVisible(page_id != 12)" in source


def test_same_exact_launcher_artwork_is_packaged_on_all_clients():
    import hashlib
    def digest(path):
        return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    assert len({
        digest("assets/launcher/icons-3d.png"),
        digest("apps/mobile-android/app/src/main/res/drawable-nodpi/launcher_icons.png"),
        digest("apps/mobile-ios/AICarScanner/Launcher/launcher_icons.png"),
    }) == 1
    assert len({
        digest("assets/launcher/brand-car.png"),
        digest("apps/mobile-android/app/src/main/res/drawable-nodpi/launcher_car.png"),
        digest("apps/mobile-ios/AICarScanner/Launcher/launcher_car.png"),
    }) == 1


def test_icon_id_mapping_follows_workflow_meaning_not_client_page_number():
    desktop = DESKTOP.read_text(encoding="utf-8")
    android = ANDROID_NAV.read_text(encoding="utf-8")
    ios = IOS_THEME.read_text(encoding="utf-8")
    assert "order = [11, 3, 2, 1, 4, 6, 8, 7, 9, 10, 0, 5]" in desktop
    for mapped in ("0->0", "14->1", "2->2", "3->4", "8,13->5",
                   "4->6", "7->7", "9->8", "10->9", "6,12->10", "5->11"):
        assert mapped in android
    for mapped in ("11:0", "1:1", "3:2", "8:4", "7:5",
                   "2:6", "6:7", "9:8", "10:9", "5:10", "4:11"):
        assert mapped in ios
    assert "result[0]=car;result[12]=car" in ios
