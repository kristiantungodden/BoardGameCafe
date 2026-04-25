from unittest.mock import MagicMock, patch

from shared.infrastructure.email.flask_mail_service import FlaskMailService


@patch("shared.infrastructure.email.flask_mail_service.Message")
def test_send_email_supports_inline_attachments(mock_message_cls):
    mock_msg = MagicMock()
    mock_message_cls.return_value = mock_msg

    mock_mail = MagicMock()
    service = FlaskMailService(mock_mail)

    service.send_email(
        subject="Reservation confirmation",
        sender=None,
        recipients=["user@example.com"],
        body="Plain text",
        html="<p>HTML</p>",
        inline_attachments=[
            (
                "reservation-52-checkin-qr.svg",
                "image/svg+xml",
                b"<svg></svg>",
                "reservation-52-checkin-qr",
            )
        ],
    )

    mock_message_cls.assert_called_once_with(
        "Reservation confirmation",
        sender=None,
        recipients=["user@example.com"],
    )
    mock_msg.attach.assert_called_once_with(
        filename="reservation-52-checkin-qr.svg",
        content_type="image/svg+xml",
        data=b"<svg></svg>",
        disposition="inline",
        headers=[
            ("Content-ID", "<reservation-52-checkin-qr>"),
            ("X-Attachment-Id", "reservation-52-checkin-qr"),
        ],
    )
    mock_mail.send.assert_called_once_with(mock_msg)
