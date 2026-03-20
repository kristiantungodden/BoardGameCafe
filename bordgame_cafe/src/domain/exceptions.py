"""
Domain exceptions.

Custom exceptions for domain-level errors.
"""


class DomainException(Exception):
    """Base exception for domain errors."""
    pass


class UserException(DomainException):
    """Base exception for user-related errors."""
    pass


class UserAlreadyExists(UserException):
    """User with this email already exists."""
    pass


class UserNotFound(UserException):
    """User not found."""
    pass


class InvalidPassword(UserException):
    """Invalid password."""
    pass


class GameException(DomainException):
    """Base exception for game-related errors."""
    pass


class GameNotFound(GameException):
    """Game not found."""
    pass


class GameCopyException(DomainException):
    """Base exception for game copy-related errors."""
    pass


class GameCopyNotFound(GameCopyException):
    """Game copy not found."""
    pass


class InvalidGameCopyStatus(GameCopyException):
    """Invalid game copy status transition."""
    pass


class TableException(DomainException):
    """Base exception for table-related errors."""
    pass


class TableNotFound(TableException):
    """Table not found."""
    pass


class TableUnavailable(TableException):
    """Table is not available for reservation."""
    pass


class ReservationException(DomainException):
    """Base exception for reservation-related errors."""
    pass


class ReservationNotFound(ReservationException):
    """Reservation not found."""
    pass


class InvalidReservationStatus(ReservationException):
    """Invalid reservation status transition."""
    pass


class PartyTooLarge(ReservationException):
    """Party size exceeds table capacity."""
    pass


class OverlappingReservation(ReservationException):
    """Reservation overlaps with existing reservation."""
    pass


class PaymentException(DomainException):
    """Base exception for payment-related errors."""
    pass


class InvalidPaymentStatus(PaymentException):
    """Invalid payment status."""
    pass


class PaymentProcessingError(PaymentException):
    """Error processing payment."""
    pass


class AuthenticationException(DomainException):
    """Authentication related error."""
    pass


class AuthorizationException(DomainException):
    """Authorization related error."""
    pass
