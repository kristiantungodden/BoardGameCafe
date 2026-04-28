from types import SimpleNamespace
import pytest

from shared.application.event_handlers import realtime_event_handler
from shared.domain.events import IncidentReported, IncidentDeleted


class FakeBus:
    def __init__(self):
        self.handlers = {}

    def subscribe(self, event_type, handler):
        self.handlers[event_type] = handler


def test_realtime_handler_registers_and_publishes(monkeypatch):
    bus = FakeBus()

    published = []

    def fake_publish(payload):
        published.append(payload)

    monkeypatch.setattr('shared.application.event_handlers.realtime_event_handler.publish_realtime_event', fake_publish)

    # Register handlers
    realtime_event_handler.register_realtime_event_handlers(bus)

    # Ensure the incident handlers are registered
    assert IncidentReported in bus.handlers
    assert IncidentDeleted in bus.handlers

    # Call the registered handler for reported
    evt = IncidentReported(incident_id=123, game_copy_id=10, reported_by=5, incident_type='damage', note='x', created_at='2020-01-01T00:00:00')
    bus.handlers[IncidentReported](evt)

    assert len(published) == 1
    assert published[0]['event_type'] == 'incident.created'
    assert published[0]['data']['id'] == 123

    # Call the registered handler for deleted
    bus.handlers[IncidentDeleted](SimpleNamespace(incident_id=123))
    # The delete handler should have been called and appended another payload
    assert any(p['event_type'] == 'incident.deleted' for p in published)
