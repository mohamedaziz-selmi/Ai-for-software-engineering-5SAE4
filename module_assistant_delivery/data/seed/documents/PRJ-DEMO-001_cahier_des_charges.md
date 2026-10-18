# Project Specification (Cahier des charges): Atelier Lumière Online Ordering

Document reference: CDC-PRJ-DEMO-001, version 1.0, agreed by both parties on 10 October 2026.
Synthetic demonstration document. The client, people and figures are fictional.

## 1. Context and objectives

Atelier Lumière is a fictional bakery with three shops in Sousse. Customers currently order special cakes and large bread orders by phone, which causes lost orders and long queues at peak hours.

The objective of the project is a web application that lets customers order online and pick up their order in a chosen shop and time slot, and lets shop staff prepare orders from a single daily list.

## 2. Parties and roles

The client is Atelier Lumière, represented for this project by its operations manager. The client's project contact address is orders-pm@example.com. The client validates milestones and answers questions from the freelancer.

The freelancer is an independent full-stack developer who designs, builds, tests and deploys the application and writes the handover documentation.

## 3. Scope

### 3.1 In scope

- Customer web application: browse the catalogue, add products to a cart, choose a pickup shop and a pickup time slot, place the order, and view order history.
- Customer accounts with email and password, including password reset by email.
- Staff back-office: manage products, prices and daily availability; view the daily order list per shop; mark an order as ready for pickup.
- Email order confirmation to the customer, and a second email when the order is marked ready.
- User interface in French and English.

### 3.2 Out of scope

- Online card payment. Customers pay at pickup; online payment may be offered as a separate phase 2 project.
- Native mobile applications for iOS or Android.
- Home delivery to customer addresses.
- A loyalty or points programme.
- Migration of historical phone orders.

### 3.3 Change requests

Any feature that is not listed in section 3.1 is a change request. The client sends change requests in writing. The freelancer replies with an estimate of effort and cost within 3 business days, and no work on a change request starts before the client approves the estimate in writing.

## 4. Non-negotiable requirements

The following requirements are non-negotiable. A milestone that violates one of them cannot be accepted.

- NN-1 Pickup capacity: a shop accepts at most 20 orders per 15-minute pickup slot, and booking for a slot closes 2 hours before the slot starts.
- NN-2 Accessibility: customer-facing pages meet WCAG 2.1 level AA.
- NN-3 Personal data: customer personal data is stored only on servers located in Tunisia or the European Union, and no customer personal data is sent to third-party analytics tools.
- NN-4 Security: passwords are hashed with Argon2id or bcrypt, and every staff back-office account uses two-factor authentication.
- NN-5 Performance: the catalogue page reaches Largest Contentful Paint in under 2.5 seconds on a simulated 4G connection.

## 5. Functional requirements

Priorities use MoSCoW (must, should, could).

- REQ-001 (must): A customer can create an account with an email address and a password, and can reset a forgotten password by email.
- REQ-002 (must): A customer can browse the catalogue by category and see each product's price and availability for the chosen day.
- REQ-003 (must): A customer can choose a pickup shop and a 15-minute pickup slot; full or closed slots cannot be selected.
- REQ-004 (must): A customer receives an email confirmation with the order number, pickup shop and slot within 1 minute of placing the order.
- REQ-005 (must): Staff can view the daily order list per shop, sorted by pickup slot, and mark each order as ready.
- REQ-006 (should): A customer can cancel an order up to 3 hours before the pickup slot.
- REQ-007 (should): Staff can export the daily order list as a CSV file.
- REQ-008 (could): The catalogue shows a "best seller" badge on the five most ordered products of the previous week.

## 6. Technical constraints

- Front end in React; back end in Node.js or Python; PostgreSQL database.
- The application is packaged with Docker and deployed on a staging environment for every milestone review.
- Source code is delivered in the client's Git repository with a README explaining how to run and deploy it.
- Automated tests cover at least the order placement flow and the slot capacity rule (NN-1).

## 7. Milestones and deliverables

| Milestone | Due | Deliverables | Payment |
|---|---|---|---|
| M1 | End of week 3 | Clickable prototype of the customer flow, data model, deployment plan | 20% |
| M2 | End of week 7 | Customer ordering flow working on staging, with the slot capacity rule and automated tests | 30% |
| M3 | End of week 10 | Staff back-office, email notifications, accessibility audit report | 30% |
| Final | End of week 12 | Production deployment, handover documentation, source code | 20% |

## 8. Acceptance and review

The client has 5 business days to review each milestone. Defects are classified as blocking or non-blocking. A milestone is accepted when no blocking defect remains. Each milestone includes up to 2 rounds of revisions; further rounds are handled as change requests.

## 9. Contract terms

- Fixed price: 18,000 TND excluding VAT, paid per milestone according to section 7. Invoices are payable within 15 days.
- Intellectual property on the delivered application transfers to the client after the final payment. The freelancer may keep and reuse generic libraries that contain no client-specific code.
- Warranty: the freelancer fixes defects reported within 60 days after final acceptance at no extra cost.
- Termination: either party may terminate with 15 days of written notice. Milestones already accepted are paid in full.
- Confidentiality: both parties keep the other party's business information confidential during the project and for 2 years after it ends.

## 10. Communication

A 30-minute progress call takes place every Monday. The client answers the freelancer's questions within 2 business days. Decisions that change scope, price or deadlines are confirmed in writing.
