# Live review check: v3-v2-run1

Deliverable `demo/deliverables/M2_v2_fixed`, scored against `eval/datasets/review_demo_v2_gold.json`. Real run through the HTTP API; review served by `hosted` model `openai/gpt-oss-120b`. Verdicts are after code-side evidence verification.

- Verdict accuracy: **10/13**
- Planted defects detected with verified evidence (blocker/major): **0/0**
- Findings kept: 5; dropped unverified: {'quote_not_at_location': 1}
- Wall time: 184.8 s for 13 requirements; model `openai/gpt-oss-120b`

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
| REQ-004 | conforms/partial | cannot_determine | cannot_determine | no |  |
| REQ-005 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-006 | conforms | conforms | conforms | yes |  |
| REQ-007 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-008 | cannot_determine | cannot_determine | cannot_determine | yes |  |

## Findings

- **blocker** NN-4 `README.md:19-19`: Two-factor authentication for staff back‑office accounts is only planned for a future milestone (M3) and not currently implemented, violating the MUST requirement.  
  evidence: `- The staff back-office, including two-factor authentication for staff accounts, is planned for M3.`
- **info** NN-1 `src/slots.py:5-14`: Constants define MAX_ORDERS_PER_SLOT = 20 and BOOKING_CLOSES_BEFORE = 2 hours; slot_is_open returns False when orders reach the limit or when now is after slot_start minus 2 hours, satisfying the requirement.  
  evidence: `MAX_ORDERS_PER_SLOT = 20  # NN-1: at most 20 orders per 15-minute slot
BOOKING_CLOSES_BEFORE = timedelta(hours=2)  # NN-1: booking closes 2 `
- **info** NN-4 `src/accounts.py:5-10`: Password hashing uses Argon2id via the default PasswordHasher from argon2-cffi, satisfying the hashing requirement.  
  evidence: `from argon2 import PasswordHasher
_hasher = PasswordHasher()  # NN-4: Argon2id (argon2-cffi default)`
- **info** REQ-001 `src/accounts.py:24-32`: The module provides `create_account` to store email and hashed password, and `start_password_reset` that generates a token, stores it, and emails a reset link, fulfilling the required account creation and password reset flow.  
  evidence: `def create_account(db, email: str, password: str) -> int:
    user_id = db.insert("customers", {"email": email, "password_hash": hash_passwo`
- **info** REQ-006 `src/orders.py:18-21`: The cancellation logic checks that the time difference is at least 3 hours; if less, it raises an error, enforcing the 3‑hour cutoff as required.  
  evidence: `def cancel_order(db, order, now):
    """REQ-006: cancellation is allowed up to 3 hours before the pickup slot."""
    if (order.slot_start `
