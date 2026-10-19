# Atelier Lumière ordering: milestone M2, version 2 (synthetic demo deliverable)

Customer ordering flow: accounts, pickup slots, order placement, confirmation email.
Version 2 fixes the slot capacity (20 per slot), the booking cut-off (2 hours before the slot) and
password hashing (Argon2id).

## Run the tests

```
pytest -q
```

## Configuration

`SMTP_PASSWORD` (and optionally `SMTP_HOST`) must be set in the environment. No secret is stored in the code.

## Known limitations

- The staff back-office, including two-factor authentication for staff accounts, is planned for M3.
