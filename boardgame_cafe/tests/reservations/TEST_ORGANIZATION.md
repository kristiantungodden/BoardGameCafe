# Reservations Feature - Test Organization Guide (DDD-Aligned)

This document explains the test structure for the Reservations feature, organized by Domain-Driven Design (DDD) layers.

## Test Structure

```
tests/reservations/
├── unit/
│   ├── domain/
│   │   ├── test_reservation.py              # Domain model invariants & state transitions
│   │   └── __init__.py
│   ├── application/
│   │   ├── test_reservation_use_cases.py    # Application logic (existing)
│   │   ├── test_reservation_game_use_cases.py
│   │   └── __init__.py
│   └── presentation/
│       ├── test_schemas_reservation.py      # DTO validation
│       └── __init__.py
├── integration/
│   ├── infrastructure/
│   │   ├── test_reservation_repository.py           # Repository pattern tests (existing)
│   │   ├── test_reservation_payment_transaction.py  # Payment atomicity (existing)
│   │   ├── test_repository_abstraction.py          # Dependency inversion tests ✨ NEW
│   │   ├── test_transaction_atomicity.py           # All-or-nothing bookings ✨ NEW
│   │   └── __init__.py
│   ├── architecture/
│   │   ├── test_layer_separation.py                # Clean architecture enforcement ✨ NEW
│   │   └── __init__.py
│   ├── api/
│   │   ├── test_reservations_api.py         # API behavior tests (existing)
│   │   ├── test_api_authorization.py        # Authorization boundary tests ✨ NEW
│   │   └── test_business_rules_enforcement.py  # Business rules enforcement ✨ NEW
│   └── __init__.py
├── e2e/
│   ├── test_booking_flow.py                 # End-to-end workflows (empty - ready for tests)
│   └── __init__.py
└── __init__.py
```

## Test Categories & What They Enforce

### 1. **Unit Tests » Domain Layer** (`unit/domain/test_reservation.py`)

These tests ensure **domain models enforce their own invariants**.

