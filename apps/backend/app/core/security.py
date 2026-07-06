"""Security primitives: Telegram initData validation, JWTs, password hashing, tokens."""
import hashlib
import hmac
import json
import secrets
import time
import uuid
from urllib.parse import parse_qsl

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings

_ph = PasswordHasher()


class InitDataError(Exception):
    pass


def validate_init_data(init_data: str, bot_token: str, max_age: int | None = None) -> dict:
    """Validate Telegram Mini App initData (HMAC-SHA256 per official spec).

    Returns the parsed payload with `user` decoded to a dict.
    Raises InitDataError on any validation failure.
    """
    if not init_data:
        raise InitDataError("empty initData")
    try:
        pairs = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError as exc:
        raise InitDataError("malformed initData") from exc

    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise InitDataError("missing hash")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise InitDataError("hash mismatch")

    max_age = max_age if max_age is not None else get_settings().init_data_max_age
    try:
        auth_date = int(pairs.get("auth_date", "0"))
    except ValueError as exc:
        raise InitDataError("bad auth_date") from exc
    if auth_date <= 0 or time.time() - auth_date > max_age:
        raise InitDataError("initData expired")

    if "user" in pairs:
        try:
            pairs["user"] = json.loads(pairs["user"])
        except json.JSONDecodeError as exc:
            raise InitDataError("bad user payload") from exc
    return pairs


# ── JWT ─────────────────────────────────────────────────────────────────────

def create_token(subject: str, token_type: str, ttl: int, extra: dict | None = None) -> str:
    now = int(time.time())
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + ttl,
        "jti": uuid.uuid4().hex,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, get_settings().jwt_secret, algorithm="HS256")


def decode_token(token: str, expected_type: str) -> dict:
    payload = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("wrong token type")
    return payload


# ── Passwords ───────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


# ── Opaque tokens (subscription URL) ────────────────────────────────────────

def generate_subscription_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
