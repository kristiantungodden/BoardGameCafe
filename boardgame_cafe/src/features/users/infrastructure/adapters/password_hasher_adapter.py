from features.users.application.interfaces import PasswordHasherInterface
from features.users.infrastructure.database.security_db import hash_password, verify_password


class WerkzeugPasswordHasher(PasswordHasherInterface):
    def hash(self, password: str) -> str:
        return hash_password(password)

    def verify(self, hashed: str, password: str) -> bool:
        return verify_password(hashed, password)