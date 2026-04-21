from flask import Blueprint, request, jsonify, redirect, url_for, flash, render_template, current_app
from flask_login import logout_user, login_required, current_user

from werkzeug.exceptions import BadRequest
from pydantic import ValidationError as PydanticValidationError

from shared.domain.exceptions import ValidationError as DomainValidationError
from shared.infrastructure import csrf
from features.users.application.use_cases.auth_use_cases import LoginCommand, RegisterCommand
from features.users.application.use_cases.user_use_cases import ChangePasswordCommand
from features.users.composition.auth_use_case_factories import (
    get_change_password_use_case,
    get_login_use_case,
    get_password_hasher,
    get_register_use_case,
)
from features.users.infrastructure.repositories import SqlAlchemyUserRepository
from features.users.presentation.schemas.auth_schema import (
    ChangePasswordRequest,
    LoginRequest,
)

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


from features.users.presentation.schemas.user_schema import UserCreate, UserResponse
from shared.domain.events import UserRegistered


def _is_json_request() -> bool:
    return request.is_json


def _user_role_value(user) -> str | None:
    role = getattr(user, "role", None)
    if hasattr(role, "value"):
        role = role.value
    if isinstance(role, str):
        return role
    return None


@bp.route('/register', methods=['POST'])
def register():
    is_json_request = _is_json_request()

    if is_json_request:
        try:
            raw = request.get_json()
        except BadRequest:
            return jsonify({'error': 'Invalid JSON body'}), 400
    else:
        raw = request.form.to_dict()

    try:
        payload = UserCreate.model_validate(raw or {})
    except PydanticValidationError as exc:
        if is_json_request:
            return {"error": "Registration failed", "details": exc.errors()}, 400
        flash("Registration failed. Please check your input.", "error")
        return redirect(url_for("register_page"))

    use_case = get_register_use_case()

    try:
        user = use_case.execute(RegisterCommand(**payload.model_dump()))
    except DomainValidationError as exc:
        if is_json_request:
            return {"error": str(exc)}, 409
        flash(str(exc), "error")
        return redirect(url_for("register_page"))

    event_bus = getattr(current_app, "event_bus", None)
    if event_bus is not None:
        event_bus.publish(UserRegistered(user_id=user.id, email=user.email))

    if is_json_request:
        return {"message": "User registered successfully"}, 201

    flash("User registered successfully. You can now sign in.", "success")
    return redirect(url_for("login_page"))

@bp.post("/login")
def login():
    is_json_request = _is_json_request()
    login_area = None

    if is_json_request:
        try:
            raw = request.get_json()
        except BadRequest:
            return {"error": "Invalid JSON body"}, 400
    else:
        raw = request.form.to_dict()

    if raw:
        login_area = str(raw.get("area") or request.args.get("area") or "").strip().lower() or None

    try:
        payload = LoginRequest.model_validate(raw or {})
    except PydanticValidationError as exc:
        if is_json_request:
            return {"error": "Validation failed", "details": exc.errors()}, 400
        flash("Invalid login input.", "error")
        return redirect(url_for("login_page"))

    use_case = get_login_use_case()
    try:
        user = use_case.execute(LoginCommand(**payload.model_dump()))
    except DomainValidationError as exc:
        status = 403 if str(exc) == "Account suspended" else 401
        if is_json_request:
            return {"error": str(exc)}, status
        flash(str(exc), "error")
        if login_area == "admin":
            return redirect(url_for("admin_login_page"))
        return redirect(url_for("login_page"))

    user_role = _user_role_value(user)
    if login_area == "admin" and user_role != "admin":
        message = "Admin access required."
        if is_json_request:
            return {"error": message}, 403
        flash(message, "error")
        return redirect(url_for("admin_login_page"))

    if is_json_request:
        return {
            "message": "Logged in",
            "requires_password_change": bool(getattr(user, "force_password_change", False)),
            "user": UserResponse.from_domain(user).model_dump(),
        }, 200

    flash("Logged in successfully.", "success")
    next_target = request.form.get("next") or request.args.get("next")
    if next_target and next_target.startswith("/") and not next_target.startswith("//"):
        return redirect(next_target)
    if user_role == "admin":
        return redirect(url_for("admin_page"))
    return redirect(url_for("home"))


@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out'}), 200


@bp.route('/me', methods=['GET'])
@login_required
def me():
    return jsonify({'user': current_user.to_dict()}), 200


@bp.post('/change-password')
@login_required
def change_password():
    is_json_request = _is_json_request()

    if is_json_request:
        try:
            raw = request.get_json()
        except BadRequest:
            return {"error": "Invalid JSON body"}, 400
    else:
        raw = request.form.to_dict()

    try:
        payload = ChangePasswordRequest.model_validate(raw or {})
    except PydanticValidationError as exc:
        if is_json_request:
            return {"error": "Validation failed", "details": exc.errors()}, 400
        flash("Invalid password change input.", "error")
        return redirect(url_for("password_change_page"))

    users = SqlAlchemyUserRepository()
    requesting_user = users.get_by_id(int(current_user.id))
    if requesting_user is None:
        if is_json_request:
            return {"error": "Authentication required"}, 401
        flash("Authentication required.", "error")
        return redirect(url_for("login_page"))

    # Only enforce current password when user is not in forced reset flow.
    if not requesting_user.force_password_change:
        hasher = get_password_hasher()
        if not payload.current_password:
            if is_json_request:
                return {"error": "current_password is required"}, 400
            flash("Current password is required.", "error")
            return redirect(url_for("password_change_page"))
        if not hasher.verify(requesting_user.password_hash, payload.current_password):
            if is_json_request:
                return {"error": "Current password is incorrect"}, 400
            flash("Current password is incorrect.", "error")
            return redirect(url_for("password_change_page"))

    use_case = get_change_password_use_case()
    hasher = get_password_hasher()
    try:
        updated_user = use_case.execute(
            ChangePasswordCommand(
                user_id=requesting_user.id,
                new_password_hash=hasher.hash(payload.new_password),
            ),
            requesting_user=requesting_user,
        )
    except DomainValidationError as exc:
        if is_json_request:
            return {"error": str(exc)}, 400
        flash(str(exc), "error")
        return redirect(url_for("password_change_page"))

    if is_json_request:
        return {
            "message": "Password changed",
            "user": UserResponse.from_domain(updated_user).model_dump(),
        }, 200

    flash("Password changed successfully.", "success")
    role = _user_role_value(updated_user)
    if role == "admin":
        return redirect(url_for("admin_page"))
    if role == "staff":
        return redirect(url_for("steward_page"))
    return redirect(url_for("home"))
