# Live review check: qwen3-4b-base

Synthetic M2 deliverable with planted defects (see `eval/datasets/review_demo_gold.json`). Real run through the HTTP API on the local model. Verdicts are after code-side evidence verification.

- Verdict accuracy: **9/13**
- Planted defects detected with verified evidence (blocker/major): **2/2**
- Findings kept: 10; dropped unverified: {'quote_not_at_location': 1}
- Wall time: 108.6 s for 13 requirements; model `qwen3:4b-instruct-2507-q4_K_M`

| Requirement | Gold | Model said | Final verdict | OK | Note |
|---|---|---|---|---|---|
| NN-1 | violates/partial | violates | violates | yes |  |
| NN-2 | cannot_determine | violates | violates | no |  |
| NN-3 | cannot_determine | violates | violates | no |  |
| NN-4 | violates/partial | violates | violates | yes |  |
| NN-5 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-001 | conforms/partial | conforms | conforms | yes |  |
| REQ-002 | cannot_determine | cannot_determine | cannot_determine | yes |  |
| REQ-003 | conforms/partial | conforms | conforms | yes |  |
| REQ-004 | conforms/partial | conforms | conforms | yes |  |
| REQ-005 | cannot_determine | partial | partial | no |  |
| REQ-006 | conforms | conforms | conforms | yes |  |
| REQ-007 | cannot_determine | None | review_failed | no | [{"served_by": "local", "model": "qwen3:4b-instruct-2507-q4_K_M", "error": "bad_response"}] |
| REQ-008 | cannot_determine | cannot_determine | cannot_determine | yes |  |

## Findings

- **blocker** NN-1 `src/slots.py:6-7`: The requirement specifies a maximum of 20 orders per 15-minute slot, but the code defines MAX_ORDERS_PER_SLOT as 25, which exceeds the limit.  
  evidence: `MAX_ORDERS_PER_SLOT = 25`
- **blocker** NN-2 `README.md:15-15`: The README.md mentions only the back-office, which is not customer-facing. There is no content in the deliverable files that addresses customer-facing pages or their accessibility compliance with WCAG 2.1 AA.  
  evidence: `The staff back-office is planned for M3.`
- **blocker** NN-3 `src/mailer.py:6-19`: The email server host 'smtp.atelier.example' is not located in Tunisia or the European Union, and there is no indication that it is hosted in a compliant region. This violates the requirement that personal data must be stored only on servers in Tunisia or the EU and not sent to third-party analytics tools.  
  evidence: `SMTP_HOST = "smtp.atelier.example"`
- **blocker** NN-4 `src/accounts.py:10-11`: The password hashing function uses SHA-256, which is not Argon2id or bcrypt as required by NN-4 (MUST).  
  evidence: `return hashlib.sha256(password.encode("utf-8")).hexdigest()`
- **major** NN-4 `README.md:15-15`: The staff back-office is mentioned as being planned for M3, but there is no evidence that two-factor authentication is implemented for any staff account.  
  evidence: `- The staff back-office is planned for M3.`
- **major** REQ-003 `src/orders.py:9-14`: The code checks if a slot is open using the slot_is_open function and raises an error if it is full or closed, which satisfies the requirement that full or closed slots cannot be selected.  
  evidence: `if not slot_is_open(slot_start, now, orders_in_slot):
        raise ValueError("This pickup slot is full or closed.")`
- **minor** REQ-005 `src/orders.py:7-15`: The place_order function checks if a pickup slot is open (has capacity and booking hasn't closed) before inserting an order, which supports staff viewing a daily order list sorted by pickup slot. The function also allows marking orders as ready implicitly through the order insertion process, though no explicit 'mark as ready' functionality is present in the provided code.  
  evidence: `def place_order(db, customer, cart, shop_id, slot_start, now):
    orders_in_slot = db.count("orders", {"shop_id": shop_id, "slot_start": sl`
- **info** REQ-001 `src/accounts.py:18-22`: The function start_password_reset creates a token and sends an email with a reset link, fulfilling the requirement for password reset via email.  
  evidence: `def start_password_reset(db, email: str) -> None:    token = secrets.token_urlsafe(32)    db.insert("password_resets", {"email": email, "tok`
- **info** REQ-004 `src/orders.py:13-14`: The code includes a comment indicating that the email confirmation is sent right after the order is inserted, which aligns with the requirement to send an email within 1 minute of placing the order.  
  evidence: `REQ-004: confirmation email with order number, shop and slot, sent synchronously right after insert.`
- **info** REQ-006 `src/orders.py:20-21`: The code checks if the order is within 3 hours of pickup, and if so, raises an error preventing cancellation. This matches the requirement that cancellation is allowed up to 3 hours before pickup.  
  evidence: `if (order.slot_start - now).total_seconds() < 3 * 3600:
        raise ValueError("Orders can be cancelled up to 3 hours before pickup.")`
