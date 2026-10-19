"""Customer accounts (synthetic demo deliverable, corrected version v2)."""

import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from .mailer import send_email

_hasher = PasswordHasher()  # NN-4: Argon2id (argon2-cffi default)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def create_account(db, email: str, password: str) -> int:
    user_id = db.insert("customers", {"email": email, "password_hash": hash_password(password)})
    return user_id


def start_password_reset(db, email: str) -> None:
    token = secrets.token_urlsafe(32)
    db.insert("password_resets", {"email": email, "token": token})
    send_email(email, "Reset your password", f"Use this link within 1 hour: https://atelier.example/reset/{token}")
