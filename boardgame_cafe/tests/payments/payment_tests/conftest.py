import sys
import types
from dataclasses import dataclass

import pytest


@dataclass
class FakeBooking:
    id: int | None
    party_size: int


@pytest.fixture(autouse=True)
def stub_booking_module(monkeypatch):
    """Provide a lightweight booking module so payment imports work in isolation."""
    features_pkg = sys.modules.get("features") or types.ModuleType("features")
    bookings_pkg = sys.modules.get("features.bookings") or types.ModuleType(
        "features.bookings"
    )
    domain_pkg = sys.modules.get(
        "features.bookings.domain"
    ) or types.ModuleType("features.bookings.domain")
    models_pkg = sys.modules.get(
        "features.bookings.domain.models"
    ) or types.ModuleType("features.bookings.domain.models")
    booking_module = types.ModuleType(
        "features.bookings.domain.models.booking"
    )
    booking_module.Booking = FakeBooking

    monkeypatch.setitem(sys.modules, "features", features_pkg)
    monkeypatch.setitem(sys.modules, "features.bookings", bookings_pkg)
    monkeypatch.setitem(sys.modules, "features.bookings.domain", domain_pkg)
    monkeypatch.setitem(sys.modules, "features.bookings.domain.models", models_pkg)
    monkeypatch.setitem(
        sys.modules,
        "features.bookings.domain.models.booking",
        booking_module,
    )
    yield
