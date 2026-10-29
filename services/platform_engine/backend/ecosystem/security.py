"""Password hashing and opaque tokens; no trust in caller-supplied role claims."""
import base64
import hashlib
import hmac
import secrets


def password_hash(value):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(value.encode('utf-8'), salt=salt, n=32768, r=8, p=3, dklen=32, maxmem=64*1024**2)
    return 'scrypt$32768$8$3$' + base64.b64encode(salt).decode() + '$' + base64.b64encode(digest).decode()


def password_matches(value, encoded):
    try:
        kind, n, r, p, salt, expected = encoded.split('$')
        if (kind, n, r, p) != ('scrypt', '32768', '8', '3'): return False
        salt, expected = base64.b64decode(salt, validate=True), base64.b64decode(expected, validate=True)
        if len(salt) != 16 or len(expected) != 32: return False
        digest = hashlib.scrypt(value.encode('utf-8'), salt=salt, n=32768, r=8, p=3, dklen=32, maxmem=64*1024**2)
        return hmac.compare_digest(digest, expected)
    except (ValueError, TypeError):
        return False


def token_digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def new_token():
    value = secrets.token_urlsafe(32)
    return value, token_digest(value)
