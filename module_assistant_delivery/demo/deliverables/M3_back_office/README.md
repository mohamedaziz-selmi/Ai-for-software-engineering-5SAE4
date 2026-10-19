# M3: staff back-office, e-mails, accessibility report

Project PRJ-DEMO-001, Atelier Lumière online ordering. Synthetic demonstration deliverable; people and figures are fictional.

## What this milestone delivers

- Staff back-office: the day's order list per shop, "mark as ready", CSV export (`frontend/src/StaffOrders.jsx`, `backend/staff.py`).
- Two-factor authentication (TOTP) for every staff account (`backend/staff.py`, `db/schema.sql`).
- E-mail to the customer when an order is ready (`backend/notifications.py`, `config/notifications.json`).
- Accessibility audit report of the customer pages (`docs/accessibility_audit.txt`).
- Staging deployment for the review (`deploy/docker-compose.yml`).

## Run on staging

```sh
docker compose -f deploy/docker-compose.yml up --build
```
