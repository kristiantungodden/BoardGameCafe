"""
Flask application initialization and configuration.

This is the main entry point for the Board Game Café application.
"""

from flask import Flask, jsonify
from flask_cors import CORS
from config import settings
from infrastructure.database import engine
from infrastructure.database.models import Base


# Initialize Flask app
app = Flask(
    __name__,
    instance_relative_config=True,
)

# Configuration
app.config['DEBUG'] = settings.debug
app.config['JSON_SORT_KEYS'] = False

# Enable CORS
CORS(
    app,
    origins=["*"],  # TODO: Configure in production
    supports_credentials=True,
    allow_headers=["*"],
    methods=["*"],
)

# Create database tables
Base.metadata.create_all(engine)

# Register blueprints
from presentation.api import auth_bp, games_bp, tables_bp, reservations_bp, steward_bp, admin_bp

app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(games_bp, url_prefix="/games")
app.register_blueprint(tables_bp, url_prefix="/tables")
app.register_blueprint(reservations_bp, url_prefix="/reservations")
app.register_blueprint(steward_bp, url_prefix="/steward")
app.register_blueprint(admin_bp, url_prefix="/admin")


@app.route("/", methods=["GET"])
def root():
    """Root endpoint."""
    return jsonify({
        "app": settings.app_name,
        "version": "1.0.0",
    })


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"})


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=settings.debug,
    )
