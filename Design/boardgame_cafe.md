# Board Game Café — Reservation & Management System

## Application description

A web app for a fictional board-game café. Customers can browse a visual game
library, reserve tables and specific time slots, and optionally pre-borrow
games for the session. Staff manage the floor plan, assign/hand out/receive game
copies, track availability, and enforce late/clean-up fees. Admins manage
inventory, pricing, fees, and reports. A delivery component is not needed;
the “courier” analogue is the **Game Steward** who handles physical hand-offs
in the café.

---

## Domain-Driven Design snapshot

### Core entities (suggested)

- **Game** (catalogue metadata: title, min/max players, playtime,
  weight/complexity, tags, image, description)
- **GameCopy** (physical copy with unique ID, condition, status: Available/Reserved/CheckedOut/Missing/Repair)
- **Table** (capacity, location/zone, status, features)
- **Reservation** (Customer, Table, time slot, party size, status: Submitted/Confirmed/Seated/Completed/Cancelled/NoShow)
- **Customer** (name, phone, email, auth identities, preferences, rating history)
- **Steward** (staff user, permissions)
- **Payment** (provider, amount, status, type: ReservationFee/LateFee/DamageFee)
- **Review/Rating** (per Game; optional comments)
- **WaitlistEntry** (for fully booked times)

### Aggregates & invariants

- **Reservation (aggregate root)**Invariants:
  - table capacity ≥ party size
  - no overlapping reservations on the same table/time window
  - only Available GameCopies can be pre-assigned
- **GameCopy (aggregate root for copy lifecycle)**
  Invariants: status transitions are valid (e.g., Available → Reserved →
  CheckedOut → Available).

### Domain events (examples)

- `ReservationRequested`
- `ReservationConfirmed`
- `ReservationCancelled`
- `ReservationNoShow`
- `ReservationSeated`
- `ReservationCompleted`
- `GameAssignedToReservation`
- `GameCheckoutStarted`
- `GameReturned`
- `DamageReported`
- `PaymentCaptured`
- `WaitlistTriggered`

---

## Actors and workflows (prioritized)

### Customer

#### **Workflows**

1. Register as customer.
2. Log in.
3. Fill out profile.
4. Browse visual game library.
5. View table availability on floor-plan.
6. Place a reservation.
7. Pay reservation fee.
8. View reservation status.
9. Modify/Cancel reservation (policy-aware).
10. Check-in (QR code).
11. See assigned games; request swaps.
12. Rate games post-session.
13. See reservation history.
14. Join waitlist for fully booked slots.
15. Receive notifications.

### Game Steward (staff)

#### **Workflows**

1. Log in (staff portal).
2. View pending reservations.
3. Seat parties; update status.
4. Assign/Swap games.
5. Check out & check in GameCopies.
6. Mark incident (damage/loss).
7. Manage waitlist.
8. See personal dashboard.
9. View earnings/tip pool (optional).

### Administrator

#### **Workflows**

1. Separate admin login.
2. Force password change on first login.
3. Manage users.
4. Approve/decline steward registrations.
5. Dashboard with stats.
6. Manage game catalogue & copies.
7. Manage café floor & tables.
8. Set policies/fees.
9. Reports (revenue, utilization, popularity).
10. Content & promos.

---

## UI & UX highlights

- Rich floor-plan UI (drag-and-drop tables).
- Visual game library with filters.
- Reservation wizard (party size → time → table → games → pay).
- Live notifications in-app.
- Accessible design.

---

## Pricing & policy

- Reservation fee per table/time-slot.
- Cancellation: free until X hours before; then partial fee.
- No-show fee: full reservation fee retained.
- Late return / damage: steward proposes fee; admin confirms.

---

## Technical requirements (pass criteria)

- Web application with **database**.
- Registration/login for customers & stewards; separate admin login.
- Persisted reservation drafts.
- Runs with Docker & docker-compose.
- GitHub Actions automated tests.
- Database seeding with demo data.
- Reservation status tracking with history.
- Service/Reservation fee applied.
- Customer can view reservations & history.
- Steward dashboard for managing reservations.
- Admin tools for games, tables, fees.

### Suggested stack

- **Backend**: Node.js, .NET, or Django.
- **DB**: Postgres.
- **Auth**: JWT with roles.
- **Frontend**: React + TypeScript, Tailwind.
- **Infra**: Docker, Mailhog, Redis.
- **Events/Queues**: BullMQ/RabbitMQ.

---

## Advanced requirements

1. Password self-reset via email.
2. Social logins (Google, Microsoft, etc.).
3. Email sending (welcome, confirmation, waitlist, damage fee).
4. External payment provider (Stripe/Klarna).
5. Realtime push notifications.
6. AI game recommender.
7. Leaderboards & popularity stats.
8. Incident workflow with photo uploads.
9. QR flows for check-in and game copies.
10. Floor load optimizer (algorithmic).

---

## Data model (starter sketch)

**Game**
`id, title, min_players, max_players, playtime_min, complexity, tags[], description, image_url, created_at`

**GameCopy**
`id, game_id, copy_code, condition_note, status, location, updated_at`

**Table**
`id, name, capacity, zone, features jsonb, status`

**Reservation**
`id, customer_id, table_id, start_ts, end_ts, party_size, status, notes, created_at`

**ReservationGame**
`reservation_id, game_copy_id, requested_game_id`

**User**
`id, role, name, email, phone, password_hash, force_password_change`

**Payment**
`id, reservation_id, type, provider, amount_cents, currency, status, provider_ref, created_at`

**Rating**
`id, customer_id, game_id, stars, comment, created_at`

**WaitlistEntry**
`id, customer_id, desired_time_range, party_size, created_at, status`

---

## API surface (illustrative)

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/password-reset`
- `GET /games`
- `GET /tables/availability`
- `POST /reservations`
- `POST /reservations/{id}/confirm`
- `POST /reservations/{id}/cancel`
- `POST /reservations/{id}/checkin`
- `POST /reservations/{id}/assign-game`
- `POST /game-copies/{id}/checkout`
- `POST /game-copies/{id}/return`
- `GET /me/reservations`
- `GET /admin/dashboard`
- `POST /admin/games`
- `POST /admin/copies`
- `POST /admin/tables`
- `POST /admin/users/invite`
- `POST /payments/intent`
