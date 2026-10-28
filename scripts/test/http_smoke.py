"""Exercise the compiled C++ backend over real loopback HTTP; isolated SQLite only."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request


def run(binary):
    checks = []
    with tempfile.TemporaryDirectory(prefix="cda-v3-http-") as tmp:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        database = str(Path(tmp) / "backend.sqlite")
        def start():
            p = subprocess.Popen([str(binary), "--database", database, "--port", str(port)], stdout=subprocess.DEVNULL)
            for _ in range(100):
                if p.poll() is not None:
                    raise RuntimeError("C++ backend exited during startup")
                try:
                    if request("/health")[0] == 200:
                        return p
                except OSError:
                    pass
                time.sleep(0.03)
            p.terminate()
            p.wait(timeout=5)
            raise RuntimeError("C++ backend startup timeout")
        def request(path, method="GET", data=None, token=None):
            headers = {"Content-Type": "application/json"}
            if token:
                headers["Authorization"] = "Bearer " + token
            req = urllib.request.Request(f"http://127.0.0.1:{port}/api/v1" + path, method=method, headers=headers,
                                         data=json.dumps(data).encode() if data is not None else None)
            try:
                response = urllib.request.urlopen(req, timeout=10)
            except urllib.error.HTTPError as e:
                response = e
            with response:
                raw = response.read()
                return response.status, json.loads(raw) if raw else None
        def verify(name, condition):
            if not condition:
                raise AssertionError(name)
            checks.append(name)
        process = start()
        try:
            verify("unauthenticated_vehicle_access_denied", request("/vehicles")[0] == 401)
            payload = {"email": "owner@example.org", "password": "a sufficiently long password", "role": "ADMIN"}
            status, account = request("/accounts", "POST", payload)
            verify("register", status == 201 and account["emailVerified"] is False)
            status, session = request("/sessions", "POST", payload)
            token = session["token"]
            verify("self_granted_admin_denied", status == 200 and session["roles"] == ["USER"])
            status, vehicle = request("/vehicles", "POST", {"make": "Mercedes-Benz", "model": "E350", "year": 2006}, token)
            verify("owned_vehicle", status == 201 and not vehicle["identityVerified"])
            other = {"email": "other@example.org", "password": "another long password"}
            request("/accounts", "POST", other)
            other_token = request("/sessions", "POST", other)[1]["token"]
            verify("cross_account_isolation", request("/vehicles", token=other_token)[1] == [])
            prefs = {"language": "fr", "units": "imperial", "theme": "light", "secret": "not_saved"}
            status, stored = request("/settings", "PUT", prefs, token)
            verify("settings_field_whitelist", status == 200 and stored == {k: prefs[k] for k in ("language", "units", "theme")})
            verify("invalid_locale_rejected", request("/settings", "PUT", dict(prefs, language="de"), token)[0] == 422)
            process.terminate()
            process.wait(timeout=5)
            process = start()
            verify("token_and_vehicle_survive_restart", request("/vehicles", token=token)[1][0]["id"] == vehicle["id"])
            verify("preferences_survive_restart", request("/settings", token=token)[1]["language"] == "fr")
            verify("logout", request("/sessions/current", "DELETE", token=token)[0] == 204)
            verify("revoked_token_denied", request("/me", token=token)[0] == 401)
            caps = request("/capabilities")[1]
            verify("no_fake_hardware_or_payment_claims", caps["ecuWrites"] == "LOCKED" and caps["payments"] == "NOT_IMPLEMENTED" and not caps["physicalHardwareValidated"])
        finally:
            process.terminate()
            process.wait(timeout=5)
    print(json.dumps({"status": "PASS", "checks": checks}, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--binary", type=Path, default=Path("build/dev/cda_backend"))
    run(p.parse_args().binary.resolve())
