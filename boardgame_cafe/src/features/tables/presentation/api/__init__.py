from .table_routes import bp

try:
	from .admin_routes import bp as admin_bp
except ModuleNotFoundError:
	admin_bp = None

__all__ = ["bp", "admin_bp"]
