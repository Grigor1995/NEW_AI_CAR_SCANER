"""Cross-platform installed app icon regression checks, no GUI runtime required."""
from pathlib import Path
import struct
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def _png_info(path):
    data = (ROOT / path).read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    return struct.unpack(">IIBB", data[16:26]), data


def test_original_transparent_logo_and_ios_opaque_export():
    from PIL import Image, ImageChops
    sources = [
        "assets/AI-Car-Scanner-master.png",
        "assets/AI-Car-Scanner-mobile.png",
        "apps/mobile-android/app/src/main/res/drawable-nodpi/ic_launcher_foreground.png",
    ]
    pairs = [_png_info(path) for path in sources]
    assert all(meta == (1024, 1024, 8, 6) for meta, _ in pairs)
    assert len({data for _, data in pairs}) == 1
    with Image.open(ROOT / sources[0]) as master:
        assert master.getchannel('A').getextrema() == (0, 255)
        expected = Image.new('RGB', master.size, 'black')
        expected.paste(master, (0, 0), master.getchannel('A'))
    with Image.open(ROOT / "apps/mobile-ios/AICarScanner/Assets.xcassets/AppIcon.appiconset/ai-car-scanner-icon.png") as ios:
        assert ios.mode == 'RGB'
        assert ImageChops.difference(ios, expected).getbbox() is None


def test_android_api26_launcher_uses_inset_safe_area_and_same_foreground():
    xml = ROOT / "apps/mobile-android/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml"
    tree = ET.parse(xml)
    ns = "{http://schemas.android.com/apk/res/android}"
    foreground = tree.getroot().find("foreground")
    assert foreground is not None
    assert foreground.attrib[ns + "drawable"] == "@drawable/ic_launcher_safezone"
    assert tree.getroot().find("monochrome") is None
    inset = ET.parse(ROOT / "apps/mobile-android/app/src/main/res/drawable/ic_launcher_safezone.xml").getroot()
    assert inset.attrib[ns + "drawable"] == "@drawable/ic_launcher_foreground"
    for direction in ("Left", "Right", "Top", "Bottom"):
        assert inset.attrib[ns + "inset" + direction] == "18dp"
    gradle = (ROOT / "apps/mobile-android/app/build.gradle.kts").read_text()
    assert "minSdk = 26" in gradle


def test_ios_asset_catalog_references_opaque_shared_icon():
    import json
    contents = json.loads((ROOT / "apps/mobile-ios/AICarScanner/Assets.xcassets/AppIcon.appiconset/Contents.json").read_text())
    assert any(image.get("filename") == "ai-car-scanner-icon.png" for image in contents["images"])


def test_windows_release_always_stages_ico_from_desktop_master():
    spec = (ROOT / "apps/desktop/specs/AICarScanner.spec").read_text()
    assert 'source = project_root / "assets" / "AI-Car-Scanner-master.png"' in spec
    assert "helper.stage_icons(source, asset_root)" in spec
    assert 'icon_file = asset_root / "AI-Car-Scanner.ico"' in spec
    shell = (ROOT / "scripts/build_desktop_git_bash.sh").read_text()
    assert 'ICON_SOURCE="assets/AI-Car-Scanner-master.png"' in shell


def test_launcher_3d_menu_icon_source_preserved():
    paths = [
        ROOT / "assets/launcher/icons-3d.png",
        ROOT / "apps/mobile-android/app/src/main/res/drawable-nodpi/launcher_icons.png",
        ROOT / "apps/mobile-ios/AICarScanner/Launcher/launcher_icons.png",
    ]
    assert len({path.read_bytes() for path in paths}) == 1
