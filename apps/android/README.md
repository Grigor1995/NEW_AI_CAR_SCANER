# Android source integration — BUILD NOT RUN

The client source is apps/shared plus ui, built against a Qt 6.8+ Android kit.
The Android manifest and canonical adaptive/raster icons are provided here.
Use qt-cmake from that kit with a matching Android SDK/NDK, an Android OpenSSL
build and CDA_BUILD_BACKEND=OFF. Configure signing and APK/AAB deployment with
Qt's supported Android deployment tooling. No CI or store upload is configured.

TCP connections use Qt Network. BLE/Classic Bluetooth and USB-host driver/permission
integration are NOT IMPLEMENTED; do not infer Android serial support from desktop
QSerialPort. Background monitoring is not implemented. Permission requests and
operating-system lifecycle/hardware validation are release gates.
