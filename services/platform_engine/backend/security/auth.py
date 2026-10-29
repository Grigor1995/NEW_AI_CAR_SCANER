from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import base64, hashlib, hmac, json

@dataclass(frozen=True)
class Principal:
    subject: str
    organization_id: str
    roles: tuple[str, ...]

class TokenError(ValueError): pass

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

def issue_token(principal: Principal, secret: str, ttl_seconds: int = 3600) -> str:
    header = _b64(json.dumps({"alg":"HS256","typ":"JWT"}, separators=(",",":"), sort_keys=True).encode())
    now = datetime.now(timezone.utc)
    payload = _b64(json.dumps({"sub":principal.subject,"org":principal.organization_id,"roles":list(principal.roles),"iat":int(now.timestamp()),"exp":int((now+timedelta(seconds=ttl_seconds)).timestamp())}, separators=(",",":"), sort_keys=True).encode())
    signing = f"{header}.{payload}".encode()
    sig = _b64(hmac.new(secret.encode(), signing, hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"

def verify_token(token: str, secret: str, now: int | None = None) -> Principal:
    try: header, payload, signature = token.split(".")
    except ValueError as exc: raise TokenError("invalid token") from exc
    expected = _b64(hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected): raise TokenError("invalid signature")
    body = json.loads(_unb64(payload))
    current = int(datetime.now(timezone.utc).timestamp()) if now is None else now
    if current >= int(body["exp"]): raise TokenError("expired token")
    return Principal(str(body["sub"]), str(body["org"]), tuple(body.get("roles", [])))
