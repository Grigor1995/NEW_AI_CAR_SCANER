from __future__ import annotations

import math

from vehicle.obd.transport import DiagnosticTransport


class SimulatorTransport(DiagnosticTransport):
    def __init__(self, responses=None, *, dynamic: bool = False):
        self.responses = responses or {}
        self.dynamic = dynamic
        self._connected = False
        self._tick = 0
        self.last_command = ""

    @property
    def connected(self):
        return self._connected

    async def connect(self):
        self._connected = True

    async def disconnect(self):
        self._connected = False

    async def write(self, data):
        self.last_command = data.decode().strip().upper()

    def _dynamic_response(self, cmd: str) -> str | None:
        if not self.dynamic:
            return None
        if cmd == "0100":
            return "41 00 08 18 80 00"  # Four implemented synthetic live channels.
        # Deterministic, repeatable live-data waveform for development/demo use.
        self._tick += 1
        phase = self._tick * 0.18
        if cmd == "010C":  # RPM: normal variation with periodic load dip.
            rpm = 1450 + int(350 * math.sin(phase))
            if self._tick % 45 in (0, 1, 2):
                rpm -= 500
            a = max(0, min(255, int((rpm * 4) // 256)))
            b = max(0, min(255, int((rpm * 4) % 256)))
            return f"41 0C {a:02X} {b:02X}"
        if cmd == "0105":  # Coolant temperature.
            value = int(round(88 + 1.5 * math.sin(phase / 3)))
            return f"41 05 {max(0, min(255, value + 40)):02X}"
        if cmd == "010D":  # Vehicle speed.
            speed = int(round(32 + 7 * math.sin(phase / 2)))
            return f"41 0D {max(0, min(255, speed)):02X}"
        if cmd == "0111":  # Throttle position.
            throttle = int(round(28 + 18 * (0.5 + 0.5 * math.sin(phase / 1.5))))
            return f"41 11 {max(0, min(255, throttle * 255 // 100)):02X}"
        return None

    async def read_until(self, terminator=b">", timeout=2.0):
        response = self._dynamic_response(self.last_command)
        if response is None:
            response = self.responses.get(self.last_command, "NO DATA")
        return (response + ">").encode()
