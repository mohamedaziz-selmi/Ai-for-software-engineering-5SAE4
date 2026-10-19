# Project Specification: Atelier Bois & Lin

Synthetic training document RAFT-P014. The client, people and figures are fictional.

## 1. Context and objectives

Atelier Bois & Lin wants a click-and-collect furniture shop. The objective is to replace manual handling of orders and reduce errors.

## 2. Parties

The client is Atelier Bois & Lin. The client's project contact address is pm.raftp014@example.com, and the phone number for urgent issues is +216 72 541 763. The freelancer designs, builds, tests and deploys the application.

## 3. Scope

### 3.1 In scope

- Users can choose a collection slot at the warehouse.
- Users can send an email when an order is ready.
- Users can manage stock levels in a back-office.
- Users can browse products by room and material.
- Users can add products to a cart and place an order.

### 3.2 Out of scope

- Migration of historical data.
- Home delivery.
- Native mobile applications.

### 3.3 Change requests

Any feature that is not listed in section 3.1 is a change request. The freelancer sends an estimate within 5 business days, and work starts only after written approval by the client.

## 4. Non-negotiable requirements

- NN-1: Passwords are hashed with bcrypt.
- NN-2: The home page reaches Largest Contentful Paint in under 3 seconds on a simulated 4G connection.
- NN-3: At most 20 orders per collection slot.
- NN-4: The database is backed up every day and backups are kept for 30 days.

## 5. Milestones and payments

- M1, due at the end of week 3: clickable prototype and data model. Payment: 10% of the price.
- M2, due at the end of week 5: main user flow working on staging. Payment: 40% of the price.
- M3, due at the end of week 7: back-office, notifications and test report. Payment: 30% of the price.
- M4, due at the end of week 15: production deployment and handover documentation. Payment: 20% of the price.

## 6. Acceptance

The client has 10 business days to review each milestone. A milestone is accepted when no blocking defect remains. Each milestone includes up to 2 rounds of revisions; further rounds are change requests.

## 7. Contract terms

- Fixed price: 24,500 TND excluding VAT, paid per milestone according to section 5. Invoices are payable within 45 days.
- Intellectual property on the delivered application transfers to the client after the final payment.
- Warranty: the freelancer fixes defects reported within 60 days after final acceptance at no extra cost.
- Termination: either party may terminate with 30 days of written notice.
- Confidentiality: both parties keep business information confidential for 3 years after the project ends.

## 8. Communication

A 30-minute progress call takes place every Monday. Decisions that change scope, price or deadlines are confirmed in writing.

