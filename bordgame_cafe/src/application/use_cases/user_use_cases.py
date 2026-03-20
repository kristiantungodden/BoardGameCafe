"""User-related use cases."""

from typing import Optional
from pydantic import BaseModel, EmailStr
from domain.models import User, UserRole
from domain.exceptions import UserAlreadyExists, UserNotFound, InvalidPassword


class RegisterCustomerRequest(BaseModel):
    """Request for registering a new customer."""
    
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    password: str


class RegisterCustomerUseCase:
    """Use case for registering a new customer."""
    
    def __init__(self, user_repository) -> None:
        self.user_repository = user_repository
    
    async def execute(self, request: RegisterCustomerRequest) -> User:
        """
        Register a new customer.
        
        Args:
            request: Registration request with user details
            
        Returns:
            Created user
            
        Raises:
            UserAlreadyExists: If user with email already exists
        """
        # Check if user already exists
        existing_user = await self.user_repository.get_by_email(request.email)
        if existing_user:
            raise UserAlreadyExists(f"User with email {request.email} already exists")
        
        # Create new user (password hashing should be done in repository or service)
        user = User(
            email=request.email,
            full_name=request.full_name,
            phone=request.phone,
            password_hash=request.password,  # TODO: hash password
            role=UserRole.CUSTOMER,
            is_active=True,
        )
        
        await self.user_repository.add(user)
        return user


class LoginRequest(BaseModel):
    """Request for user login."""
    
    email: EmailStr
    password: str


class LoginUseCase:
    """Use case for user login."""
    
    def __init__(self, user_repository) -> None:
        self.user_repository = user_repository
    
    async def execute(self, request: LoginRequest) -> User:
        """
        Authenticate user.
        
        Args:
            request: Login credentials
            
        Returns:
            Authenticated user
            
        Raises:
            UserNotFound: If user doesn't exist
            InvalidPassword: If password is incorrect
        """
        user = await self.user_repository.get_by_email(request.email)
        if not user:
            raise UserNotFound(f"User with email {request.email} not found")
        
        # TODO: verify password against hash
        # if not verify_password(request.password, user.password_hash):
        #     raise InvalidPassword("Invalid password")
        
        return user
