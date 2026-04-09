#Her skal interfacet for email være.
from abc import ABC, abstractmethod

class EmailServiceInterface(ABC):
    @abstractmethod
    def send_welcome_email(self, recipient_email: str) -> None:
        pass
    @abstractmethod
    def send_reservation_confirmation_email(self, recipient_email: str, reservation_details: str) -> None:
        pass
    @abstractmethod
    def send_reservation_reminder_email(self, recipient_email: str, reservation_details: str) -> None:
        pass
    @abstractmethod
    def send_reservation_cancellation_email(self, recipient_email: str, reservation_details: str) -> None:
        pass
    @abstractmethod
    def send_password_reset_email(self, recipient_email: str, reset_link: str) -> None:
        pass