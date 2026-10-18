"""Email sending through the shop's SMTP relay (synthetic demo deliverable)."""

import smtplib
from email.message import EmailMessage

SMTP_HOST = "smtp.atelier.example"
SMTP_PASSWORD = "Sm7p-Dem0-Passw0rd-2026"


def send_email(to: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = "orders@atelier.example"
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(SMTP_HOST, 587) as smtp:
        smtp.starttls()
        smtp.login("orders@atelier.example", SMTP_PASSWORD)
        smtp.send_message(message)
