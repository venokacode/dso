import hashlib
from datetime import datetime, timedelta, timezone
from hmac import compare_digest
from secrets import token_hex, token_urlsafe


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(raw_password: str) -> str:
    salt = token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", raw_password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return f"{salt}${digest.hex()}"


def verify_password(raw_password: str, hashed_password: str) -> bool:
    parts = hashed_password.split("$", maxsplit=1)
    if len(parts) != 2:
        return False
    salt, saved_digest = parts
    candidate_digest = hashlib.pbkdf2_hmac(
        "sha256",
        raw_password.encode("utf-8"),
        salt.encode("utf-8"),
        120000,
    ).hex()
    return compare_digest(saved_digest, candidate_digest)


def generate_access_token() -> str:
    return token_urlsafe(32)


def token_expiry(hours: int = 24) -> datetime:
    return utc_now() + timedelta(hours=hours)
