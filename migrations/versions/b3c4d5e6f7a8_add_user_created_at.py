"""add user created_at

Revision ID: b3c4d5e6f7a8
Revises: f1c2b3d4e5f6
Create Date: 2026-04-22 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b3c4d5e6f7a8"
down_revision = "f1c2b3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=True,
            )
        )

    op.execute("UPDATE users SET created_at = datetime('now') WHERE created_at IS NULL")


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("created_at")
