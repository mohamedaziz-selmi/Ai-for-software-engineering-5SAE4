# Project Specification: Rent&Go Sfax

Synthetic training document RAFT-P034. The client, people and figures are fictional.

## 1. Context and objectives

Rent&Go Sfax wants a car rental reservation portal. The objective is to replace manual handling of reservations and reduce errors.

## 2. Parties

The client is Rent&Go Sfax. The client's project contact address is pm.raftp034@example.com, and the phone number for urgent issues is +216 36 166 803. The freelancer designs, builds, tests and deploys the application.

## 3. Scope

### 3.1 In scope

- Users can let agents confirm or decline reservations.
- Users can search available cars by date and category.
- Users can upload a scan of the driving licence.
- Users can reserve a car and choose a pickup agency.
- Users can show a fleet availability calendar to staff.

### 3.2 Out of scope

- A loyalty programme.
- Home delivery.
- Native mobile applications.

### 3.3 Change requests

Any feature that is not listed in section 3.1 is a change request. The freelancer sends an estimate within 5 business days, and work starts only after written approval by the client.

## 4. Non-negotiable requirements

- NN-1: Passwords are hashed with Argon2id.
- NN-2: The home page reaches Largest Contentful Paint in under 2.5 seconds on a simulated 4G connection.
- NN-3: Monthly availability is at least 99%.
- NN-4: Personal data is stored only on servers located in the European Union.

## 5. Milestones and payments

- M1, due at the end of week 6: clickable prototype and data model. Payment: 10% of the price.
- M2, due at the end of week 11: main user flow working on staging. Payment: 40% of the price.
- M3, due at the end of week 14: back-office, notifications and test report. Payment: 30% of the price.
- M4, due at the end of week 17: production deployment and handover documentation. Payment: 20% of the price.

## 6. Acceptance

The client has 5 business days to review each milestone. A milestone is accepted when no blocking defect remains. Each milestone includes up to 2 rounds of revisions; further rounds are change requests.

## 7. Contract terms

- Fixed price: 19,000 TND excluding VAT, paid per milestone according to section 5. Invoices are payable within 45 days.
- Intellectual property on the delivered application transfers to the client after the final payment.
- Warranty: the freelancer fixes defects reported within 30 days after final acceptance at no extra cost.
- Termination: either party may terminate with 30 days of written notice.
- Confidentiality: both parties keep business information confidential for 2 years after the project ends.
- Late delivery: a penalty of 1% of the price per week of delay applies, capped at 10%.

## 8. Communication

A 60-minute progress call takes place every Thursday. Decisions that change scope, price or deadlines are confirmed in writing.

