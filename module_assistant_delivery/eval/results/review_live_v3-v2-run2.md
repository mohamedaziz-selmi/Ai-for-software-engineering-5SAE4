# Live review check: v3-v2-run2

Deliverable `demo/deliverables/M2_v2_fixed`, scored against `eval/datasets/review_demo_v2_gold.json`. Real run through the HTTP API; review served by `hosted` model `openai/gpt-oss-120b`. Verdicts are after code-side evidence verification.

- Verdict accuracy: **8/13**
- Planted defects detected with verified evidence (blocker/major): **0/0**
- Findings kept: 5; dropped unverified: {'quote_not_at_location': 1}
- Wall time: 124.4 s for 13 requirements; model `openai/gpt-oss-120b`

| Requirement | Gold | Model said | Final verdict | OK | Note |
|---|---|---|---|---|---|
| NN-1 | conforms | conforms | conforms | yes |  |
| NN-2 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| NN-3 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| NN-4 | conforms/partial/cannot_determine | violates | violates | no |  |
| NN-5 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-001 | conforms/partial | conforms | conforms | yes |  |
| REQ-002 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-003 | conforms/partial | partial | cannot_determine | no | model said partial but no evidence could be verified |
| REQ-004 | conforms/partial | conforms | conforms | yes |  |
| REQ-005 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-006 | conforms | None | review_failed | no | [{"served_by": "hosted", "model": "openai/gpt-oss-120b", "error": "rate_limited"}] |
| REQ-007 | cannot_determine | None | review_failed | no | [{"served_by": "hosted", "model": "openai/gpt-oss-120b", "error": "rate_limited"}] |
| REQ-008 | cannot_determine | None | review_failed | no | [{"served_by": "hosted", "model": "openai/gpt-oss-120b", "error": "rate_limited"}] |

## Findings

- **blocker** NN-4 `README.md:19-19`: Two-factor authentication for staff back‑office accounts is only described as planned for a future milestone (M3), not implemented, violating the MUST requirement.  
  evidence: `- The staff back-office, including two-factor authentication for staff accounts, is planned for M3.`
- **info** NN-1 `src/slots.py:5-14`: Constants define MAX_ORDERS_PER_SLOT = 20 and BOOKING_CLOSES_BEFORE = 2 hours; slot_is_open returns False when orders reach the limit or when now is after slot_start minus 2 hours, satisfying the requirement.  
  evidence: `MAX_ORDERS_PER_SLOT = 20  # NN-1: at most 20 orders per 15-minute slot
BOOKING_CLOSES_BEFORE = timedelta(hours=2)  # NN-1: booking closes 2 `
- **info** NN-4 `src/accounts.py:10-14`: Password hashing uses Argon2id via the default argon2-cffi PasswordHasher, satisfying the hashing part of the requirement.  
  evidence: `_hasher = PasswordHasher()  # NN-4: Argon2id (argon2-cffi default)

def hash_password(password: str) -> str:
    return _hasher.hash(passwor`
- **info** REQ-001 `src/accounts.py:24-32`: The module provides `create_account` to store email and hashed password, and `start_password_reset` that generates a token, stores it, and sends a reset email, fulfilling the required functionality.  
  evidence: `def create_account(db, email: str, password: str) -> int:
    user_id = db.insert("customers", {"email": email, "password_hash": hash_passwo`
- **info** REQ-004 `src/orders.py:12-14`: The order placement function calls send_email synchronously right after inserting the order, providing immediate confirmation containing order number, shop and slot.  
  evidence: `send_email(customer.email, f"Order {order_id} confirmed",
               f"Order {order_id}: pickup at shop {shop_id}, slot {slot_start:%Y-%`
