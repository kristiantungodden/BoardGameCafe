class DomainError(Exception):
	"""Base class for domain-level errors."""


class ValidationError(DomainError):
	"""Raised when entity invariants are violated."""


class InvalidStatusTransition(DomainError):
	"""Raised when a status change is not allowed."""
