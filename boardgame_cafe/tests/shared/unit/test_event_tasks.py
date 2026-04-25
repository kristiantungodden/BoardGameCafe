"""Tests for Celery task implementations."""
import pytest
from unittest.mock import Mock, patch
from shared.infrastructure.message_bus.event_tasks import (
    send_welcome_email,
    send_reservation_confirmation_email,
    publish_realtime_event_task,
)


class TestSendWelcomeEmailTask:
    """Test send_welcome_email Celery task."""

    @patch("shared.infrastructure.message_bus.event_tasks.FlaskMailService")
    def test_send_welcome_email_extracts_email_and_calls_service(self, mock_mail_service):
        """Task should extract email from payload and call FlaskMailService."""
        mock_service_instance = Mock()
        mock_mail_service.return_value = mock_service_instance

        event_payload = {
            "event_type": "UserRegistered",
            "event_module": "shared.domain.events.user_registered",
            "data": {
                "user_id": 123,
                "email": "newuser@example.com"
            }
        }

        send_welcome_email(event_payload)

        mock_mail_service.assert_called_once()
        mock_service_instance.send_email.assert_called_once_with(
            subject="Welcome to Dicer.no!",
            sender=None,
            recipients=["newuser@example.com"],
            body="Thank you for signing up at Dicer.no! \n\nWe are excited to have you as part of our community. Stay tuned for updates on events, new games, and special offers!",
        )

    @patch("shared.infrastructure.message_bus.event_tasks.FlaskMailService")
    def test_send_welcome_email_handles_missing_email(self, mock_mail_service):
        """Task should silently skip if email is missing."""
        mock_service_instance = Mock()
        mock_mail_service.return_value = mock_service_instance

        event_payload = {
            "event_type": "UserRegistered",
            "event_module": "shared.domain.events.user_registered",
            "data": {
                "user_id": 123
                # missing email
            }
        }

        send_welcome_email(event_payload)

        # Should not call send method
        mock_service_instance.send_email.assert_not_called()

    @patch("shared.infrastructure.message_bus.event_tasks.FlaskMailService")
    def test_send_welcome_email_handles_missing_data_field(self, mock_mail_service):
        """Task should handle payload with missing data field."""
        mock_service_instance = Mock()
        mock_mail_service.return_value = mock_service_instance

        event_payload = {
            "event_type": "UserRegistered",
            "event_module": "shared.domain.events.user_registered"
            # missing data field
        }

        send_welcome_email(event_payload)

        mock_service_instance.send_email.assert_not_called()

    @patch("shared.infrastructure.message_bus.event_tasks.FlaskMailService")
    def test_send_welcome_email_handles_none_email(self, mock_mail_service):
        """Task should skip if email is None."""
        mock_service_instance = Mock()
        mock_mail_service.return_value = mock_service_instance

        # Test with None - should not call
        event_payload = {
            "event_type": "UserRegistered",
            "event_module": "shared.domain.events.user_registered",
            "data": {"user_id": 123, "email": None}
        }

        send_welcome_email(event_payload)
        mock_service_instance.send_email.assert_not_called()

        # Reset and test with empty string - should not call
        mock_service_instance.reset_mock()
        event_payload["data"]["email"] = ""
        send_welcome_email(event_payload)
        mock_service_instance.send_email.assert_not_called()


class TestSendReservationConfirmationEmailTask:
    """Test send_reservation_confirmation_email Celery task."""

    @patch("shared.infrastructure.message_bus.event_tasks.FlaskMailService")
    def test_send_reservation_confirmation_extracts_email_and_details(self, mock_mail_service):
        """Task should extract email and details from payload."""
        mock_service_instance = Mock()
        mock_mail_service.return_value = mock_service_instance

        event_payload = {
            "event_type": "ReservationPaymentCompleted",
            "event_module": "shared.domain.events.reservation_payment_completed",
            "data": {
                "reservation_id": 456,
                "user_id": 123,
                "user_email": "user@example.com",
                "table_numbers": [2],
                "start_ts": "2026-04-17T17:00:00",
                "end_ts": "2026-04-17T19:00:00",
                "party_size": 4,
            }
        }

        send_reservation_confirmation_email(event_payload)

        mock_mail_service.assert_called_once()
        mock_service_instance.send_email.assert_called_once()
        send_kwargs = mock_service_instance.send_email.call_args.kwargs
        assert send_kwargs["subject"] == "Your Dicer.no Reservation Confirmation"
        assert send_kwargs["sender"] is None
        assert send_kwargs["recipients"] == ["user@example.com"]
        assert (
            send_kwargs["body"]
            == "Thank you for your reservation at Dicer.no! \n\n"
            "Here are your reservation details:\n"
            "table_numbers=[2], start_ts=2026-04-17T17:00:00, "
            "end_ts=2026-04-17T19:00:00, party_size=4"
            "\n\nWe look forward to seeing you soon!"
        )
        assert "html" in send_kwargs
        assert "Your Reservation Is Confirmed" in send_kwargs["html"]

    @patch("shared.infrastructure.message_bus.event_tasks.FlaskMailService")
    def test_send_reservation_confirmation_handles_missing_email(self, mock_mail_service):
        """Task should skip if user_email is missing."""
        mock_service_instance = Mock()
        mock_mail_service.return_value = mock_service_instance

        event_payload = {
            "event_type": "ReservationPaymentCompleted",
            "event_module": "shared.domain.events.reservation_payment_completed",
            "data": {
                "reservation_id": 456,
                "user_id": 123,
                # missing user_email
                "table_numbers": [2],
                "start_ts": "2026-04-17T17:00:00",
                "end_ts": "2026-04-17T19:00:00",
                "party_size": 4,
            }
        }

        send_reservation_confirmation_email(event_payload)

        mock_service_instance.send_email.assert_not_called()

    @patch("shared.infrastructure.message_bus.event_tasks.FlaskMailService")
    def test_send_reservation_confirmation_handles_missing_details(self, mock_mail_service):
        """Task should still send email if structured detail fields are missing."""
        mock_service_instance = Mock()
        mock_mail_service.return_value = mock_service_instance

        event_payload = {
            "event_type": "ReservationPaymentCompleted",
            "event_module": "shared.domain.events.reservation_payment_completed",
            "data": {
                "reservation_id": 456,
                "user_id": 123,
                "user_email": "user@example.com"
                # missing structured detail fields
            }
        }

        send_reservation_confirmation_email(event_payload)

        mock_service_instance.send_email.assert_called_once()

    @patch("shared.infrastructure.message_bus.event_tasks.FlaskMailService")
    def test_send_reservation_confirmation_does_not_require_other_fields(
        self, mock_mail_service
    ):
        """Task should work with only user_email."""
        mock_service_instance = Mock()
        mock_mail_service.return_value = mock_service_instance

        # Minimal payload
        event_payload = {
            "event_type": "ReservationPaymentCompleted",
            "event_module": "shared.domain.events.reservation_payment_completed",
            "data": {
                "user_email": "user@example.com",
            }
        }

        send_reservation_confirmation_email(event_payload)

        mock_service_instance.send_email.assert_called_once()


