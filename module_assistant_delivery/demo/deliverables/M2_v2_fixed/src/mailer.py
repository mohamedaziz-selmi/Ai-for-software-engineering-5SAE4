"""Email sending through the shop's SMTP relay (synthetic demo deliverable, corrected version v2)."""

import os
import smtplib
from email.message import EmailMessage

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.atelier.example")


def send_email(to: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = "orders@atelier.example"
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(SMTP_HOST, 587) as smtp:
        smtp.starttls()
        smtp.login("orders@atelier.example", os.environ["SMTP_PASSWORD"])  # secret from the environment
        smtp.send_message(message)
