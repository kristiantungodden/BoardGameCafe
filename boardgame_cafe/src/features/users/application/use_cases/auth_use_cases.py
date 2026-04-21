# auth_use_cases.py
from dataclasses import dataclass
from features.users.application.interfaces import UserRepositoryInterface, AuthSessionPortInterface, PasswordHasherInterface
from features.users.domain.models.user import User, Role
from shared.domain.exceptions import ValidationError

@dataclass
class RegisterCommand:
    name: str
    email: str
    password: str
    role: str = "customer"
    phone: str | None = None

class RegisterUseCase:
    def __init__(self, users: UserRepositoryInterface, hasher: PasswordHasherInterface):
        self.users = users
        self.hasher = hasher

    def execute(self, cmd: RegisterCommand) -> User:
        if self.users.get_by_email(cmd.email):
            raise ValidationError("email already exists")
        user = User(
            name=cmd.name,
            email=cmd.email,
            password_hash=self.hasher.hash(cmd.password),
            role=Role(cmd.role),
            phone=cmd.phone,
        )
        return self.users.save(user)

@dataclass
class LoginCommand:
    email: str
    password: str

class LoginUseCase:
    def __init__(self, users: UserRepositoryInterface, hasher: PasswordHasherInterface, session: AuthSessionPortInterface):
        self.users = users
        self.hasher = hasher
        self.session = session

    def execute(self, cmd: LoginCommand) -> User:
        user = self.users.get_by_email(cmd.email)
        if not user or not self.hasher.verify(user.password_hash, cmd.password):
            raise ValidationError("Invalid credentials")
        if bool(getattr(user, "is_suspended", False)):
            raise ValidationError("Account suspended")
        self.session.login(user.id)  # adapter handles flask-login user object lookup
        return user