class TestPublishRealtimeEventTask:
    """Test publish_realtime_event_task Celery task."""

    @patch("shared.infrastructure.message_bus.event_tasks.publish_realtime_event")
    def test_publish_realtime_event_calls_publish_function(self, mock_publish):
        """Task should call publish_realtime_event with payload."""
        event_payload = {
            "event_type": "UserRegistered",
            "event_module": "shared.domain.events.user_registered",
            "data": {
                "user_id": 123,
                "email": "newuser@example.com"
            }
        }

        publish_realtime_event_task(event_payload)

        mock_publish.assert_called_once_with(event_payload)

    @patch("shared.infrastructure.message_bus.event_tasks.publish_realtime_event")
    def test_publish_realtime_event_handles_empty_payload(self, mock_publish):
        """Task should handle empty payload gracefully."""
        publish_realtime_event_task({})

        mock_publish.assert_called_once_with({})

    @patch("shared.infrastructure.message_bus.event_tasks.publish_realtime_event")
    def test_publish_realtime_event_passes_through_complete_payload(self, mock_publish):
        """Task should pass through the complete event payload unchanged."""
        event_payload = {
            "event_type": "ReservationPaymentCompleted",
            "event_module": "shared.domain.events.reservation_payment_completed",
            "data": {
                "reservation_id": 456,
                "user_id": 123,
                "user_email": "user@example.com",
                "table_numbers": [2],
                "start_ts": "2026-04-17T17:00:00",
                "end_ts": "2026-04-17T19:00:00",
                "party_size": 4,
            }
        }

        publish_realtime_event_task(event_payload)

        mock_publish.assert_called_once_with(event_payload)
        # Verify the exact payload was passed (not modified)
        called_payload = mock_publish.call_args[0][0]
        assert called_payload == event_payload


class TestTasksErrorHandling:
    """Test error handling in task implementations."""

    @patch("shared.infrastructure.message_bus.event_tasks.FlaskMailService")
    def test_send_welcome_email_handles_service_exception(self, mock_mail_service):
        """Task should handle exceptions from mail service gracefully."""
        mock_mail_service.side_effect = Exception("Mail service unavailable")

        event_payload = {
            "event_type": "UserRegistered",
            "event_module": "shared.domain.events.user_registered",
            "data": {"user_id": 123, "email": "user@example.com"}
        }

        # Should not raise, allowing Celery to handle retry/dead letter
        with pytest.raises(Exception):
            send_welcome_email(event_payload)

    @patch("shared.infrastructure.message_bus.event_tasks.FlaskMailService")
    def test_send_reservation_confirmation_handles_service_exception(self, mock_mail_service):
        """Task should handle exceptions from mail service gracefully."""
        mock_mail_service.side_effect = Exception("Mail service error")

        event_payload = {
            "event_type": "ReservationCreated",
            "event_module": "shared.domain.events.reservation_created",
            "data": {
                "user_email": "user@example.com",
                "table_numbers": [2],
                "start_ts": "2026-04-17T17:00:00",
                "end_ts": "2026-04-17T19:00:00",
                "party_size": 4,
            }
        }

        # Should raise, allowing Celery to handle it
        with pytest.raises(Exception):
            send_reservation_confirmation_email(event_payload)

    @patch("shared.infrastructure.message_bus.event_tasks.publish_realtime_event")
    def test_publish_realtime_event_handles_redis_exception(self, mock_publish):
        """Task should allow redis exceptions to propagate for Celery handling."""
        mock_publish.side_effect = RuntimeError("Redis unavailable")

        event_payload = {
            "event_type": "UserRegistered",
            "event_module": "shared.domain.events.user_registered",
            "data": {"user_id": 123, "email": "user@example.com"}
        }

        # Should raise, allowing Celery retry logic to handle it
        with pytest.raises(RuntimeError):
            publish_realtime_event_task(event_payload)
