import sys
import types
from dataclasses import dataclass

import pytest


@dataclass
class FakeTableReservation:
    id: int | None
    party_size: int


@pytest.fixture(autouse=True)
def stub_reservation_module(monkeypatch):
    """Provide a lightweight reservation module so payment imports work in isolation."""
    features_pkg = sys.modules.get("features") or types.ModuleType("features")
    reservations_pkg = sys.modules.get("features.reservations") or types.ModuleType(
        "features.reservations"
    )
    domain_pkg = sys.modules.get(
        "features.reservations.domain"
    ) or types.ModuleType("features.reservations.domain")
    models_pkg = sys.modules.get(
        "features.reservations.domain.models"
    ) or types.ModuleType("features.reservations.domain.models")
    reservation_module = types.ModuleType(
        "features.reservations.domain.models.reservation"
    )
    reservation_module.TableReservation = FakeTableReservation

    monkeypatch.setitem(sys.modules, "features", features_pkg)
    monkeypatch.setitem(sys.modules, "features.reservations", reservations_pkg)
    monkeypatch.setitem(sys.modules, "features.reservations.domain", domain_pkg)
    monkeypatch.setitem(sys.modules, "features.reservations.domain.models", models_pkg)
    monkeypatch.setitem(
        sys.modules,
        "features.reservations.domain.models.reservation",
        reservation_module,
    )
    yield
