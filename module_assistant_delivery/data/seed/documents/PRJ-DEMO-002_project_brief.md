# Project Brief: Clinique Horizon Appointment Reminders

Document reference: BRIEF-PRJ-DEMO-002, version 1.0. Synthetic demonstration document; the client and figures are fictional.

## 1. Objective

Clinique Horizon wants an internal service that sends appointment reminders by SMS 24 hours before each appointment, to reduce missed appointments.

## 2. Scope

- Import the next day's appointments from a nightly CSV export.
- Send one SMS reminder per appointment through the clinic's SMS provider.
- A dashboard listing sent, failed and pending reminders.

Out of scope: online appointment booking and two-way SMS replies.

## 3. Budget and timeline

Fixed price of 7,500 TND excluding VAT. Delivery within 6 weeks, in two milestones of 3 weeks each, paid 50% each.

## 4. Non-negotiable requirements

- Patient phone numbers never leave the clinic's own server, except in the request to the SMS provider.
- Reminder messages contain no medical information, only the date, time and clinic name.
