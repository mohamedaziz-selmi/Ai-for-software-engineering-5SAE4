# Live review check: v3-v1-run1

Deliverable `demo/deliverables/M2_v1_with_defects`, scored against `eval/datasets/review_demo_gold.json`. Real run through the HTTP API; review served by `hosted` model `openai/gpt-oss-120b`. Verdicts are after code-side evidence verification.

- Verdict accuracy: **12/13**
- Planted defects detected with verified evidence (blocker/major): **2/2**
- Findings kept: 8; dropped unverified: {}
- Wall time: 219.8 s for 13 requirements; model `openai/gpt-oss-120b`

| Requirement | Gold | Model said | Final verdict | OK | Note |
|---|---|---|---|---|---|
| NN-1 | violates/partial | violates | violates | yes |  |
| NN-2 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| NN-3 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| NN-4 | violates/partial | violates | violates | yes |  |
| NN-5 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-001 | conforms/partial | conforms | conforms | yes |  |
| REQ-002 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-003 | conforms/partial | partial | partial | yes |  |
| REQ-004 | conforms/partial | cannot_determine | cannot_determine | no |  |
| REQ-005 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-006 | conforms | conforms | conforms | yes |  |
| REQ-007 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-008 | cannot_determine | cannot_determine | cannot_determine | yes |  |

## Findings

- **blocker** NN-1 `src/slots.py:5-8`: The code sets MAX_ORDERS_PER_SLOT to 25, exceeding the required maximum of 20 orders per slot.  
  evidence: `MAX_ORDERS_PER_SLOT = 25
BOOKING_CLOSES_BEFORE = timedelta(hours=1)`
- **blocker** NN-1 `src/slots.py:7-8`: Booking closes only 1 hour before the slot (timedelta(hours=1)) instead of the required 2 hours.  
  evidence: `BOOKING_CLOSES_BEFORE = timedelta(hours=1)`
- **blocker** NN-4 `src/accounts.py:9-11`: Password hashing uses SHA‑256 via hashlib, which does not meet the required Argon2id or bcrypt algorithm.  
  evidence: `def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()`
- **blocker** NN-4 `README.md:15-15`: Staff back‑office two‑factor authentication is only mentioned as planned for a future milestone, not implemented.  
  evidence: `- The staff back-office is planned for M3.`
- **major** REQ-003 `src/orders.py:7-10`: The code validates the slot via slot_is_open but does not show any validation or selection mechanism for the pickup shop; the requirement that a customer can choose a shop is not demonstrated.  
  evidence: `def place_order(db, customer, cart, shop_id, slot_start, now):
    orders_in_slot = db.count("orders", {"shop_id": shop_id, "slot_start": sl`
- **info** REQ-001 `src/accounts.py:13-21`: The module provides `create_account` that stores the email and a hashed password, and `start_password_reset` that generates a token, records it, and sends a reset email, fulfilling the required functionality.  
  evidence: `def create_account(db, email: str, password: str) -> int:
    user_id = db.insert("customers", {"email": email, "password_hash": hash_passwo`
- **info** REQ-003 `src/slots.py:5-14`: Slot duration is defined as 15 minutes and slot_is_open rejects slots that are full or past the booking cutoff, satisfying the 15‑minute slot and full/closed slot constraints.  
  evidence: `SLOT_MINUTES = 15
...
if orders_in_slot >= MAX_ORDERS_PER_SLOT:
    return False
return now <= slot_start - BOOKING_CLOSES_BEFORE`
- **info** REQ-006 `src/orders.py:18-22`: The cancel_order function checks that the time difference between the slot start and the current time is at least 3 hours; if it is less, it raises an error, thereby allowing cancellation only up to 3 hours before pickup as required.  
  evidence: `if (order.slot_start - now).total_seconds() < 3 * 3600:
    raise ValueError("Orders can be cancelled up to 3 hours before pickup.")
    db.`
