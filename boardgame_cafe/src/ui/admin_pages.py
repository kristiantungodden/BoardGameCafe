from __future__ import annotations

from flask import Flask, flash, redirect, render_template, url_for
from flask_login import current_user, login_required


def _user_role_value(user) -> str | None:
    role = getattr(user, "role", None)
    if hasattr(role, "value"):
        role = role.value
    if isinstance(role, str):
        return role
    return None


def _require_admin_page():
    if not current_user.is_authenticated:
        flash("Admin access required.", "error")
        return redirect(url_for("admin_login_page"))
    if _user_role_value(current_user) != "admin":
        flash("Admin access required.", "error")
        return redirect(url_for("home"))
    return None


def register_admin_pages(app: Flask) -> None:
    @app.route("/admin", methods=["GET"])
    @login_required
    def admin_page():
        err = _require_admin_page()
        if err:
            return err
        return render_template("admin_dashboard.html")

    @app.route("/admin/login", methods=["GET"])
    def admin_login_page():
        if current_user.is_authenticated and _user_role_value(current_user) == "admin":
            return redirect(url_for("admin_page"))
        return render_template("admin_login.html")