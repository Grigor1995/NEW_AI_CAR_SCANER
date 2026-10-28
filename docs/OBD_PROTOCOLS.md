# OBD protocol support

New C++ ELM adapter setup delegates physical bus negotiation to the actual compatible adapter (ATSP0); no universal vehicle support is claimed. Implemented parser accepts headerless generic replies, spaced/compact 11-bit and spaced/compact 29-bit classic CAN headers, single-frame and bounded per-ECU ISO-TP responses with sequence validation. Parser rejects adapter errors, invalid hex, overlong frames, incomplete segments and wrong service/PID measurements.

Qt Network TCP numeric-IP and desktop Qt SerialPort I/O are real source implementations, tested against loopback only. CAN/ISO/KWP/J1850 hardware negotiation remains adapter-dependent and unverified. Native raw CAN hardware, BLE/Classic Bluetooth, USB-host mobile drivers, DoIP, UDS DID/routine execution, OEM protocols and flashing are NOT IMPLEMENTED. These are architecture targets, not automatic capabilities of an ELM adapter.
