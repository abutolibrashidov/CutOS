# Barber Platform Architecture

## Product overview

Barber is a Telegram-based booking and business-management platform for independent barbers. The initial prototype serves one physical barber shop with roughly ten barbers. Barbers share a location but run independent businesses; there is no shop-owner or administrator dashboard in the prototype.

## Technology stack

- Backend: Python, FastAPI, SQLAlchemy 2 async, PostgreSQL, Alembic
- Telegram: Telegram Bot and Mini App, Aiogram 3, backend `initData` HMAC verification
- Frontend: React, Vite, TypeScript

The project runs against local services. Docker is intentionally not part of the architecture.

## Core entities and relationships

```text
Location
  └─ Barbers
       ├─ Services
       ├─ WorkingSchedule
       ├─ BlockedTime
       ├─ Appointments
       ├─ Expenses
       └─ BarberCustomer ─ Customer
```

- `Location` is a physical shared shop.
- `Barber` is an independent business user linked to a location when applicable.
- `Customer` is a shared identity record.
- `BarberCustomer` is the private relationship of one barber to one customer, including notes and visit/spend totals.
- `Service`, `WorkingSchedule`, `BlockedTime`, `Appointment`, and `Expense` belong to one barber.

## Barber data isolation

The authenticated barber is resolved from verified Telegram identity. Endpoints must derive ownership from that authenticated barber, not from a `barber_id` supplied by the client. Queries for private data must be scoped to that barber. A barber must never see another barber's services, schedules, appointments, expenses, notes, customer relationship data, or business statistics.

## Services and appointments

Services are individual to each barber. Prices are integer UZS values, never floating point. An appointment stores `service_name_at_booking`, `price_at_booking`, and `duration_at_booking`; these snapshots preserve historical data when a service changes later. Appointment statuses support pending, confirmed, completed, cancelled, and no-show states.

## Telegram authentication

The Mini App sends Telegram's signed `initData`. The backend validates its HMAC with the bot token, validates `auth_date` freshness, and reads the nested signed user data. `initDataUnsafe`, unverified user IDs, and client-provided barber IDs are not trusted. A development-only test authentication mode is disabled outside the development environment.

## Current prototype scope

Current Stage 3 functionality covers barber profile, services, weekly schedule, blocked time, customer booking, availability, multi-service appointments, customer/barber cancellation, and walk-ins.

## Future direction and exclusions

The schema allows future multiple locations and independent barbers without a redesign. Booking supports a selected barber or “Any Available Barber”; the latter assigns a concrete available barber at booking time. The availability engine uses schedules, appointments, blocked time, service duration, and 15-minute start intervals.

Not currently in scope: SaaS billing, payments, shop-owner administration, salaries, full accounting, marketplace features, AI recommendations, advanced marketing, loyalty systems, multi-location administration UI, advanced analytics, and notifications.
