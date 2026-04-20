from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from pydantic import ValidationError as PydanticValidationError

from features.users.application.use_cases.user_use_cases import UpdateOwnProfileCommand
from features.users.composition.auth_use_case_factories import get_update_profile_use_case
from features.users.infrastructure import UserDB as User
from features.users.presentation.schemas.user_schema import UserUpdate
from shared.domain.exceptions import ValidationError as DomainValidationError



def register_account_pages(app: Flask) -> None:
    @app.route("/me", methods=["GET", "POST"])
    @login_required
    def me():
        if request.method == "POST":
            try:
                payload = UserUpdate.model_validate(request.form.to_dict())
            except PydanticValidationError:
                flash("Profile update failed. Please check your input.", "error")
                return redirect(url_for("me"))

            use_case = get_update_profile_use_case()
            try:
                use_case.execute(
                    UpdateOwnProfileCommand(
                        user_id=current_user.id,
                        name=payload.name,
                        phone=payload.phone,
                    ),
                    current_user,
                )
            except DomainValidationError as exc:
                flash(str(exc), "error")
                return redirect(url_for("me"))

            flash("Profile updated successfully.", "success")
            return redirect(url_for("me"))

        return render_template("account.html", user=current_user)

    @app.route("/me/password-change", methods=["GET"])
    @login_required
    def password_change_page():
        return render_template("change_password.html", user=current_user)
