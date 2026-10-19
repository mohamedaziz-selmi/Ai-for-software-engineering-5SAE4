# Project Specification: Café Jasmin

Synthetic training document RAFT-P012. The client, people and figures are fictional.

## 1. Context and objectives

Café Jasmin wants a table reservation website. The objective is to replace manual handling of table reservations and reduce errors.

## 2. Parties

The client is Café Jasmin. The client's project contact address is pm.raftp012@example.com, and the phone number for urgent issues is +216 25 936 718. The freelancer designs, builds, tests and deploys the application.

## 3. Scope

### 3.1 In scope

- Users can let staff see tonight's reservations by table.
- Users can export the daily reservations as CSV.
- Users can choose a date, time and party size.
- Users can receive an SMS confirmation.
- Users can manage opening hours and closed days.

### 3.2 Out of scope

- Online card payment; customers pay on site.
- Home delivery.
- A loyalty programme.

### 3.3 Change requests

Any feature that is not listed in section 3.1 is a change request. The freelancer sends an estimate within 3 business days, and work starts only after written approval by the client.

## 4. Non-negotiable requirements

- NN-1: Passwords are hashed with bcrypt.
- NN-2: Every administrator account uses two-factor authentication.
- NN-3: Personal data is stored only on servers located in Tunisia or the European Union.
- NN-4: Customer-facing pages meet WCAG 2.2 level AA.

## 5. Milestones and payments

- M1, due at the end of week 2: clickable prototype and data model. Payment: 10% of the price.
- M2, due at the end of week 9: main user flow working on staging. Payment: 40% of the price.
- M3, due at the end of week 13: back-office, notifications and test report. Payment: 30% of the price.
- M4, due at the end of week 19: production deployment and handover documentation. Payment: 20% of the price.

## 6. Acceptance

The client has 3 business days to review each milestone. A milestone is accepted when no blocking defect remains. Each milestone includes up to 1 rounds of revisions; further rounds are change requests.

## 7. Contract terms

- Fixed price: 37,000 TND excluding VAT, paid per milestone according to section 5. Invoices are payable within 30 days.
- Intellectual property on the delivered application transfers to the client after the final payment.
- Warranty: the freelancer fixes defects reported within 30 days after final acceptance at no extra cost.
- Termination: either party may terminate with 15 days of written notice.
- Confidentiality: both parties keep business information confidential for 2 years after the project ends.
- Late delivery: a penalty of 2% of the price per week of delay applies, capped at 10%.

## 8. Communication

A 60-minute progress call takes place every Thursday. Decisions that change scope, price or deadlines are confirmed in writing.

