from abc import ABC, abstractmethod

# Email Service Interface skal kun vite hvordan en mail sendes. Ikke hvordan den bygges!!!
class EmailServiceInterface(ABC):
    @abstractmethod
    def send_email(self, subject: str, sender: str, recipients: list[str], body: str) -> None:
        pass