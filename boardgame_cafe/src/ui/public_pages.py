from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import login_required, logout_user



def register_public_pages(app: Flask) -> None:
    @app.route("/", methods=["GET"])
    def home():
        return render_template("index.html")

    @app.route("/games", methods=["GET"])
    def games_page():
        return render_template("games.html")

    @app.route("/booking", methods=["GET"])
    @login_required
    def booking_page():
        return render_template("booking.html")

    @app.route("/my-bookings", methods=["GET"])
    @login_required
    def my_bookings_page():
        return render_template("my_bookings.html")

    @app.route("/reservations/confirmation/<int:reservation_id>", methods=["GET"])
    @login_required
    def reservation_confirmation_page(reservation_id: int):
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
