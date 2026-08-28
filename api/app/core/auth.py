"""Core security module - password hashing, token hashing, and JWT utilities."""

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
import jwt
from app.config import get_settings

settings = get_settings()

JWT_ISSUER = "aergia"
ACCESS_TOKEN_AUDIENCE = "aergia-api"
REFRESH_TOKEN_AUDIENCE = "aergia-refresh"
ACCESS_COOKIE_NAME = "aergia_access_token"
REFRESH_COOKIE_NAME = "aergia_refresh_token"
CSRF_COOKIE_NAME = "aergia_csrf"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (UnicodeEncodeError, ValueError, TypeError):
        # bcrypt rejects inputs longer than 72 bytes. Treat those as a normal
        # failed credential rather than allowing the exception to become 500.
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_token_hash(token: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_token(token), stored_hash)


def _create_token(email: str, token_type: str, audience: str, expires_delta: timedelta) -> str:
    expires = datetime.now(timezone.utc) + expires_delta
    to_encode = {
        "sub": email,
        "exp": expires,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid4()),
        "typ": token_type,
        "iss": JWT_ISSUER,
        "aud": audience,
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")


def create_access_token(email: str) -> str:
    return _create_token(
        email,
        "access",
        ACCESS_TOKEN_AUDIENCE,
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(email: str) -> str:
    return _create_token(
        email,
        "refresh",
        REFRESH_TOKEN_AUDIENCE,
        timedelta(days=settings.refresh_token_expire_days),
    )


def _verify_token(token: str, token_type: str, audience: str) -> str | None:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
            audience=audience,
            issuer=JWT_ISSUER,
        )
        if payload.get("typ") != token_type:
            return None
        subject = payload.get("sub")
        return subject if isinstance(subject, str) and subject else None
    except (jwt.PyJWTError, TypeError, ValueError):
        return None


def verify_access_token(token: str) -> str | None:
    return _verify_token(token, "access", ACCESS_TOKEN_AUDIENCE)


def verify_refresh_token(token: str) -> str | None:
    return _verify_token(token, "refresh", REFRESH_TOKEN_AUDIENCE)


def verify_token(token: str) -> str | None:
    """Backward-compatible access-token verifier for older callers."""
    return verify_access_token(token)
