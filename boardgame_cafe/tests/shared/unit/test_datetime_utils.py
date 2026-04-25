from datetime import datetime, timezone

from shared.domain.datetime_utils import format_utc_iso, to_app_local, to_utc_naive


def test_to_utc_naive_converts_aware_timestamp_to_naive_utc():
    aware = datetime(2099, 3, 30, 9, 0, tzinfo=timezone.utc)

    normalized = to_utc_naive(aware)

    assert normalized.tzinfo is None
    assert normalized == datetime(2099, 3, 30, 9, 0)


def test_to_app_local_converts_utc_to_oslo_time():
    utc_ts = datetime(2099, 3, 30, 7, 0, tzinfo=timezone.utc)

    local_ts = to_app_local(utc_ts)

    assert local_ts.hour in (8, 9)
    assert local_ts.tzinfo is not None


def test_format_utc_iso_uses_z_suffix():
    aware = datetime(2099, 3, 30, 7, 0, tzinfo=timezone.utc)

    assert format_utc_iso(aware) == "2099-03-30T07:00:00Z"
