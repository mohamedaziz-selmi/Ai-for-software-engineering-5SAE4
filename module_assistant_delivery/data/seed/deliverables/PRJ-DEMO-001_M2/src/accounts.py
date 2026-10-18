"""Customer accounts (synthetic demo deliverable with planted defects)."""

import hashlib
import secrets

from .mailer import send_email


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_account(db, email: str, password: str) -> int:
    user_id = db.insert("customers", {"email": email, "password_hash": hash_password(password)})
    return user_id


def start_password_reset(db, email: str) -> None:
    token = secrets.token_urlsafe(32)
    db.insert("password_resets", {"email": email, "token": token})
    send_email(email, "Reset your password", f"Use this link within 1 hour: https://atelier.example/reset/{token}")
