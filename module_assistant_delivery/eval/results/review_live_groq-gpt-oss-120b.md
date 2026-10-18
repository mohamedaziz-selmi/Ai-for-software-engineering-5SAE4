# Live review check: groq-gpt-oss-120b

Synthetic M2 deliverable with planted defects (see `eval/datasets/review_demo_gold.json`). Real run through the HTTP API; review served by `hosted` model `openai/gpt-oss-120b`. Verdicts are after code-side evidence verification.

- Verdict accuracy: **13/13**
- Planted defects detected with verified evidence (blocker/major): **2/2**
- Findings kept: 10; dropped unverified: {}
- Wall time: 120.9 s for 13 requirements; model `openai/gpt-oss-120b`

| Requirement | Gold | Model said | Final verdict | OK | Note |
|---|---|---|---|---|---|
| NN-1 | violates/partial | violates | violates | yes |  |
| NN-2 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| NN-3 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| NN-4 | violates/partial | violates | violates | yes |  |
| NN-5 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-001 | conforms/partial | conforms | conforms | yes |  |
| REQ-002 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-003 | conforms/partial | conforms | conforms | yes |  |
| REQ-004 | conforms/partial | conforms | conforms | yes |  |
| REQ-005 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-006 | conforms | conforms | conforms | yes |  |
| REQ-007 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-008 | cannot_determine | cannot_determine | cannot_determine | yes |  |

## Findings

- **blocker** NN-1 `src/slots.py:5-7`: Maximum orders per slot is set to 25, but the requirement mandates at most 20 orders.  
  evidence: `SLOT_MINUTES = 15
MAX_ORDERS_PER_SLOT = 25
BOOKING_CLOSES_BEFORE = timedelta(hours=1)`
- **blocker** NN-1 `src/slots.py:7-8`: Booking closes 1 hour before the slot, whereas the requirement requires closing 2 hours before.  
  evidence: `BOOKING_CLOSES_BEFORE = timedelta(hours=1)`
- **blocker** NN-4 `src/accounts.py:9-11`: Password hashing uses SHA‑256 instead of Argon2id or bcrypt, violating the mandatory hashing algorithm requirement.  
  evidence: `def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()`
- **major** NN-4 `README.md:15-15`: No evidence that staff back‑office accounts have two‑factor authentication enabled; the requirement is a MUST.  
  evidence: `- The staff back-office is planned for M3.`
- **info** REQ-001 `src/accounts.py:13-15`: create_account stores email and a hashed password, fulfilling account creation with email and password.  
  evidence: `def create_account(db, email: str, password: str) -> int:
    user_id = db.insert("customers", {"email": email, "password_hash": hash_passwo`
- **info** REQ-001 `src/accounts.py:18-21`: start_password_reset generates a token, stores it, and sends a reset email, satisfying password reset via email.  
  evidence: `def start_password_reset(db, email: str) -> None:
    token = secrets.token_urlsafe(32)
    db.insert("password_resets", {"email": email, "t`
- **info** REQ-003 `src/slots.py:5-6`: Slot duration is defined as 15 minutes, satisfying the 15‑minute slot requirement.  
  evidence: `SLOT_MINUTES = 15
MAX_ORDERS_PER_SLOT = 25`
- **info** REQ-003 `src/orders.py:9-10`: Order placement checks slot availability via `slot_is_open` and raises an error when the slot is full or closed, preventing selection of such slots.  
  evidence: `    if not slot_is_open(slot_start, now, orders_in_slot):
        raise ValueError("This pickup slot is full or closed.")`
- **info** REQ-004 `src/orders.py:12-14`: The order placement function calls send_email synchronously right after inserting the order, providing immediate confirmation.  
  evidence: `    # REQ-004: confirmation email with order number, shop and slot, sent synchronously right after insert.
    send_email(customer.email, f"`
- **info** REQ-006 `src/orders.py:18-22`: The cancel_order function checks that the time difference between the slot start and the current time is at least 3 hours before allowing cancellation, matching the requirement.  
  evidence: `if (order.slot_start - now).total_seconds() < 3 * 3600:
    raise ValueError("Orders can be cancelled up to 3 hours before pickup.")`
