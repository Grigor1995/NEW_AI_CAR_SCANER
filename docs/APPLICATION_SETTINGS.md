# Persistent settings

Device-local QSettings stores language (en/hy/ru/fr), units (metric/imperial) and theme (dark/light/system). Those fields can be saved to a signed-in account in SQLite through an explicit whitelist; additional arbitrary fields are discarded. Sign-in loads account preferences and runtime language changes retranslate the QML engine. No secret or bearer is stored in QSettings.

Diagnostic refresh currently uses a fixed one-second timer, connection timeout 5 s, PID reads 3 s and initial protocol discovery 35 s. Advanced timeout/retry/AI/update/privacy preferences, notifications, multi-device conflict resolution and secure remote settings synchronization are NOT IMPLEMENTED. Do not describe device persistence as complete cloud settings functionality.
