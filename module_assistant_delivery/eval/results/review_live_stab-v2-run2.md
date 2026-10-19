# Live review check: stab-v2-run2

Deliverable `demo/deliverables/M2_v2_fixed`, scored against `eval/datasets/review_demo_v2_gold.json`. Real run through the HTTP API; review served by `hosted` model `openai/gpt-oss-120b`. Verdicts are after code-side evidence verification.

- Verdict accuracy: **11/13**
- Planted defects detected with verified evidence (blocker/major): **0/0**
- Findings kept: 7; dropped unverified: {}
- Wall time: 133.5 s for 13 requirements; model `openai/gpt-oss-120b`

| Requirement | Gold | Model said | Final verdict | OK | Note |
|---|---|---|---|---|---|
| NN-1 | conforms | conforms | conforms | yes |  |
| NN-2 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| NN-3 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| NN-4 | conforms/partial/cannot_determine | violates | violates | no |  |
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

- **blocker** NN-4 `README.md:19-19`: The README states that two-factor authentication for staff accounts is only planned for a future milestone (M3), meaning it is not currently implemented, violating the MUST requirement.  
  evidence: `- The staff back-office, including two-factor authentication for staff accounts, is planned for M3.`
- **info** NN-1 `src/slots.py:5-14`: Constants define MAX_ORDERS_PER_SLOT = 20 and BOOKING_CLOSES_BEFORE = 2 hours, and slot_is_open enforces both capacity and booking cut‑off.  
  evidence: `MAX_ORDERS_PER_SLOT = 20  # NN-1: at most 20 orders per 15-minute slot
BOOKING_CLOSES_BEFORE = timedelta(hours=2)  # NN-1: booking closes 2 `
- **info** NN-4 `src/accounts.py:10-14`: Password hashing uses Argon2id via the argon2-cffi PasswordHasher, satisfying the hashing part of the requirement.  
  evidence: `_hasher = PasswordHasher()  # NN-4: Argon2id (argon2-cffi default)

def hash_password(password: str) -> str:
    return _hasher.hash(passwor`
- **info** REQ-001 `src/accounts.py:24-32`: The `create_account` function stores the provided email and a hashed password, and `start_password_reset` generates a token, records it, and sends a reset email, satisfying the required account creation and password‑reset flow.  
  evidence: `def create_account(db, email: str, password: str) -> int:
    user_id = db.insert("customers", {"email": email, "password_hash": hash_passwo`
- **info** REQ-003 `src/slots.py:5-6`: Slot duration is defined as 15 minutes, matching the required slot granularity.  
  evidence: `SLOT_MINUTES = 15`
- **info** REQ-003 `src/slots.py:10-14`: slot_is_open returns False when the slot is full or when booking has closed (2‑hour cutoff), preventing selection of such slots.  
  evidence: `if orders_in_slot >= MAX_ORDERS_PER_SLOT:
    return False
return now <= slot_start - BOOKING_CLOSES_BEFORE`
- **info** REQ-006 `src/orders.py:18-22`: The cancellation function checks that the time difference between the slot start and the current time is at least 3 hours before allowing cancellation, matching the requirement.  
  evidence: `def cancel_order(db, order, now):
    """REQ-006: cancellation is allowed up to 3 hours before the pickup slot."""
    if (order.slot_start `
