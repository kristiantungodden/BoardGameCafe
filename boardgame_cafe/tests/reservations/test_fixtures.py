"""
Shared test utilities and fixtures for the Reservations test suite.

This module contains test doubles and utilities that support testing
but should never be imported by production code.
"""


class FakeCurrentUser:
	"""
	Test double for Flask-Login's current_user.
	
	Allows tests to mock authentication state without needing actual user records.
	This simulates the current_user proxy object injected by Flask-Login.
	"""
	def __init__(self, user_id: int = 1, is_authenticated: bool = True, is_staff: bool = False):
		self.id = user_id
		self.is_authenticated = is_authenticated
		self.is_staff = is_staff
