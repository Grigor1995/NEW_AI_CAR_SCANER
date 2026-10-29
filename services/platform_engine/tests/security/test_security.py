from backend.security.auth import Principal, issue_token, verify_token, TokenError
from backend.security.rbac import allowed
from backend.security.rate_limit import SlidingWindowRateLimiter

def test_token_roundtrip():
    p=Principal("u1","org1",("technician",))
    t=issue_token(p,"secret",ttl_seconds=60)
    assert verify_token(t,"secret").subject == "u1"

def test_tampered_token_rejected():
    p=Principal("u1","org1",("viewer",)); t=issue_token(p,"secret")
    try: verify_token(t+"x","secret")
    except TokenError: pass
    else: assert False

def test_rbac():
    assert allowed(("technician",), "session:write")
    assert not allowed(("viewer",), "session:write")

def test_rate_limit():
    r=SlidingWindowRateLimiter(2,10)
    assert r.allow("a",0); assert r.allow("a",1); assert not r.allow("a",2); assert r.allow("a",11)
