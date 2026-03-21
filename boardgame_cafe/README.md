"""
README for Board Game Café Application

## Project Structure

The application follows Clean Architecture principles with clear separation of concerns:

### Directory Structure

```
src/
├── config.py                 # Application configuration
├── main.py                   # Flask application entry point
├── domain/                   # Domain layer (business logic)
│   ├── models/              # Domain entities
│   ├── events/              # Domain events and handlers
│   └── exceptions.py        # Custom domain exceptions
├── application/             # Application layer (use cases)
│   ├── interfaces/          # Repository and service interfaces
│   └── use_cases/           # Business logic orchestration
├── infrastructure/          # Infrastructure layer (external concerns)
│   ├── database/            # Database setup and ORM models
│   ├── repositories/        # Repository implementations
│   ├── message_bus/         # Event publishing
│   └── email/               # Email service
└── presentation/            # Presentation layer (API)
    ├── api/                 # Flask blueprint route handlers
    └── schemas/             # Pydantic request/response schemas
```

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy and configure environment:
   ```bash
   cp .env.example .env
   ```

3. Initialize the database (will be created automatically on first run)

## Running the Application

Start the Flask development server:

```bash
python -m flask run
```

Or using the main entry point:

```bash
python src/main.py
```

The API will be available at:
- App: http://localhost:8000
- Health check: http://localhost:8000/health

## Running Tests

```bash
pytest
pytest tests/unit/
pytest tests/integration/
pytest --cov=src/
```

## Key Features

- **User Management**: Customer registration, authentication, and profile management
- **Game Catalogue**: Browse and manage games with detailed metadata
- **Reservations**: Book tables with specific time slots
- **Payment Processing**: Handle reservation fees and other payments (Stripe integration ready)
- **Game Assignment**: Assign and checkout board games for reservations
- **Event-Driven Architecture**: Domain events for business process monitoring
- **Role-Based Access**: Support for customers, stewards (staff), and administrators

## Architecture Highlights

### Domain Layer
- Pure business logic without external dependencies
- Domain entities (User, Game, Reservation, etc.)
- Custom exceptions for domain errors
- Domain events for business process tracking

### Application Layer
- Use cases that orchestrate business operations
- Repository interfaces for data access abstraction
- Request/response DTOs
- No external dependencies

### Infrastructure Layer
- SQLAlchemy ORM with SQLite (configurable to PostgreSQL, MySQL, etc.)
- Repository implementations
- Message bus for event publishing
- Email service (SMTP with mock for development)

### Presentation Layer
- Flask REST API with blueprints
- Pydantic schemas for validation
- Clean separation of concerns
- Organized by feature (auth, games, tables, reservations)

## Configuration

All configuration is managed through environment variables defined in `.env`.
See `.env.example` for available options.

## Development Notes

- This is a template structure with many endpoints marked as "TODO"
- Password hashing is implemented in domain models but not yet integrated
- JWT token generation is prepared but not yet implemented
- Email notifications are mocked in development mode
- Database transactions and error handling are simplified for clarity

## API Endpoints

### Authentication
- `POST /auth/register` - Register a new customer
- `POST /auth/login` - Login with email and password
- `POST /auth/logout` - Logout current user

### Games
- `GET /games` - List all games
- `GET /games/{id}` - Get game details
- `POST /games` - Create new game (admin)
- `PUT /games/{id}` - Update game (admin)
- `DELETE /games/{id}` - Delete game (admin)
- `GET /games/search/title` - Search games by title
- `GET /games/search/tags` - Search games by tags

### Tables
- `GET /tables` - List all tables
- `GET /tables/{id}` - Get table details
- `POST /tables` - Create new table (admin)
- `PUT /tables/{id}` - Update table (admin)
- `DELETE /tables/{id}` - Delete table (admin)
- `GET /tables/available/search` - Find available tables

### Reservations
- `GET /reservations` - List all reservations
- `GET /reservations/{id}` - Get reservation details
- `POST /reservations` - Create new reservation
- `PUT /reservations/{id}` - Update reservation
- `DELETE /reservations/{id}` - Cancel reservation
- `POST /reservations/{id}/confirm` - Confirm reservation
- `GET /reservations/customer/{customer_id}` - Get customer's reservations

### Steward (Staff)
- `GET /steward/game-copies` - List all game copies
- `GET /steward/game-copies/{id}` - Get copy details
- `POST /steward/game-copies/{id}/assign` - Assign game to reservation
- `POST /steward/game-copies/{id}/checkout` - Checkout game
- `POST /steward/game-copies/{id}/return` - Return game
- `POST /steward/game-copies/{id}/report-damage` - Report damage

### Admin
- `GET /admin/users` - List all users
- `GET /admin/users/{id}` - Get user details
- `DELETE /admin/users/{id}` - Delete user
- `POST /admin/users/{id}/activate` - Activate user
- `POST /admin/users/{id}/deactivate` - Deactivate user
- `GET /admin/reports/revenue` - Revenue report
- `GET /admin/reports/usage` - Usage statistics
- `GET /admin/system/health` - System health check

## Next Steps

1. Implement password hashing using passlib
2. Implement JWT token generation and validation
3. Add comprehensive error handling middleware
4. Implement database migrations with Alembic
5. Add logging throughout the application
6. Implement payment provider integration
7. Add email notification system
8. Implement comprehensive test suite
9. Add API request validation
10. Deploy to production environment

## Contact & Support

For issues or questions about the project structure, refer to the design documentation
in the Design/ directory.
"""
