# Technology stack

C++20; Qt 6.8 Core, Quick/QML, QuickControls2, Network, Sql/SQLite, SerialPort (desktop), Concurrent, Test, Svg, HttpServer/WebSockets, LinguistTools; CMake >=3.24 with Ninja; OpenSSL >=3 for random generation, scrypt, hashing and Ed25519 verification. Python scripts are development/QA/asset tools only, not application runtime code. PostgreSQL/Drogon/GoogleTest were recommendations; PostgreSQL deployment is planned, and tests currently use a small C++ contract harness plus Qt Test.

This cloud machine uses Debian 13, GCC 14.2 and Qt 6.8.2 development packages verified through signed Debian package indexes and extracted under /workspace/toolchains without root. CMake 4.4.4 is a tool-only environment dependency. Platform SDKs, OpenSSL and Qt kits must match compiler and architecture; no single executable serves all platforms.
