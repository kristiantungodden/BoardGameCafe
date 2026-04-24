from flask import Flask, flash, redirect, render_template, url_for
from flask_login import login_required, logout_user, current_user
from features.users.infrastructure.database.announcement_db import AnnouncementDB
from shared.infrastructure import db


def register_public_pages(app: Flask) -> None:
    def _require_customer_role():
        if not current_user.is_authenticated or current_user.role != "customer":
            flash("You must be logged in as a customer to access this page.", "error")
            return redirect(url_for("login_page"))
        return None

    @app.route("/", methods=["GET"])
    def home():
        announcements = (
            db.session.query(AnnouncementDB)
            .filter(AnnouncementDB.is_published.is_(True))
            .order_by(AnnouncementDB.published_at.desc(), AnnouncementDB.id.desc())
            .limit(5)
            .all()
        )   
        return render_template("index.html", announcements=announcements)

    @app.route("/games", methods=["GET"])
    def games_page():
        return render_template("games.html")

    @app.route("/booking", methods=["GET"])
    @login_required
    def booking_page():
        err = _require_customer_role()
        if err:
            return err
        return render_template("booking.html")

    @app.route("/my-bookings", methods=["GET"])
    @login_required
    def my_bookings_page():
        err = _require_customer_role()
        if err:
            return err
        return render_template("my_bookings.html")

    @app.route("/reservations/confirmation/<int:reservation_id>", methods=["GET"])
    @login_required
    def reservation_confirmation_page(reservation_id: int):
        err = _require_customer_role()
        if err:
            return err
        return render_template("booking_confirmation.html", reservation_id=reservation_id)

    @app.route("/login", methods=["GET"])
    def login_page():
        return render_template("login.html")

    @app.route("/register", methods=["GET"])
    def register_page():
        return render_template("register.html")

    @app.route("/logout", methods=["POST"])
    @login_required
    def logout():
        logout_user()
        flash("Logged out.", "success")
        return redirect(url_for("home"))