**Tests Enforce:**
- Status transitions are valid (e.g., can't complete without being seated)
- Party size must be positive (> 0)
- End time must be after start time
- Status values are from valid set
- Customer ID and Table ID are positive

**Example Test:**
```python
def test_reservation_rejects_negative_party_size():
    """INVARIANT: party_size MUST be positive (> 0)."""
    with pytest.raises(ValidationError):
        TableReservation(party_size=-1)
```

**Key Principle:** Domain models are the **last line of defense** for invariants. If it gets past the domain model constructor, it's valid.

---

### 2. **Unit Tests » Application Layer** (`unit/application/`)

These tests ensure **application logic is orchestrated correctly** (already well-structured).

**Tests Enforce:**
- Use cases execute business processes
- Commands are processed correctly
- Reservations can be created, updated, cancelled
- Use cases receive dependencies via injection (covered by architecture tests below)

---

### 3. **Integration Tests » Authentication & Authorization** (`integration/api/test_api_authorization.py`)

These tests ensure **security at API boundaries**. ✨ NEW

**Tests Enforce:**
- ✅ Unauthenticated users get 401 Unauthorized
- ✅ Non-staff users only see their own reservations (filtered)
- ✅ Non-staff users get 403 Forbidden when accessing others' reservations
- ✅ Staff users can see all reservations
- ✅ Staff users can access any reservation

**Example Test:**
```python
def test_non_staff_user_only_sees_their_own_reservations(app, test_data):
    """Non-staff users must be filtered by customer_id."""
    # Create reservations for users 1, 2, 3
    # When user 1 requests /api/reservations
    # Should only see reservations where customer_id == 1
```

**Key Principle:** Authorization is **business logic**, not API fluffy stuff. Tests prove the system enforces access control.

---

### 4. **Integration Tests » Business Rules** (`integration/api/test_business_rules_enforcement.py`)

These tests enforce **cafe business rules**. ✨ NEW

**Cafe Operating Hours Rule:**
- ✅ Bookings can only start at or after 09:00
- ✅ Bookings can only end by or before 23:00
- ✅ These are hard constraints that cannot be bypassed

**Auto-Assignment Logic (Deterministic):**
- ✅ Availability endpoint suggests the SAME table auto-selection will pick
- ✅ Auto-selection picks the **smallest table** fitting party_size
- ✅ Auto-selection picks the **first available copy** by ID
- ✅ Auto-selection respects existing confirmed bookings

**Example Test:**
```python
def test_auto_selection_chooses_smallest_fitting_table(app, test_data):
    """For party_size=4: pick Table 1 (cap 4), not Table 2 (cap 6)."""
    # Create booking for party of 4
    # Verify table_id == smallest_fitting_table
```

**Key Principle:** These tests make the **API contract explicit**: "This is what will happen when you call this endpoint."

---

### 5. **Integration Tests » Repository Pattern** (`integration/infrastructure/test_repository_abstraction.py`)

These tests enforce **dependency inversion principle**. ✨ NEW

**Tests Enforce:**
- ✅ Use cases depend on `ReservationRepositoryInterface`, not `SqlAlchemyReservationRepository`
- ✅ Use cases don't instantiate repositories (receives pre-configured instance)
- ✅ Use case source code has NO `sql`, `db.session`, or database model references
- ✅ Repository implementations match their interface contracts
- ✅ Use cases work with **any** repository implementation (swappability)

**Example Test:**
```python
def test_create_reservation_use_case_depends_on_interface_not_implementation():
    """Use case.__init__(repo) must be annotated with interface type."""
    sig = inspect.signature(CreateReservationUseCase.__init__)
    assert sig.parameters['repo'].annotation == ReservationRepositoryInterface
```

**Key Principle:** This makes the system **testable** (use fakes instead of database) and **flexible** (swap implementations).

---

### 6. **Integration Tests » Transaction Atomicity** (`integration/infrastructure/test_transaction_atomicity.py`)

These tests enforce **all-or-nothing booking semantics**. ✨ NEW

**Tests Enforce:**
- ✅ If no suitable table available, entire booking fails (no partial state)
- ✅ If party too large, booking fails (no orphaned records)
- ✅ Two concurrent bookings for same table don't both succeed
- ✅ Payment failures recorded without rolling back reservation (allows retry)

**Example Test:**
```python
def test_booking_fails_atomically_if_table_unavailable(app, test_data):
    """If booking fails, NO reservation should be created."""
    initial_count = len(repo.list_all())
    with pytest.raises(ValidationError):
        handler(CreateReservationCommand(...))
    assert len(repo.list_all()) == initial_count
```

**Valid Partial States:**
- `status="pending_payment"`: Reservation confirmed, payment being processed

**Invalid Partial States (must never occur):**
- Reservation exists but no games assigned
- Games assigned but no reservation
- Payment exists but no reservation

---

### 7. **Integration Tests » Clean Architecture** (`integration/architecture/test_layer_separation.py`)

These tests enforce **layer separation in clean architecture**. ✨ NEW

**Domain Layer Purity:**
- ✅ Domain models have NO Flask/Werkzeug imports
- ✅ Domain models have NO SQLAlchemy imports
- ✅ Domain is pure business logic

**Presentation Layer Boundaries:**
- ✅ API routes do NOT import database model classes (TableReservationDB, etc.)
- ✅ API routes do NOT instantiate use cases directly
- ✅ Routes receive use cases via dependency injection

**Application Layer Dependency Injection:**
- ✅ Use cases receive all dependencies through `__init__`, not imports
- ✅ Dependency injection container only wires components (no business logic)

**Import Hierarchy (correct dependency direction):**
```
✅ Presentation depends on Application
✅ Application depends on Domain
✅ Infrastructure depends on Domain
❌ Presentation depends on Infrastructure (violates this!)
❌ Application depends on Presentation (violates this!)
```

**Example Test:**
```python
def test_api_routes_do_not_import_database_models_directly():
    """Routes should not contain 'TableReservationDB'."""
    source = inspect.getsource(reservation_routes)
    assert "TableReservationDB" not in source
```

---

## Running the Tests

### Run all reservation tests:
```bash
pytest boardgame_cafe/tests/reservations/ -v
```

### Run only unit tests:
```bash
pytest boardgame_cafe/tests/reservations/unit/ -v
```

### Run only integration tests:
```bash
pytest boardgame_cafe/tests/reservations/integration/ -v
```

### Run a specific test file:
```bash
pytest boardgame_cafe/tests/reservations/integration/api/test_api_authorization.py -v
```

### Run a specific test:
```bash
pytest boardgame_cafe/tests/reservations/unit/domain/test_reservation.py::test_reservation_rejects_negative_party_size -v
```

### Run with coverage:
```bash
pytest boardgame_cafe/tests/reservations/ --cov=features.reservations --cov-report=html
```

---

## Test Philosophy

### 1. **TDD (Test-Driven Design)**
Tests define the **contract** - what code SHOULD do. Implementation follows tests.

### 2. **Boundary-Enforcing**
Tests catch architectural violations early:
- "You tried to import the database model in the API route" → Test fails
- "You created a partial state during booking failure" → Test fails
- "You stored data with an invalid status" → Test fails

### 3. **Clear Intent**
Each test has:
- **REQUIREMENT comment**: What rule is being enforced
- **Example**: Clear setup/act/assert
- **Error message**: What goes wrong if violated

### 4. **Orthogonal Concerns**
Tests focus on ONE concern per class:
- `TestDomainModelIntegrity`: Only domain invariants
- `TestAuthorizationBoundaries`: Only authorization rules
- `TestRepositoryAbstraction`: Only dependency inversion
- (Not all mixed together)

---

## Common Patterns In Tests

### Pattern 1: Invariant Testing
```python
def test_domain_rejects_invalid_input():
    with pytest.raises(ValidationError) as exc:
        TableReservation(invalid_field=-1)
    assert "field_name" in str(exc.value).lower()
```

### Pattern 2: Boundary Testing
```python
def test_api_endpoint_requires_authentication():
    fake_user = FakeCurrentUser(is_authenticated=False)
    with patch('current_user', fake_user):
        response = client.get("/api/endpoint")
        assert response.status_code == 401
```

### Pattern 3: Contract Testing
```python
def test_use_case_works_with_any_repository_implementation():
    fake_repo = FakeReservationRepository()
    use_case = CreateReservationUseCase(fake_repo)
    # Use case should work identically with any implementation
```

### Pattern 4: Atomicity Testing
```python
def test_operation_succeeds_completely_or_fails_completely():
    initial_state = capture_state()
    try:
        operation_that_might_fail()
    except:
        pass
    final_state = capture_state()
    assert initial_state == final_state or success_recorded
```

---

## What's NOT in These Tests

❌ **UI/HTML rendering** (that's for frontend tests)  
❌ **HTTP status code exhaustiveness** (a few key ones suffice)  
❌ **Performance benchmarks** (use separate perf tests)  
❌ **External API mocking** (use separate contract tests)  

**Why?** Tests should focus on **architecture and business rules**, not implementation details.

---

## Future: E2E Tests

The `e2e/test_booking_flow.py` file is ready for end-to-end workflow tests:
```python
def test_complete_booking_workflow():
    # 1. User signs up
    # 2. User books a table
    # 3. User adds games
    # 4. User pays
    # 5. Reservation confirmed
    # All from API perspective
```

---

## Summary

✅ **Domain tests**: Invariants & state machines  
✅ **Application tests**: Use case orchestration  
✅ **API tests**: Authorization, business rules, auto-assignment logic  
✅ **Infrastructure tests**: Repository pattern, transaction atomicity  
✅ **Architecture tests**: Layer separation, dependency direction  

**The result:** A codebase where **violating architectural rules is caught by tests**, not code review.
