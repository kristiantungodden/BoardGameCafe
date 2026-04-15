"""Tests for realtime event pub/sub functionality."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
import json
from flask import Flask

from shared.infrastructure.message_bus.realtime import (
    get_redis_client,
    publish_realtime_event,
    stream_realtime_events,
)


@pytest.fixture
def app():
    """Create a test Flask app with app context."""
    app = Flask(__name__)
    app.config["REDIS_URL"] = "redis://localhost:6379/2"
    app.config["REALTIME_EVENTS_CHANNEL"] = "boardgame_cafe.events"
    return app


@pytest.fixture
def app_context(app):
    """Provide an app context for tests that need current_app."""
    with app.app_context():
        yield app


class TestGetRedisClient:
    """Test Redis client initialization."""

    @patch("shared.infrastructure.message_bus.realtime.redis")
    def test_get_redis_client_from_url(self, mock_redis_module):
        """Should create Redis client from provided URL."""
        mock_client = Mock()
        mock_redis_module.Redis.from_url.return_value = mock_client

        client = get_redis_client("redis://custom-redis:6379/0")

        mock_redis_module.Redis.from_url.assert_called_once_with(
            "redis://custom-redis:6379/0",
            decode_responses=True
        )
        assert client == mock_client

    @patch("shared.infrastructure.message_bus.realtime.redis")
    def test_get_redis_client_from_config(self, mock_redis_module, app_context):
        """Should use REDIS_URL from app config when no URL provided."""
        mock_client = Mock()
        mock_redis_module.Redis.from_url.return_value = mock_client

        client = get_redis_client()

        mock_redis_module.Redis.from_url.assert_called_once_with(
            "redis://localhost:6379/2",
            decode_responses=True
        )
        assert client == mock_client

    def test_get_redis_client_raises_when_redis_not_installed(self):
        """Should raise RuntimeError if redis module not available."""
        with patch("shared.infrastructure.message_bus.realtime.redis", None):
            with pytest.raises(RuntimeError) as exc_info:
                get_redis_client()

            assert "Redis client not installed" in str(exc_info.value)
            assert "redis" in str(exc_info.value)


class TestPublishRealtimeEvent:
    """Test publishing events to Redis pub/sub."""

    @patch("shared.infrastructure.message_bus.realtime.get_redis_client")
    def test_publish_realtime_event_sends_to_redis(self, mock_get_client, app_context):
        """Should publish event payload to Redis channel."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        payload = {
            "event_type": "UserRegistered",
            "event_module": "shared.domain.events.user_registered",
            "data": {"user_id": 123, "email": "user@example.com"}
        }

        publish_realtime_event(payload)

        # Verify Redis.publish was called with channel and JSON payload
        mock_client.publish.assert_called_once()
        call_args = mock_client.publish.call_args
        assert call_args[0][0] == "boardgame_cafe.events"
        
        # Verify payload is JSON serialized
        json_payload = call_args[0][1]
        parsed = json.loads(json_payload)
        assert parsed["event_type"] == "UserRegistered"
        assert parsed["data"]["user_id"] == 123

    @patch("shared.infrastructure.message_bus.realtime.get_redis_client")
    def test_publish_realtime_event_uses_custom_channel(self, mock_get_client, app_context):
        """Should publish to custom channel if provided."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        payload = {"event_type": "UserRegistered", "data": {}}

        publish_realtime_event(payload, channel="custom.channel")

        call_args = mock_client.publish.call_args
        assert call_args[0][0] == "custom.channel"

    @patch("shared.infrastructure.message_bus.realtime.get_redis_client")
    def test_publish_realtime_event_handles_non_json_serializable_values(
        self, mock_get_client, app_context
    ):
        """Should handle non-JSON-serializable values with str() conversion."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        from datetime import datetime, date
        
        payload = {
            "event_type": "TestEvent",
            "data": {
                "timestamp": datetime(2026, 4, 15, 10, 30, 45),
                "date": date(2026, 4, 15),
                "message": "test"
            }
        }

        publish_realtime_event(payload)

        # Should not raise - datetime/date are handled by default=str in json.dumps
        mock_client.publish.assert_called_once()
        json_payload = mock_client.publish.call_args[0][1]
        # Just verify it's valid JSON
        parsed = json.loads(json_payload)
        assert "timestamp" in str(parsed)

    @patch("shared.infrastructure.message_bus.realtime.get_redis_client")
    def test_publish_realtime_event_propagates_redis_errors(self, mock_get_client, app_context):
        """Should propagate Redis connection errors."""
        mock_client = Mock()
        mock_client.publish.side_effect = RuntimeError("Connection refused")
        mock_get_client.return_value = mock_client

        payload = {"event_type": "TestEvent", "data": {}}

        with pytest.raises(RuntimeError) as exc_info:
            publish_realtime_event(payload)

        assert "Connection refused" in str(exc_info.value)


