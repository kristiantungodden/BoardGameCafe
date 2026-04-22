"""allow created booking status

Revision ID: b7c8d9e0f1a2
Revises: f1c2b3d4e5f6
Create Date: 2026-04-22 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7c8d9e0f1a2"
down_revision = "f1c2b3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("bookings", schema=None) as batch_op:
        batch_op.drop_constraint("ck_bookings_status_valid", type_="check")
        batch_op.create_check_constraint(
            "ck_bookings_status_valid",
            "status IN ('created', 'confirmed', 'seated', 'completed', 'cancelled', 'no_show')",
        )
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=30),
            server_default=sa.text("'created'"),
            existing_nullable=False,
        )


def downgrade():
    with op.batch_alter_table("bookings", schema=None) as batch_op:
        batch_op.drop_constraint("ck_bookings_status_valid", type_="check")
        batch_op.create_check_constraint(
            "ck_bookings_status_valid",
            "status IN ('confirmed', 'seated', 'completed', 'cancelled', 'no_show')",
        )
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=30),
            server_default=sa.text("'confirmed'"),
            existing_nullable=False,
        )
