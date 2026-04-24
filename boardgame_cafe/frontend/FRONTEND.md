# Frontend

HTML Templates, JavaScript, and a single CSS file.

## Structure

```
frontend/
├── templates/   # HTML templates (base.html + one template per page)
└── static/
    ├── css/     # main.css — single stylesheet for all pages
    └── js/      # admin.js, steward.js — dashboard interactivity
```

## Pages

- **Public** — home, game catalogue, login, register
- **Customer** — booking flow, payment result, my bookings, account
- **Admin** — dashboard with user/game/table/announcement management
- **Steward** — live floor view, incidents, check-ins, game copies
## Templates

### Public pages
| Template | Route | Description |
|---|---|---|
| `index.html` | `/` | Landing page |
| `games.html` | `/games` | Filterable game catalogue with detail overlay, ratings, and copy status |
| `login.html` | `/login` | Customer sign-in |
| `register.html` | `/register` | Customer sign-up |

### Customer pages (login required)
| Template | Route | Description |
|---|---|---|
| `booking.html` | `/booking` | Book a table — select date, time, party size |
| `booking_confirmation.html` | `/booking/confirmation` | Booking summary before payment |
| `payment_result.html` | `/payment/result` | Stripe payment outcome |
| `my_bookings.html` | `/my-bookings` | List of past and upcoming reservations |
| `account.html` | `/me` | View and edit profile details |
| `change_password.html` | `/me/change-password` | Password change form |

### Admin pages (admin role required)
| Template | Route | Description |
|---|---|---|
| `admin_login.html` | `/admin/login` | Separate admin login |
| `admin_dashboard.html` | `/admin` | Full control panel: users, game catalogue, floor/zone/table management, announcements, pricing, and reports |

### Steward pages (staff role required)
| Template | Route | Description |
|---|---|---|
| `steward_dashboard.html` | `/steward` | Live metrics (bookings, incidents, capacity), interactive floorplan, pending check-ins, seated parties |
| `steward_game_copies.html` | `/steward/game-copies` | View and update game copy statuses |
| `steward_incidents.html` | `/steward/incidents` | Incident list for the selected date |
| `steward_pending.html` | `/steward/pending` | Reservations pending check-in |
| `steward_seated.html` | `/steward/seated` | Currently seated parties |

## Static Assets

### `css/main.css`
Single stylesheet for all pages. Uses CSS custom properties for the design.

### `js/admin.js`
Handles all interactions on the admin dashboard:
- Fetches and renders summary stats (users, games, tables, bookings, incidents, announcements)
- CRUD operations for game catalogue and copies
- Floor → zone → table management with an SVG-style floorplan grid
- Announcement create/edit/delete
- User management (suspend, delete, role change)
- Pricing and policy settings
- CSV/JSON report downloads

All state-mutating requests include a CSRF token read from the `<meta name="csrf-token">` tag.

### `js/steward.js`
Powers the steward dashboard:
- Polls live metrics (bookings open, incidents, capacity) on a configurable interval
- Renders an interactive floorplan grouped by floor and zone (available = green, reserved = red)
- Lists pending check-ins and currently seated parties
- Incident creation and status updates
- Game copy status management



