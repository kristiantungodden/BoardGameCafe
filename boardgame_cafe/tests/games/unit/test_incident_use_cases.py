from datetime import datetime, timezone

from features.games.application.use_cases.incident_use_cases import ReportIncidentUseCase, DeleteIncidentUseCase
from features.games.domain.models.incident import Incident
from types import SimpleNamespace


class FakeGameCopy:
    def __init__(self):
        self.status = 'available'
        self.condition_note = ''
        self.maintenance_sent = False

    def send_to_maintenance(self):
        if self.status == 'maintenance':
            raise Exception('Already in maintenance')
        self.status = 'maintenance'
        self.maintenance_sent = True

    def update_condition_note(self, note):
        self.condition_note = note


class FakeGameCopyRepo:
    def __init__(self, copies):
        self.copies = {c_id: FakeGameCopy() for c_id in copies}

    def get_by_id(self, copy_id):
        return self.copies.get(copy_id)

    def update(self, game_copy):
        # noop for fake
        return game_copy


class FakeIncidentRepo:
    def __init__(self):
        self.store = {}
        self.next_id = 1

    def add(self, incident: Incident):
        domain = SimpleNamespace(
            id=self.next_id,
            game_copy_id=incident.game_copy_id,
            reported_by=incident.reported_by,
            incident_type=incident.incident_type,
            note=incident.note,
            created_at=datetime.now(timezone.utc),
        )
        self.store[self.next_id] = domain
        self.next_id += 1
        return domain

    def get_by_id(self, incident_id):
        return self.store.get(incident_id)

    def list_for_game_copy(self, game_copy_id):
        return [v for v in self.store.values() if v.game_copy_id == game_copy_id]

    def delete(self, incident_id):
        if incident_id not in self.store:
            return False
        del self.store[incident_id]
        return True


class FakeEventBus:
    def __init__(self):
        self.published = []

    def publish(self, event):
        self.published.append(event)


def test_report_incident_publishes_event():
    game_copy_repo = FakeGameCopyRepo(copies=[1])
    incident_repo = FakeIncidentRepo()
    bus = FakeEventBus()

    uc = ReportIncidentUseCase(incident_repo=incident_repo, game_copy_repo=game_copy_repo, event_bus=bus)

    domain_incident = uc.execute(game_copy_id=1, steward_id=10, incident_type='damage', note='Broken corner')

    assert domain_incident.id is not None
    assert domain_incident.incident_type == 'damage'
    assert len(bus.published) == 1
    evt = bus.published[0]
    assert getattr(evt, 'incident_id', None) == domain_incident.id
    assert getattr(evt, 'game_copy_id', None) == domain_incident.game_copy_id


def test_delete_incident_publishes_event():
    game_copy_repo = FakeGameCopyRepo(copies=[1])
    incident_repo = FakeIncidentRepo()
    bus = FakeEventBus()

    # Pre-seed an incident
    inc = incident_repo.add(Incident(game_copy_id=1, reported_by=5, incident_type='damage', note='x'))

    uc = DeleteIncidentUseCase(incident_repo=incident_repo, event_bus=bus)
    ok = uc.execute(inc.id)
    assert ok
    assert len(bus.published) == 1
    assert getattr(bus.published[0], 'incident_id', None) == inc.id