class TestStreamRealtimeEvents:
    """Test streaming realtime events via SSE."""

    @patch("shared.infrastructure.message_bus.realtime.get_redis_client")
    def test_stream_realtime_events_yields_ready_event(self, mock_get_client, app_context):
        """Should yield a ready event first to signal connection."""
        mock_client = Mock()
        mock_pubsub = Mock()
        mock_client.pubsub.return_value = mock_pubsub
        mock_pubsub.listen.return_value = iter([])  # No messages
        mock_get_client.return_value = mock_client

        stream = stream_realtime_events()
        first_event = next(stream)

        assert "ready" in first_event
        assert "connected" in first_event

    @patch("shared.infrastructure.message_bus.realtime.get_redis_client")
    def test_stream_realtime_events_yields_domain_events(self, mock_get_client, app_context):
        """Should yield domain_event SSE messages from Redis pub/sub."""
        mock_client = Mock()
        mock_pubsub = Mock()
        mock_client.pubsub.return_value = mock_pubsub

        # Mock Redis pub/sub messages
        messages = [
            {"type": "subscribe", "channel": "boardgame_cafe.events"},  # subscribe message
            {
                "type": "message",
                "channel": "boardgame_cafe.events",
                "data": '{"event_type": "UserRegistered", "data": {"user_id": 123}}'
            },
            {
                "type": "message",
                "channel": "boardgame_cafe.events",
                "data": '{"event_type": "ReservationCreated", "data": {"reservation_id": 456}}'
            }
        ]
        mock_pubsub.listen.return_value = iter(messages)
        mock_get_client.return_value = mock_client

        stream = stream_realtime_events()
        
        # Skip ready event
        next(stream)
        
        # Get domain events
        event1 = next(stream)
        event2 = next(stream)

        assert "domain_event" in event1
        assert "UserRegistered" in event1
        
        assert "domain_event" in event2
        assert "ReservationCreated" in event2

    @patch("shared.infrastructure.message_bus.realtime.get_redis_client")
    def test_stream_realtime_events_ignores_non_message_types(self, mock_get_client, app_context):
        """Should ignore subscribe/unsubscribe messages from Redis pub/sub."""
        mock_client = Mock()
        mock_pubsub = Mock()
        mock_client.pubsub.return_value = mock_pubsub

        # Mock messages with various types
        messages = [
            {"type": "subscribe", "channel": "boardgame_cafe.events"},
            {
                "type": "message",
                "channel": "boardgame_cafe.events",
                "data": '{"event_type": "UserRegistered"}'
            },
            {"type": "unsubscribe", "channel": "boardgame_cafe.events"}
        ]
        mock_pubsub.listen.return_value = iter(messages)
        mock_get_client.return_value = mock_client

        stream = stream_realtime_events()
        
        # Skip ready event
        next(stream)
        
        # Should get exactly one domain event
        event = next(stream)
        assert "domain_event" in event

        # Next iteration should raise StopIteration (no more events)
        with pytest.raises(StopIteration):
            next(stream)

    @patch("shared.infrastructure.message_bus.realtime.get_redis_client")
    def test_stream_realtime_events_subscribes_to_config_channel(
        self, mock_get_client, app_context
    ):
        """Should subscribe to REALTIME_EVENTS_CHANNEL from app config."""
        mock_client = Mock()
        mock_pubsub = Mock()
        mock_client.pubsub.return_value = mock_pubsub
        mock_pubsub.listen.return_value = iter([])
        mock_get_client.return_value = mock_client

        stream = stream_realtime_events()
        next(stream)  # Start consuming

        mock_pubsub.subscribe.assert_called_once_with("boardgame_cafe.events")

    @patch("shared.infrastructure.message_bus.realtime.get_redis_client")
    def test_stream_realtime_events_subscribes_to_custom_channel(
        self, mock_get_client, app_context
    ):
        """Should subscribe to custom channel if provided."""
        mock_client = Mock()
        mock_pubsub = Mock()
        mock_client.pubsub.return_value = mock_pubsub
        mock_pubsub.listen.return_value = iter([])
        mock_get_client.return_value = mock_client

        stream = stream_realtime_events(channel="special.events")
        next(stream)  # Start consuming

        mock_pubsub.subscribe.assert_called_once_with("special.events")

    @patch("shared.infrastructure.message_bus.realtime.get_redis_client")
    def test_stream_realtime_events_closes_pubsub_on_error(self, mock_get_client, app_context):
        """Should close pubsub on any exception."""
        mock_client = Mock()
        mock_pubsub = Mock()
        mock_client.pubsub.return_value = mock_pubsub

        # Simulate Redis connection error during listen
        def listen_with_error():
            yield {"type": "subscribe", "channel": "boardgame_cafe.events"}
            raise RuntimeError("Connection lost")

        mock_pubsub.listen.return_value = listen_with_error()
        mock_get_client.return_value = mock_client

        stream = stream_realtime_events()
        next(stream)  # Get ready event

        # Consuming next event should raise RuntimeError
        with pytest.raises(RuntimeError):
            next(stream)

        # But pubsub should be closed
        mock_pubsub.close.assert_called_once()

    @patch("shared.infrastructure.message_bus.realtime.get_redis_client")
    def test_stream_realtime_events_closes_pubsub_on_normal_completion(
        self, mock_get_client, app_context
    ):
        """Should close pubsub when stream completes normally."""
        mock_client = Mock()
        mock_pubsub = Mock()
        mock_client.pubsub.return_value = mock_pubsub
        mock_pubsub.listen.return_value = iter([])  # Empty stream
        mock_get_client.return_value = mock_client

        stream = stream_realtime_events()
        next(stream)  # Get ready event

        # Next iteration should raise StopIteration and close
        with pytest.raises(StopIteration):
            next(stream)

        mock_pubsub.close.assert_called_once()

    @patch("shared.infrastructure.message_bus.realtime.get_redis_client")
    def test_stream_realtime_events_formats_sse_correctly(self, mock_get_client, app_context):
        """SSE messages should be formatted with proper event and data fields."""
        mock_client = Mock()
        mock_pubsub = Mock()
        mock_client.pubsub.return_value = mock_pubsub

        messages = [
            {"type": "subscribe", "channel": "boardgame_cafe.events"},
            {
                "type": "message",
                "channel": "boardgame_cafe.events",
                "data": '{"event_type": "TestEvent", "data": {}}'
            }
        ]
        mock_pubsub.listen.return_value = iter(messages)
        mock_get_client.return_value = mock_client

        stream = stream_realtime_events()
        next(stream)  # Skip ready
        domain_event = next(stream)

        # Should contain SSE format: event: domain_event\ndata: {...}\n\n
        assert "event: domain_event" in domain_event
        assert "data:" in domain_event
        assert domain_event.endswith("\n\n")
