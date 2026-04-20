def _register_and_login_staff(client, email="steward@example.com"):
    staff_payload = {
        "name": "Steward",
        "email": email,
        "password": "password123",
        "role": "staff",
    }
    reg = client.post("/api/auth/register", json=staff_payload)
    assert reg.status_code == 201

    login = client.post(
        "/api/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert login.status_code == 200


def test_creating_incident_triggers_realtime_publish(client, app, monkeypatch, test_data):
    # monkeypatch the infra realtime publish to capture calls
    published = []

    def fake_publish(payload):
        published.append(payload)

    monkeypatch.setattr('shared.infrastructure.message_bus.realtime.publish_realtime_event', fake_publish)

    copy_id = test_data['copies'][0]['id']

    _register_and_login_staff(client)

    resp = client.post(f"/api/steward/game-copies/{copy_id}/incidents", json={"incident_type": "damage", "note": "broken"})
    assert resp.status_code == 201

    # the realtime handler should publish an incident.created payload
    assert any(p['event_type'] == 'incident.created' for p in published)


def test_deleting_incident_triggers_realtime_publish(client, app, monkeypatch, test_data):
    published = []

    def fake_publish(payload):
        published.append(payload)

    monkeypatch.setattr('shared.infrastructure.message_bus.realtime.publish_realtime_event', fake_publish)

    copy_id = test_data['copies'][0]['id']

    _register_and_login_staff(client)

    # create an incident
    rep = client.post(f"/api/steward/game-copies/{copy_id}/incidents", json={"incident_type": "damage", "note": "broken"})
    assert rep.status_code == 201
    inc = rep.get_json()

    # delete it
    d = client.delete(f"/api/steward/incidents/{inc['id']}")
    assert d.status_code == 204

    assert any(p['event_type'] == 'incident.deleted' for p in published)
