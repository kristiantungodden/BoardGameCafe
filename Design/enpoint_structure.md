# Boardgame Cafe Endpoints and API structure

## Web URL Structure

### Customer

- `GET /` — Landing page. **[index.html]**
- `GET /profile` — Personal dashboard for the logged-in user.
- `GET /login` — User authentication form. **[login.html]**
- `GET /register` — New account registration form.
- `GET /games` — Browsable game library with search and filters. **[games.html]**
- `GET /games/<id>` — Detailed view for an individual game title.
- `GET /booking` — Primary entry point for table and game reservations.
- `GET /reservations` — Step-by-step reservation wizard. **[reservations.html]**

### Steward

- `GET /steward` — Main dashboard for managing pending and active reservations. **[steward_dashboard.html]**
- `GET /steward/floorplan` — Live visual map of table statuses and check-in management. **[floorplan.html]**

### Admin

- `GET /admin` — High-level overview of revenue, usage, and system metrics. **[admin_dashboard.html]**
- `GET /admin/inventory` — Management interface for game titles and physical copies. **[admin_inventory.html]**
- `GET /admin/settings` — Global configuration for fees, policies, and staff permissions. **[admin_settings.html]**

## Web API Structure

### Auth & Users (`auth.py`, `deps.py`)

- `POST /api/auth/register` - Creates a new customer account.
- `POST /api/auth/login` - Authenticates a user and returns a JWT/Session.
- `POST /api/auth/reset-password` - Triggers a Celery task to send a reset email.
- `GET /api/users/me` - Retrieves the currently logged-in user's profile.

### Games (`games.py`)

- `GET /api/games` - Lists games (supports pagination, filtering by tags/complexity).
- `GET /api/games/{id}` - Gets details for a specific game, including available copies.
- `GET /api/games/{id}/reviews` - Fetches customer ratings and reviews.

### Tables (`tables.py`)

- `GET /api/tables/availability` - Checks table availability for a specific date/time range and party size.

### Reservations (`reservations.py`)

- `POST /api/reservations` - Creates a draft reservation (triggers database lock on the time slot).
- `GET /api/reservations/{id}` - Retrieves reservation details.
- `PATCH /api/reservations/{id}/cancel` - Cancels a reservation (applies policy-aware refund logic).
- `POST /api/reservations/{id}/pay` - Initiates Vipps payment integration.
- `POST /api/reservations/waitlist` - Adds a customer to the waitlist.

### Steward (`steward.py`)

- `GET /api/steward/reservations` - Lists today's reservations (filtered by status).
- `POST /api/steward/reservations/{id}/seat` - Marks a party as seated (updates table status).
- `POST /api/steward/reservations/{id}/assign-game` - Ties a specific `GameCopy` to a reservation.
- `POST /api/steward/copies/{copy_id}/checkout` - Marks a physical game copy as in-use.
- `POST /api/steward/copies/{copy_id}/return` - Marks a physical game copy as returned/available.
- `POST /api/steward/copies/{copy_id}/incident` - Reports damage or missing pieces.

### Admin (`admin.py`)

- `GET /api/admin/stats` - Fetches aggregated data (revenue, most popular games).
- `POST /api/admin/games` - Adds a new game to the catalog.
- `POST /api/admin/copies` - Registers a new physical copy (`GameCopy`) to the inventory.
- `PATCH /api/admin/users/{id}/role` - Promotes a user to Steward or Admin.