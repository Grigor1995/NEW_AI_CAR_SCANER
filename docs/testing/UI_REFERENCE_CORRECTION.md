# Reference launcher and readable controls

The user reported that the V3 home did not match the supplied original launcher,
and that Windows Qt 6.12 rendered pale text on native white Settings controls.
The new UI restores the supplied visual layout and makes control styling explicit.

## Result

- AI CAR SCANNER title/tagline, compact Application/Help menu and original
  automotive/circuit background.
- Twelve transparent rounded cards, default order and 3D icons matching the
  reference. Artwork is bundled locally from the original project at the user's
  explicit request; legacy application source stays removed.
- Mouse/trackpad drag reorder with validated, persistent device-local order;
  two-column touch-scroll layout on narrow screens.
- Existing account/preferences and secondary areas remain in Application.
- Basic-derived controls explicitly define foreground, surfaces, placeholder,
  selection, popup, hover/focus and disabled text colors. Popup.Item avoids
  native popup styling mismatches. Light-theme semantic colors also use
  readable darker variants.
- Real menu navigation regression found and fixed a zero-width popup, and drag
  regression found and fixed a deferred callback using a destroyed delegate.

Current screenshots from the compiled application:

- [Reference home](ui-reference/home.png)
- [Settings, dark](ui-reference/settings-dark.png)
- [Settings, light](ui-reference/settings-light.png)
- [Application menu](ui-reference/application-menu.png)
- [Narrow layout](ui-reference/mobile.png)

## Verification

18 UI checks passed with 0 failures. Tests exercise actual pointer dragging,
card/menu navigation, dropdown keyboard input and text entry; assert >=4.5:1
text contrast for Settings controls and the safety-state label in both themes;
check image loading and desktop/mobile layout; and capture real screenshots.
The app is explicitly Basic even when an external Fusion style is requested.
Both existing core/integration CTest executables also passed. Four catalogs have
137 completed matching messages; source/catalog contracts passed (565 assertions,
not 565 independent application scenarios).

Executed on Linux with Qt 6.8.2, offscreen/software rendering. The reported
Windows Qt 6.12 defect is addressed by deterministic controls in source; a new
native Windows or Android execution is not claimed. No new diagnostic workflow
is implied by its reference tile; Guided Tests, Teach AI and ECU Network remain
explicitly unimplemented destination pages.

[Machine-readable results](ui-reference/results.json) ·
[UI execution log](ui-reference/ui-regression.log).

Reproduce from the repository root after a testing-enabled build:

```bash
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
  ./build/dev/car_diagnostic --ui-regression artifacts/ui
```

This command restores the previous language, units, theme and tile order after
its checks. Use an isolated OS test profile for release QA. `BUILD_TESTING=OFF`
removes the Qt Test interaction helper from the application build.

## Update on Windows / MSYS2 UCRT64

Close the running application before rebuilding its executable, then:

```bash
cd /c/Users/grigorg/Projects/NEW_AI_CAR_SCANER_V3
git pull --ff-only
cmake --build --preset dev
./build/dev/car_diagnostic.exe
```

Preferences are now at **Application → Settings**. Rebuilding is necessary;
reopening an earlier executable cannot apply QML/asset/control changes.
