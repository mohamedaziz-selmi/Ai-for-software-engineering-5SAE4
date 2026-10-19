# Live review check: stab-v1-run2

Deliverable `demo/deliverables/M2_v1_with_defects`, scored against `eval/datasets/review_demo_gold.json`. Real run through the HTTP API; review served by `hosted` model `openai/gpt-oss-120b`. Verdicts are after code-side evidence verification.

- Verdict accuracy: **12/13**
- Planted defects detected with verified evidence (blocker/major): **2/2**
- Findings kept: 6; dropped unverified: {}
- Wall time: 139.3 s for 13 requirements; model `openai/gpt-oss-120b`

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
| REQ-004 | conforms/partial | cannot_determine | cannot_determine | no |  |
| REQ-005 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-006 | conforms | conforms | conforms | yes |  |
| REQ-007 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-008 | cannot_determine | cannot_determine | cannot_determine | yes |  |

## Findings

- **blocker** NN-1 `src/slots.py:5-8`: The constant MAX_ORDERS_PER_SLOT is set to 25, exceeding the required maximum of 20 orders per slot.  
  evidence: `MAX_ORDERS_PER_SLOT = 25`
- **blocker** NN-1 `src/slots.py:7-8`: Booking closes 1 hour before the slot (timedelta(hours=1)) instead of the required 2 hours.  
  evidence: `BOOKING_CLOSES_BEFORE = timedelta(hours=1)`
- **blocker** NN-4 `src/accounts.py:9-11`: The password hashing function uses SHA‑256 instead of Argon2id or bcrypt, violating the mandatory security requirement.  
  evidence: `def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()`
- **info** REQ-001 `src/accounts.py:13-21`: The module provides `create_account` that stores email and a hashed password, and `start_password_reset` that generates a token, stores it, and sends a reset email, fulfilling the required functionality.  
  evidence: `def create_account(db, email: str, password: str) -> int:
    user_id = db.insert("customers", {"email": email, "password_hash": hash_passwo`
- **info** REQ-003 `src/slots.py:5-14`: Slot duration is set to 15 minutes and slot_is_open prevents selection of full or closed slots.  
  evidence: `SLOT_MINUTES = 15
...
if orders_in_slot >= MAX_ORDERS_PER_SLOT:
    return False
return now <= slot_start - BOOKING_CLOSES_BEFORE`
- **info** REQ-006 `src/orders.py:18-22`: The cancel_order function checks that the cancellation request is made at least 3 hours before the slot start and raises an error otherwise, fulfilling the SHOULD requirement.  
  evidence: `def cancel_order(db, order, now):
    """REQ-006: cancellation is allowed up to 3 hours before the pickup slot."""
    if (order.slot_start `
