# Live review check: groq-gpt-oss-120b

Synthetic M2 deliverable with planted defects (see `eval/datasets/review_demo_gold.json`). Real run through the HTTP API; review served by `hosted` model `openai/gpt-oss-120b` (first run, before the line-by-line evidence check). Verdicts are after code-side evidence verification.

- Verdict accuracy: **12/13**
- Planted defects detected with verified evidence (blocker/major): **2/2**
- Findings kept: 7; dropped unverified: {'quote_not_at_location': 3}
- Wall time: 132.9 s for 13 requirements; model `openai/gpt-oss-120b`

| Requirement | Gold | Model said | Final verdict | OK | Note |
|---|---|---|---|---|---|
| NN-1 | violates/partial | violates | violates | yes |  |
| NN-2 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| NN-3 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| NN-4 | violates/partial | violates | violates | yes |  |
| NN-5 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-001 | conforms/partial | conforms | conforms | yes |  |
| REQ-002 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-003 | conforms/partial | conforms | cannot_determine | no | model said conforms but no evidence could be verified |
| REQ-004 | conforms/partial | conforms | conforms | yes |  |
| REQ-005 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-006 | conforms | conforms | conforms | yes |  |
| REQ-007 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-008 | cannot_determine | cannot_determine | cannot_determine | yes |  |

## Findings

- **blocker** NN-1 `src/slots.py:5-8`: The maximum orders per slot is set to 25, exceeding the required limit of 20.  
  evidence: `SLOT_MINUTES = 15
MAX_ORDERS_PER_SLOT = 25
BOOKING_CLOSES_BEFORE = timedelta(hours=1)`
- **blocker** NN-1 `src/slots.py:7-8`: Booking closes 1 hour before the slot, but the requirement mandates closing 2 hours before.  
  evidence: `BOOKING_CLOSES_BEFORE = timedelta(hours=1)`
- **blocker** NN-4 `src/accounts.py:9-11`: Password hashing uses SHA‑256 instead of Argon2id or bcrypt, violating the required secure hash algorithm.  
  evidence: `def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()`
- **blocker** NN-4 `README.md:15-15`: No evidence that staff back‑office accounts have two‑factor authentication enabled; the README only mentions planning for staff back‑office.  
  evidence: `- The staff back-office is planned for M3.`
- **info** REQ-001 `src/accounts.py:13-21`: The module provides `create_account` to store email and hashed password, and `start_password_reset` that generates a token and emails a reset link.  
  evidence: `def create_account(db, email: str, password: str) -> int:
    user_id = db.insert("customers", {"email": email, "password_hash": hash_passwo`
- **info** REQ-004 `src/orders.py:12-14`: The order placement function calls send_email synchronously right after inserting the order, providing the order number, shop and slot details.  
  evidence: `    # REQ-004: confirmation email with order number, shop and slot, sent synchronously right after insert.
    send_email(customer.email, f"`
- **info** REQ-006 `src/orders.py:18-21`: Cancellation logic enforces that orders can only be cancelled when the remaining time before the pickup slot is at least 3 hours.  
  evidence: `def cancel_order(db, order, now):
    """REQ-006: cancellation is allowed up to 3 hours before the pickup slot."""
    if (order.slot_start `
