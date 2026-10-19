# Live review check: v3-v1-run2

Deliverable `demo/deliverables/M2_v1_with_defects`, scored against `eval/datasets/review_demo_gold.json`. Real run through the HTTP API; review served by `hosted` model `openai/gpt-oss-120b`. Verdicts are after code-side evidence verification.

- Verdict accuracy: **13/13**
- Planted defects detected with verified evidence (blocker/major): **2/2**
- Findings kept: 9; dropped unverified: {}
- Wall time: 151.8 s for 13 requirements; model `openai/gpt-oss-120b`

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
| REQ-004 | conforms/partial | conforms | conforms | yes |  |
| REQ-005 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-006 | conforms | conforms | conforms | yes |  |
| REQ-007 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-008 | cannot_determine | cannot_determine | cannot_determine | yes |  |

## Findings

- **blocker** NN-1 `src/slots.py:5-8`: The code allows up to 25 orders per slot (MAX_ORDERS_PER_SLOT = 25) instead of the required maximum of 20.  
  evidence: `MAX_ORDERS_PER_SLOT = 25`
- **blocker** NN-1 `src/slots.py:7-8`: Booking closes only 1 hour before the slot (BOOKING_CLOSES_BEFORE = timedelta(hours=1)) but the requirement mandates closing 2 hours before.  
  evidence: `BOOKING_CLOSES_BEFORE = timedelta(hours=1)`
- **blocker** NN-4 `src/accounts.py:9-11`: Password hashing uses SHA‑256 instead of Argon2id or bcrypt, violating the required secure hash algorithm.  
  evidence: `def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()`
- **blocker** NN-4 `README.md:15-15`: Staff back‑office two‑factor authentication is only mentioned as planned for a future milestone, not implemented.  
  evidence: `- The staff back-office is planned for M3.`
- **major** REQ-003 `src/orders.py:7-10`: The code validates the slot via `slot_is_open` but does not show any validation that the chosen shop exists or is selectable, so the requirement that a customer can choose a pickup shop is not demonstrated.  
  evidence: `def place_order(db, customer, cart, shop_id, slot_start, now):
    orders_in_slot = db.count("orders", {"shop_id": shop_id, "slot_start": sl`
- **info** REQ-001 `src/accounts.py:13-21`: The `create_account` function stores the provided email and a hashed password, and `start_password_reset` generates a reset token, records it, and sends a reset email, fulfilling the account creation and password‑reset requirements.  
  evidence: `def create_account(db, email: str, password: str) -> int:
    user_id = db.insert("customers", {"email": email, "password_hash": hash_passwo`
- **info** REQ-003 `src/slots.py:5-14`: Slot duration is defined as 15 minutes and `slot_is_open` rejects slots that are full or past the booking cutoff, satisfying the 15‑minute slot and full/closed slot constraints.  
  evidence: `SLOT_MINUTES = 15
...
if orders_in_slot >= MAX_ORDERS_PER_SLOT:
    return False
return now <= slot_start - BOOKING_CLOSES_BEFORE`
- **info** REQ-004 `src/orders.py:12-14`: The order placement function calls send_email synchronously right after inserting the order, providing an immediate confirmation email with order number, shop and slot.  
  evidence: `send_email(customer.email, f"Order {order_id} confirmed",
               f"Order {order_id}: pickup at shop {shop_id}, slot {slot_start:%Y-%`
- **info** REQ-006 `src/orders.py:18-22`: The cancel_order function checks that the time difference between the slot start and the current time is at least 3 hours; if less, it raises an error, thereby allowing cancellation only up to 3 hours before pickup as required.  
  evidence: `def cancel_order(db, order, now):
    """REQ-006: cancellation is allowed up to 3 hours before the pickup slot."""
    if (order.slot_start `
