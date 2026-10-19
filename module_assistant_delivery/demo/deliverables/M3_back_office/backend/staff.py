"""Staff back-office API: the day's orders, mark as ready, CSV export. Staff sign-in needs a password and a TOTP code."""

import csv
import io

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from .db import db
from .notifications import send_ready_email

hasher = PasswordHasher()  # Argon2id by default


def staff_sign_in(email: str, password: str, totp_code: str) -> bool:
    account = db.fetch_one("SELECT * FROM staff_accounts WHERE email = %s", (email,))
    if account is None:
        return False
    try:
        hasher.verify(account["password_hash"], password)
    except VerificationError:
        return False
    # Two-factor authentication is mandatory for every staff account (totp_secret is NOT NULL).
    return pyotp.TOTP(account["totp_secret"]).verify(totp_code, valid_window=1)


def daily_orders(shop_id: int, day: str) -> list[dict]:
    return db.fetch_all(
        "SELECT id, number, customer_name, customer_email, slot_start, status, created_at FROM orders"
        " WHERE shop_id = %s AND slot_start::date = %s", (shop_id, day))


def mark_ready(order_id: int) -> None:
    order = db.fetch_one("UPDATE orders SET status = 'ready' WHERE id = %s RETURNING *", (order_id,))
    send_ready_email(order)


def export_csv(shop_id: int, day: str) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["number", "customer", "slot", "status"])
    for order in sorted(daily_orders(shop_id, day), key=lambda o: o["slot_start"]):
        writer.writerow([order["number"], order["customer_name"], order["slot_start"], order["status"]])
    return out.getvalue()
