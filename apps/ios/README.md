# iOS source integration — BUILD NOT RUN

The shared C++/QML client and canonical AppIcon asset catalog are provided.
Use macOS/Xcode, a Qt 6.8+ iOS kit and a compatible OpenSSL build, configure
CDA_BUILD_BACKEND=OFF, attach this asset catalog and set your own signing team.
No signed iOS artifact or App Store deployment is claimed. Device-local network
permission/privacy descriptions must match the enabled real transports.

Generic Bluetooth Classic SPP and serial/USB must not be assumed available.
BLE integration and background monitoring are not implemented. Updates must use
App Store-supported version notifications/links, never binary self-modification.
