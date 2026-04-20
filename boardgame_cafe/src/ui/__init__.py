from flask import Flask

from .admin_pages import register_admin_pages
from .account_pages import register_account_pages
from .payment_pages import register_payment_pages
from .public_pages import register_public_pages
from .steward_pages import register_steward_pages



def register_ui_pages(app: Flask) -> None:
    register_public_pages(app)
    register_account_pages(app)
    register_payment_pages(app)
    register_admin_pages(app)
    register_steward_pages(app)
