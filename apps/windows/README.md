# Windows desktop — BUILD NOT RUN ON THIS LINUX HOST

Use a Qt 6.8+ desktop kit with Quick, QuickControls2, Sql/SQLite, SerialPort,
HttpServer/WebSockets, Svg and LinguistTools; CMake 3.24+, Ninja and OpenSSL 3.
Compiler, Qt and OpenSSL architectures/toolchains must match. In Git Bash with
those toolchains on PATH, set QT_ROOT and run scripts/build/windows-git-bash.sh.
The ICO is attached through app.rc. Use windeployqt to collect Qt/QML plugins
before packaging. Code signing and signed update installation are not configured.
The prior Python launch commands do not apply to this V3 rewrite.
