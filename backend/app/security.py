import hmac
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.config import settings
from app.db import get_db
from app.models import User

hasher = PasswordHasher()
_attempts = defaultdict(deque)


def rate_limit(key, limit=20, period=60):
    q = _attempts[key]
    current = time.monotonic()
    while q and q[0] < current - period:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(
            429,
            "Too many requests. Try again shortly.",
            headers={"Retry-After": str(period)},
        )
    q.append(current)
    if len(_attempts) > 10000:
        for k in list(_attempts)[:5000]:
            if not _attempts[k] or _attempts[k][-1] < current - period:
                _attempts.pop(k, None)


def password_ok(raw, encoded):
    try:
        return hasher.verify(encoded, raw)
    except VerificationError:
        return False


def make_token(user):
    csrf = secrets.token_urlsafe(24)
    token = jwt.encode(
        {
            "sub": user.id,
            "csrf": csrf,
            "exp": datetime.now(timezone.utc) + timedelta(hours=8),
            "iat": datetime.now(timezone.utc),
            "iss": "devsphere",
            "aud": "devsphere-browser",
        },
        settings().jwt_secret,
        algorithm="HS256",
    )
    return token, csrf


def check_origin(request):
    origin = request.headers.get("origin")
    allowed = {
        settings().app_origin,
        "http://localhost:8010",
        "http://127.0.0.1:8010",
        "http://localhost:5174",
    }
    if origin and origin not in allowed:
        raise HTTPException(403, "Origin not allowed")


def current_user(request: Request, db: Session = Depends(get_db)):
    auth = request.headers.get("authorization", "")
    bearer = auth.startswith("Bearer ")
    token = auth[7:] if bearer else request.cookies.get("devsphere_session")
    try:
        data = jwt.decode(
            token or "",
            settings().jwt_secret,
            algorithms=["HS256"],
            audience="devsphere-browser",
            issuer="devsphere",
        )
    except jwt.PyJWTError:
        raise HTTPException(401, "Sign in to continue")
    if not bearer and request.method not in {"GET", "HEAD", "OPTIONS"}:
        check_origin(request)
        if not hmac.compare_digest(
            request.headers.get("x-csrf-token", ""), data.get("csrf", "invalid")
        ):
            raise HTTPException(
                403, "Refresh the page and try again (CSRF check failed)"
            )
    user = db.get(User, data["sub"])
    if not user:
        raise HTTPException(401, "Account no longer exists")
    request.state.csrf = data["csrf"]
    return user
