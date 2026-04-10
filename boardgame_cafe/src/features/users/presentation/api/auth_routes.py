from flask import Blueprint, request, jsonify, redirect, url_for, flash, render_template
from flask_login import logout_user, login_required, current_user

from werkzeug.exceptions import BadRequest
from pydantic import ValidationError as PydanticValidationError

from shared.domain.exceptions import ValidationError as DomainValidationError
from shared.infrastructure import csrf
from features.users.application.use_cases.auth_use_cases import LoginCommand, RegisterCommand
from features.users.presentation.api.deps import get_login_use_case, get_register_use_case
from features.users.presentation.schemas.auth_schema import LoginRequest

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


from features.users.presentation.schemas.user_schema import UserCreate, UserResponse


def _is_json_request() -> bool:
    return request.is_json


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
        use_case.execute(RegisterCommand(**payload.model_dump()))
    except DomainValidationError as exc:
        if is_json_request:
            return {"error": str(exc)}, 409
        flash(str(exc), "error")
        return redirect(url_for("register_page"))

    if is_json_request:
        return {"message": "User registered successfully"}, 201

    flash("User registered successfully. You can now sign in.", "success")
    return redirect(url_for("login_page"))

@bp.post("/login")
def login():
    is_json_request = _is_json_request()

    if is_json_request:
        try:
            raw = request.get_json()
        except BadRequest:
            return {"error": "Invalid JSON body"}, 400
    else:
        raw = request.form.to_dict()

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
        if is_json_request:
            return {"error": str(exc)}, 401
        flash(str(exc), "error")
        return redirect(url_for("login_page"))

    if is_json_request:
        return {"message": "Logged in", "user": UserResponse.from_domain(user).model_dump()}, 200

    flash("Logged in successfully.", "success")
    next_target = request.form.get("next") or request.args.get("next")
    if next_target and next_target.startswith("/") and not next_target.startswith("//"):
        return redirect(next_target)
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
