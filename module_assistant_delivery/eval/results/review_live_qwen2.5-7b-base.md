# Live review check: qwen2.5-7b-base

Synthetic M2 deliverable with planted defects (see `eval/datasets/review_demo_gold.json`). Real run through the HTTP API on the local model. Verdicts are after code-side evidence verification.

- Verdict accuracy: **13/13**
- Planted defects detected with verified evidence (blocker/major): **2/2**
- Findings kept: 9; dropped unverified: {'quote_not_at_location': 2, 'unknown_file': 3}
- Wall time: 81.7 s for 13 requirements; model `qwen2.5:7b-instruct`

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

- **blocker** NN-4 `src/accounts.py:9-15`: The password is hashed using SHA-256, which does not meet the requirement of using Argon2id or bcrypt.  
  evidence: `def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode(`
- **major** NN-1 `src/slots.py:6-6`: The maximum number of orders per slot is set to 25, which violates the requirement of at most 20 orders.  
  evidence: `MAX_ORDERS_PER_SLOT = 25`
- **info** NN-4 `README.md:15-15`: The staff back-office is only planned for M3, not implemented in this deliverable.  
  evidence: `- The staff back-office is planned for M3.`
- **info** REQ-001 `src/accounts.py:13-15`: The `create_account` function allows a customer to create an account with an email and password.  
  evidence: `def create_account(db, email: str, password: str) -> int:
    user_id = db.insert("customers", {"email": email, "password_hash": hash_passwo`
- **info** REQ-001 `src/mailer.py:10-19`: The `send_email` function is used to send emails, which is required for password reset.  
  evidence: `def send_email(to: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = "orders@atelier.example"
    me`
- **info** REQ-001 `src/accounts.py:18-21`: The `start_password_reset` function sends a password reset email, which is part of the requirement.  
  evidence: `def start_password_reset(db, email: str) -> None:
    token = secrets.token_urlsafe(32)
    db.insert("password_resets", {"email": email, "t`
- **info** REQ-003 `src/orders.py:7-10`: The code checks if a slot is open before placing an order, ensuring that full or closed slots cannot be selected.  
  evidence: `    orders_in_slot = db.count(`
- **info** REQ-004 `src/orders.py:13-14`: The confirmation email is sent synchronously right after the order is inserted.  
  evidence: `send_email(customer.email, f"Order {order_id} confirmed",
                f"Order {order_id}: pickup at shop {shop_id}, slot {slot_start:%Y-`
- **info** REQ-006 `src/orders.py:18-23`: The `cancel_order` function correctly checks if the order can be cancelled up to 3 hours before the pickup slot.  
  evidence: `def cancel_order(db, order, now):
    """REQ-006: cancellation is allowed up to 3 hours before the pickup slot."""
    if (order.slot_start `
