# Live review check: demo-m2-v2-fixed

Deliverable `demo/deliverables/M2_v2_fixed`, scored against `eval/datasets/review_demo_v2_gold.json`. Real run through the HTTP API; review served by `hosted` model `openai/gpt-oss-120b`. Verdicts are after code-side evidence verification.

- Verdict accuracy: **11/13**
- Planted defects detected with verified evidence (blocker/major): **0/0**
- Findings kept: 8; dropped unverified: {}
- Wall time: 175.5 s for 13 requirements; model `openai/gpt-oss-120b`

| Requirement | Gold | Model said | Final verdict | OK | Note |
|---|---|---|---|---|---|
| NN-1 | conforms | conforms | conforms | yes |  |
| NN-2 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| NN-3 | cannot_determine | partial | partial | no |  |
| NN-4 | conforms/partial/cannot_determine | partial | partial | yes |  |
| NN-5 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-001 | conforms/partial | conforms | conforms | yes |  |
| REQ-002 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-003 | conforms/partial | conforms | conforms | yes |  |
| REQ-004 | conforms/partial | cannot_determine | cannot_determine | no |  |
| REQ-005 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-006 | conforms | conforms | conforms | yes |  |
| REQ-007 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-008 | cannot_determine | cannot_determine | cannot_determine | yes |  |

## Findings

- **major** NN-4 `README.md:19-19`: Two-factor authentication for staff back‑office accounts is only mentioned as planned, not implemented.  
  evidence: `- The staff back-office, including two-factor authentication for staff accounts, is planned for M3.`
- **info** NN-1 `src/slots.py:5-14`: The module defines MAX_ORDERS_PER_SLOT as 20 and BOOKING_CLOSES_BEFORE as a 2‑hour timedelta, and slot_is_open enforces both limits, satisfying the requirement.  
  evidence: `SLOT_MINUTES = 15
MAX_ORDERS_PER_SLOT = 20  # NN-1: at most 20 orders per 15-minute slot
BOOKING_CLOSES_BEFORE = timedelta(hours=2)  # NN-1:`
- **info** NN-3 `src/mailer.py:10-19`: Email notifications are sent via the project's own SMTP relay; there is no code that forwards customer personal data to external analytics services.  
  evidence: `def send_email(to: str, subject: str, body: str) -> None:
    ...
    with smtplib.SMTP(SMTP_HOST, 587) as smtp:
        smtp.starttls()
   `
- **info** NN-4 `src/accounts.py:5-10`: Password hashing uses Argon2id via the default PasswordHasher from argon2-cffi.  
  evidence: `from argon2 import PasswordHasher
_hasher = PasswordHasher()  # NN-4: Argon2id (argon2-cffi default)`
- **info** REQ-001 `src/accounts.py:24-32`: The module provides `create_account` to store email and hashed password, and `start_password_reset` to generate a reset token and email it to the user, fulfilling the account creation and password reset requirements.  
  evidence: `def create_account(db, email: str, password: str) -> int:
    user_id = db.insert("customers", {"email": email, "password_hash": hash_passwo`
- **info** REQ-003 `src/slots.py:10-14`: slot_is_open returns False when the slot is full or when booking has closed, enforcing the rule that full or closed slots cannot be selected.  
  evidence: `def slot_is_open(slot_start: datetime, now: datetime, orders_in_slot: int) -> bool:
    """A slot can be chosen while it has capacity and bo`
- **info** REQ-003 `src/orders.py:7-10`: place_order checks slot_is_open and raises an error if the slot is full or closed, preventing selection of invalid slots.  
  evidence: `def place_order(db, customer, cart, shop_id, slot_start, now):
    orders_in_slot = db.count("orders", {"shop_id": shop_id, "slot_start": sl`
- **info** REQ-006 `src/orders.py:18-21`: The cancel_order function checks that the time difference between the slot start and the current time is at least 3 hours before allowing cancellation, satisfying the requirement.  
  evidence: `def cancel_order(db, order, now):
    """REQ-006: cancellation is allowed up to 3 hours before the pickup slot."""
    if (order.slot_start `
