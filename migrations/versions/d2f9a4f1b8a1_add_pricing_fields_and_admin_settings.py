"""add pricing fields and admin settings

Revision ID: d2f9a4f1b8a1
Revises: c4e0a47be900
Create Date: 2026-04-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d2f9a4f1b8a1"
down_revision = "c4e0a47be900"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("games", schema=None) as batch_op:
        batch_op.add_column(sa.Column("price_cents", sa.Integer(), nullable=False, server_default="0"))

    with op.batch_alter_table("cafe_tables", schema=None) as batch_op:
        batch_op.add_column(sa.Column("price_cents", sa.Integer(), nullable=False, server_default="15000"))

    op.create_table(
        "admin_settings",
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("value_int", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )

    op.execute(
        sa.text(
            "INSERT INTO admin_settings (key, value_int) VALUES ('booking_base_fee_cents', 2500)"
        )
    )


def downgrade():
    op.drop_table("admin_settings")

    with op.batch_alter_table("cafe_tables", schema=None) as batch_op:
        batch_op.drop_column("price_cents")

    with op.batch_alter_table("games", schema=None) as batch_op:
        batch_op.drop_column("price_cents")
