"""add user suspension flag

Revision ID: f1c2b3d4e5f6
Revises: e7a9c12b4d33
Create Date: 2026-04-21 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f1c2b3d4e5f6"
down_revision = "e7a9c12b4d33"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_suspended", sa.Boolean(), nullable=False, server_default=sa.text("0"))
        )


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("is_suspended")
