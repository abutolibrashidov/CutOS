# Barber Project — Agent Instructions

## Project Overview

This is a Telegram-based barber management and booking platform.

The initial prototype is designed for one physical barber shop containing approximately 10 independent barbers.

The barbers share the same physical location, but each barber operates independently.

There is no shop-owner/admin dashboard in the initial prototype.

The primary business user is the individual barber.

---

## Technology Stack

### Backend

* Python
* FastAPI
* Aiogram 3
* SQLAlchemy 2 async
* PostgreSQL
* Alembic

### Frontend

* React
* Vite
* TypeScript

### Telegram

* Telegram Bot
* Telegram Mini App
* Telegram `initData` HMAC verification on the backend

---

## IMPORTANT DEVELOPMENT RULE

The project is developed incrementally in stages.

The complete product specification is documented in:

`architecture_analysis.md`

The architecture document describes the complete product vision.

However, the agent MUST implement only the stage explicitly requested by the user.

Never automatically implement future stages.

Never assume that understanding the complete specification means implementing the entire product.

After completing the requested stage:

1. Run appropriate tests.
2. Verify the implementation.
3. Report what was changed.
4. Stop and wait for the next instruction.

---

## DO NOT USE DOCKER

Docker has intentionally been removed from this project.

Do NOT:

* recreate Docker files
* add Docker Compose
* add Dockerfiles
* introduce container-based development
* recommend Docker as a requirement

The project must be developed using the local Windows environment.

PostgreSQL will run independently.

---

## ARCHITECTURE PRINCIPLES

The following business relationships are fundamental:

```text
Location
   ↓
Barber
   ├── Services
   ├── Working Schedule
   ├── Blocked Time
   ├── Appointments
   ├── Expenses
   └── BarberCustomer relationships

Customer
   ↓
BarberCustomer
```

A Location represents a physical shared place.

A Barber is an independent business user.

A Customer represents customer identity.

`BarberCustomer` represents the private relationship between a specific barber and a customer.

---

## BARBER DATA ISOLATION

This is a critical security requirement.

A barber must only access their own:

* Services
* Appointments
* Working schedule
* Blocked time
* Expenses
* Customer relationships
* Customer notes
* Revenue/business statistics
* Profile

Never trust a `barber_id` supplied by the frontend to determine ownership.

Ownership must come from the authenticated current barber.

A barber must never be able to access another barber's private business data simply by changing an ID in a request.

---

## CUSTOMER DATA MODEL

Customers are shared identity records where appropriate.

However, each barber has their own relationship with the customer through `BarberCustomer`.

Example:

```text
Customer: Abutolib

Barber A:
18 visits
1,620,000 UZS spent

Barber B:
3 visits
270,000 UZS spent
```

Barber A must not automatically see Barber B's private customer history.

---

## SERVICES

Services belong to individual barbers.

Each barber can independently:

* Create services
* Edit services
* Change service names
* Change prices
* Change duration
* Activate/deactivate services

Do not create a globally shared fixed service catalog.

Different barbers can have completely different services and prices.

Money must be stored using integer UZS values.

Do not use floating-point numbers for monetary values.

---

## APPOINTMENTS

Appointments belong to a specific barber.

When an appointment is created, preserve historical snapshots:

* `service_name_at_booking`
* `price_at_booking`
* `duration_at_booking`

Later edits to a Service must never change historical appointment information.

Appointment status should support the architecture defined in `architecture_analysis.md`.

---

## BOOKING LOGIC

The future booking system will support:

1. Specific barber selection.
2. "Any Available Barber".

When "Any Available Barber" is selected, the system must assign a concrete available barber at booking time.

Do not leave barber assignment until arrival.

The future availability engine will consider:

* Working schedule
* Service duration
* Existing appointments
* Blocked time
* Appointment status

Starting-time intervals are 15 minutes.

---

## WALK-IN CUSTOMERS

Future walk-in support must allow:

* Name — required
* Phone — optional
* Telegram identity — optional

Walk-ins must occupy the barber's schedule.

Do not implement walk-in functionality unless explicitly requested by the current development stage.

---

## TELEGRAM AUTHENTICATION

Telegram authentication must use secure `initData` HMAC verification on the backend.

Never trust:

* `initDataUnsafe`
* arbitrary Telegram user IDs sent by the frontend
* arbitrary barber IDs sent by the frontend

The backend must establish the authenticated user.

If development authentication is required for local testing, it must be:

* clearly development-only
* isolated from production authentication
* disabled in production
* never used as a replacement for Telegram verification

---

## LANGUAGE

The prototype's user-facing language is Uzbek.

Use the existing frontend localization structure.

Do not scatter hard-coded user-facing strings throughout the application when they can reasonably be placed in the localization system.

Future localization may support additional languages.

---

## CURRENT SCOPE

The prototype should remain focused.

Do not add these unless explicitly requested:

* SaaS billing
* Subscription management
* Payment gateway
* Shop-owner administration
* Employee salary management
* Full accounting
* Marketplace
* AI recommendations
* Advanced marketing automation
* Complex loyalty systems
* Multi-location administration UI
* Advanced analytics
* Online payments

---

## DATABASE CHANGES

Use Alembic for schema changes.

Never modify an already-applied migration destructively.

If a schema change is necessary:

1. Modify the SQLAlchemy model.
2. Create a new Alembic migration.
3. Verify the migration.
4. Test upgrade behavior.

Do not redesign existing models without a concrete reason.

---

## CODE QUALITY

Prefer:

* Clear naming
* Type hints
* Small focused modules
* Separation of concerns
* Explicit ownership checks
* Simple solutions
* Appropriate validation
* Useful automated tests

Avoid:

* Unnecessary abstractions
* Premature optimization
* Large monolithic files
* Duplicate business logic
* Unrequested dependencies
* Unrequested features

---

## DEVELOPMENT ENVIRONMENT

This project runs directly on the local machine.

Do not assume Docker is available.

Backend and frontend should be runnable independently.

PostgreSQL is an external local service.

---

## CHANGE DISCIPLINE

Before making significant architectural changes:

* inspect the existing implementation
* check `architecture_analysis.md`
* check existing migrations
* check existing tests
* explain why the change is necessary

Do not rewrite working code merely for stylistic preference.

Preserve existing functionality when adding new functionality.

---

## AGENT BEHAVIOR

When asked to implement a stage:

1. Inspect the existing implementation.
2. Understand the relevant architecture.
3. Implement only the requested stage.
4. Test the changes.
5. Fix issues discovered during testing.
6. Report the result.
7. Stop.

Never continue automatically into the next stage.
