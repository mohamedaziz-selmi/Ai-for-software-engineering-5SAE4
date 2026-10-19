# Project Specification: Café Jasmin

Synthetic training document RAFT-P038. The client, people and figures are fictional.

## 1. Context and objectives

Café Jasmin wants a table reservation website. The objective is to replace manual handling of table reservations and reduce errors.

## 2. Parties

The client is Café Jasmin. The client's project contact address is pm.raftp038@example.com, and the phone number for urgent issues is +216 90 620 442. The freelancer designs, builds, tests and deploys the application.

## 3. Scope

### 3.1 In scope

- Users can receive an SMS confirmation.
- Users can cancel a reservation from the confirmation link.
- Users can manage opening hours and closed days.
- Users can choose a date, time and party size.
- Users can export the daily reservations as CSV.

### 3.2 Out of scope

- Native mobile applications.
- Migration of historical data.
- Multi-currency pricing.

### 3.3 Change requests

Any feature that is not listed in section 3.1 is a change request. The freelancer sends an estimate within 5 business days, and work starts only after written approval by the client.

## 4. Non-negotiable requirements

- NN-1: The home page reaches Largest Contentful Paint in under 2 seconds on a simulated 4G connection.
- NN-2: Every administrator account uses two-factor authentication.
- NN-3: Passwords are hashed with bcrypt.
- NN-4: No personal data appears in application logs.

## 5. Milestones and payments

- M1, due at the end of week 8: clickable prototype and data model. Payment: 30% of the price.
- M2, due at the end of week 13: main user flow working on staging. Payment: 30% of the price.
- M3, due at the end of week 14: back-office, notifications and test report. Payment: 20% of the price.
- M4, due at the end of week 15: production deployment and handover documentation. Payment: 20% of the price.

## 6. Acceptance

The client has 3 business days to review each milestone. A milestone is accepted when no blocking defect remains. Each milestone includes up to 2 rounds of revisions; further rounds are change requests.

## 7. Contract terms

- Fixed price: 31,500 TND excluding VAT, paid per milestone according to section 5. Invoices are payable within 45 days.
- Intellectual property on the delivered application transfers to the client after the final payment.
- Warranty: the freelancer fixes defects reported within 90 days after final acceptance at no extra cost.
- Termination: either party may terminate with 15 days of written notice.
- Confidentiality: both parties keep business information confidential for 3 years after the project ends.

## 8. Communication

A 60-minute progress call takes place every Thursday. Decisions that change scope, price or deadlines are confirmed in writing.

