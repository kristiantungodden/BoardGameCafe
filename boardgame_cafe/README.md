# BoardGameCafe Application

This folder contains the backend application code for the BoardGameCafe project.
The codebase follows a layered architecture inspired by Clean Architecture and DDD.

## File Structure

```text
boardgame_cafe/
|- Dockerfile
|- requirements.txt
|- setup.cfg
|- pytest.ini
|- .env
|- .env.example
|- frontend/
|- src/
|  |- app.py
|  |- config.py
|  |- boardgame_cafe.db
|  |- instance/
|  |- application/
|  |  |- interfaces/
|  |  |  `- repositories.py
|  |  `- use_cases/
|  |     |- game_use_cases.py
|  |     |- payment_use_cases.py
|  |     |- reservation_use_cases.py
|  |     `- user_use_cases.py
|  |- domain/
|  |  |- exceptions.py
|  |  |- events/
|  |  |  |- domain_event.py
|  |  |  |- game_events.py
|  |  |  |- payment_events.py
|  |  |  |- reservation_events.py
|  |  |  `- handlers.py
|  |  `- models/
|  |     |- game.py
|  |     |- payment.py
|  |     |- reservation.py
|  |     |- table.py
|  |     |- user.py
|  |     `- waitlist.py
|  |- infrastructure/
|  |  |- extensions.py
|  |  |- database/
|  |  |  `- models.py
|  |  |- repositories/
|  |  |- payment/
|  |  |  `- vipps.py
|  |  |- message_bus/
|  |  |  `- celery_app.py
|  |  `- email/
|  `- presentation/
|     |- api/
|     |  |- admin.py
|     |  |- auth.py
|     |  |- deps.py
|     |  |- games.py
|     |  |- reservations.py
|     |  |- steward.py
|     |  `- tables.py
|     `- schemas/
|        |- game.py
|        |- payment.py
|        |- reservation.py
|        |- table.py
|        `- user.py
`- tests/
   |- conftest.py
   |- unit/
   |  |- test_models.py
   |  `- test_use_cases.py
   `- integration/
      `- test_api.py
```

## Architecture Layers

### Domain
Path: `src/domain/`

Purpose:
- Contains the core business concepts and rules.
- Should be independent of frameworks and external services.

What is here:
- `models/`: Core entities such as users, reservations, games, tables, and payments.
- `exceptions.py`: Domain-specific exceptions and validation errors.
- `events/`: Domain events and handlers for business events.

### Application
Path: `src/application/`

Purpose:
- Coordinates business workflows and use cases.
- Uses domain objects and abstracts data access behind interfaces.

What is here:
- `use_cases/`: Orchestration logic for actions like reservations, users, games, and payments.
- `interfaces/`: Contracts (for example repository interfaces) that infrastructure implements.

### Infrastructure
Path: `src/infrastructure/`

Purpose:
- Handles framework and external system concerns.
- Implements technical details needed by higher layers.

What is here:
- `database/models.py`: Persistence models.
- `repositories/`: Repository implementations.
- `extensions.py`: Flask extensions setup.
- `payment/`: Payment provider integration (Vipps).
- `message_bus/`: Async/event messaging setup (Celery).
- `email/`: Email-related integration code.

### Presentation
Path: `src/presentation/`

Purpose:
- Exposes the application to clients (HTTP API).
- Validates input/output and maps requests to use cases.

What is here:
- `api/`: Flask blueprints and route modules by feature area.
- `schemas/`: Request/response schemas.

## Core Entry Files

- `src/app.py`: Flask app factory, extension initialization, blueprint registration, and error handlers.
- `src/config.py`: Environment-specific app configuration.
- `../run.py` (repo root): Main entry script used by Flask CLI.

## How Layers Interact

Typical request flow:
1. A request enters through `presentation/api`.
2. The route calls a use case in `application/use_cases`.
3. The use case works with `domain` entities and rules.
4. Persistence/external calls go through `infrastructure` implementations.
5. A response is returned through `presentation` schemas.

## Next Steps

1. Implement one vertical feature slice end-to-end (recommended: Reservations).
   - Add use case logic in `src/application/use_cases/reservation_use_cases.py`.
   - Add repository implementation in `src/infrastructure/repositories/`.
   - Add HTTP endpoints in `src/presentation/api/reservations.py`.
   - Add request/response validation in `src/presentation/schemas/reservation.py`.

2. Add tests for the same slice before expanding scope.
   - Unit tests for domain and use-case behavior in `tests/unit/`.
   - Integration/API tests in `tests/integration/test_api.py`.

3. Implement authentication basics.
   - Register/login flow in `src/presentation/api/auth.py`.
   - Password hashing and verification in domain/application layer.
   - Auth dependency wiring in `src/presentation/api/deps.py`.

4. Stabilize persistence and migrations.
   - Ensure ORM models match domain needs in `src/infrastructure/database/models.py`.
   - Add and use migration workflow (Flask-Migrate/Alembic).

5. Improve operational concerns.
   - Add structured logging and consistent error responses.
   - Add environment-specific settings validation in `src/config.py`.
   - Document required environment variables in `.env.example`.
