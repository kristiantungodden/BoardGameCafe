from flask import Flask, flash, redirect, render_template, url_for
from flask_login import current_user, login_required



def register_steward_pages(app: Flask) -> None:
    def _require_staff_page():
        if getattr(current_user, "role", None) not in ("staff", "admin"):
            flash("Staff access required.", "error")
            return redirect(url_for("home"))
        return None

    @app.route("/steward", methods=["GET"])
    @login_required
    def steward_page():
        err = _require_staff_page()
        if err:
            return err
        return render_template("steward_dashboard.html")

    @app.route("/steward/pending", methods=["GET"])
    @login_required
    def steward_pending_page():
        err = _require_staff_page()
        if err:
            return err
        return render_template("steward_pending.html")

    @app.route("/steward/seated", methods=["GET"])
    @login_required
    def steward_seated_page():
        err = _require_staff_page()
        if err:
            return err
        return render_template("steward_seated.html")

    @app.route("/steward/game-copies", methods=["GET"])
    @login_required
    def steward_game_copies_page():
        err = _require_staff_page()
        if err:
            return err
        return render_template("steward_game_copies.html")

    @app.route("/steward/incidents", methods=["GET"])
    @login_required
    def steward_incidents_page():
        err = _require_staff_page()
        if err:
            return err
        return render_template("steward_incidents.html")

    @app.route("/steward/incidents/create", methods=["GET"])
    @login_required
    def steward_create_incident_page():
        err = _require_staff_page()
        if err:
            return err
        return render_template("create_incident.html")
