from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user

from infrastructure import db, csrf
from infrastructure.database import User, hash_password, verify_password

bp = Blueprint("auth", __name__, url_prefix="/auth")
csrf.exempt(bp)  # Exempt the entire blueprint from CSRF protection for API routes


from presentation.schemas.user import UserCreate, UserResponse


@bp.route('/register', methods=['POST'])
def register():
    try:
        payload = UserCreate(**(request.get_json() or {}))
    except Exception as e:
        return jsonify({'error': str(e)}), 400

    if User.query.filter_by(email=payload.email).first():
        return jsonify({'error': 'email already exists'}), 409

    user = User(
        name=payload.name,
        role=payload.role,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password)
    )
    db.session.add(user)
    db.session.commit()

    response = UserResponse.from_orm(user)
    return jsonify({'user': response.dict()}), 201


@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'email and password are required'}), 400

    user = User.query.filter_by(email=email).first()
    if user is None or not verify_password(user.password_hash, password):
        return jsonify({'error': 'Invalid credentials'}), 401

    login_user(user)
    return jsonify({'message': 'Logged in', 'user': user.to_dict()}), 200


@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out'}), 200


@bp.route('/me', methods=['GET'])
@login_required
def me():
    return jsonify({'user': current_user.to_dict()}), 200
