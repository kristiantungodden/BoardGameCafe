"""Authentication API endpoints."""

from flask import Blueprint, request, jsonify
from pydantic import ValidationError, EmailStr
from sqlalchemy.orm import Session
from infrastructure.database import SessionLocal
from application.use_cases.user_use_cases import LoginUseCase, RegisterCustomerUseCase, LoginRequest, RegisterCustomerRequest
from domain.exceptions import UserAlreadyExists, UserNotFound, InvalidPassword
from infrastructure.repositories import SQLAlchemyUserRepository

auth_bp = Blueprint("auth", __name__)


def get_user_repository() -> SQLAlchemyUserRepository:
    """Get user repository with session."""
    db = SessionLocal()
    return SQLAlchemyUserRepository(db)


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new customer account.
    
    JSON body:
    - email: Email address (must be unique)
    - full_name: Customer's full name
    - phone: Phone number (optional)
    - password: Account password
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body is empty"}), 400
        
        user_repo = get_user_repository()
        use_case = RegisterCustomerUseCase(user_repo)
        
        register_request = RegisterCustomerRequest(
            email=data.get("email"),
            full_name=data.get("full_name"),
            phone=data.get("phone", ""),
            password=data.get("password"),
        )
        
        result = use_case.execute(register_request)
        return jsonify(result.dict()), 201
        
    except UserAlreadyExists as e:
        return jsonify({"error": str(e)}), 409
    except ValidationError as e:
        return jsonify({"error": "Invalid input", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Login with email and password.
    
    JSON body:
    - email: Email address
    - password: Account password
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body is empty"}), 400
        
        user_repo = get_user_repository()
        use_case = LoginUseCase(user_repo)
        
        login_request = LoginRequest(
            email=data.get("email"),
            password=data.get("password"),
        )
        
        result = use_case.execute(login_request)
        # TODO: Generate JWT token
        return jsonify({
            "access_token": "token",
            "token_type": "bearer",
            "user": result.dict()
        }), 200
        
    except UserNotFound as e:
        return jsonify({"error": str(e)}), 404
    except InvalidPassword as e:
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Logout the current user."""
    # TODO: Implement logout logic with session/JWT revocation
    return jsonify({"message": "Logged out successfully"}), 200
