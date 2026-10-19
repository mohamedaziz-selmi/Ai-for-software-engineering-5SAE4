"""E-mails to customers. The order-ready e-mail is new in M3; the order confirmation comes from M2 (mailer.py)."""

import json
import smtplib
from email.message import EmailMessage
from pathlib import Path

CONFIG = json.loads((Path(__file__).parent.parent / "config" / "notifications.json").read_text(encoding="utf-8"))


def send_ready_email(order: dict) -> None:
    template = CONFIG["templates"]["order_ready"]
    message = EmailMessage()
    message["From"] = CONFIG["sender"]
    message["To"] = order["customer_email"]
    message["Subject"] = template["subject"].format(number=order["number"])
    message.set_content(template["body"].format(number=order["number"], shop=order["shop_name"], slot=order["slot_start"]))
    with smtplib.SMTP(CONFIG["smtp_host"], CONFIG["smtp_port"]) as smtp:
        smtp.starttls()
        smtp.send_message(message)
