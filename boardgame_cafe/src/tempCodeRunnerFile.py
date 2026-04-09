    configure_payment_routes,
    payment_bp,
)
from features.reservations.presentation.api import reservation_routes
from features.users.presentation.api import auth_routes, steward_admin_routes
from features.users.infrastructure import UserDB as User

def create_app(config_name: str = None):
    """
    Application factory function.
    
    Args:
        config_name: 'development', 'testing', or 'production'
                    Defaults to FLASK_ENV environment variable
    """
    template_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "frontend", "templates")
    )
    static_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "frontend", "static")
    )
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    # Configuration
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")
    app.config.from_object(f"config.{config_name.capitalize()}Config")

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    celery_app = init_celery(app)
    app.celery_app = celery_app

    # Register blueprints
    register_blueprints(app)

    # Register error handlers
    register_error_handlers(app)

    @app.route("/", methods=["GET"])
    def home():
        return render_template("index.html")

    @app.route("/games", methods=["GET"])
    def games_page():
        return render_template("games.html")

    @app.route("/reservations", methods=["GET"])
    @login_required
