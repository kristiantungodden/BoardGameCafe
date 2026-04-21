"""replace admin settings with admin policy

Revision ID: e7a9c12b4d33
Revises: d2f9a4f1b8a1
Create Date: 2026-04-20 00:00:01.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e7a9c12b4d33"
down_revision = "d2f9a4f1b8a1"
branch_labels = None
depends_on = None


def _table_exists(bind, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade():
    bind = op.get_bind()

    op.create_table(
        "admin_policies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("booking_base_fee_cents", sa.Integer(), nullable=False, server_default="2500"),
        sa.Column("booking_base_fee_priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("booking_base_fee_override_cents", sa.Integer(), nullable=True),
        sa.Column("booking_base_fee_override_priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("booking_base_fee_override_until_epoch", sa.Integer(), nullable=True),
        sa.Column("booking_cancel_time_limit_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.PrimaryKeyConstraint("id"),
    )

    base_fee = 2500
    base_priority = 0
    override_fee = None
    override_priority = 100
    override_until = None

    if _table_exists(bind, "admin_settings"):
        rows = bind.execute(sa.text("SELECT key, value_int FROM admin_settings")).fetchall()
        settings = {str(row[0]): row[1] for row in rows}
        base_fee = int(settings.get("booking_base_fee_cents", base_fee))
        base_priority = int(settings.get("booking_base_fee_priority", base_priority))
        override_raw = settings.get("booking_base_fee_override_cents")
        override_fee = int(override_raw) if override_raw is not None else None
        override_priority = int(settings.get("booking_base_fee_override_priority", override_priority))
        override_until_raw = settings.get("booking_base_fee_active_until_epoch")
        override_until = int(override_until_raw) if override_until_raw is not None else None

    bind.execute(
        sa.text(
            """
            INSERT INTO admin_policies (
                id,
                booking_base_fee_cents,
                booking_base_fee_priority,
                booking_base_fee_override_cents,
                booking_base_fee_override_priority,
                booking_base_fee_override_until_epoch,
                booking_cancel_time_limit_hours
            ) VALUES (
                1,
                :base_fee,
                :base_priority,
                :override_fee,
                :override_priority,
                :override_until,
                24
            )
            """
        ),
        {
            "base_fee": base_fee,
            "base_priority": base_priority,
            "override_fee": override_fee,
            "override_priority": override_priority,
            "override_until": override_until,
        },
    )

    if _table_exists(bind, "admin_settings"):
        op.drop_table("admin_settings")


def downgrade():
    op.create_table(
        "admin_settings",
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("value_int", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )

    bind = op.get_bind()
    row = bind.execute(
        sa.text(
            """
            SELECT
                booking_base_fee_cents,
                booking_base_fee_priority,
                booking_base_fee_override_cents,
                booking_base_fee_override_priority,
                booking_base_fee_override_until_epoch
            FROM admin_policies
            WHERE id = 1
            """
        )
    ).fetchone()

    if row is not None:
        bind.execute(
            sa.text(
                """
                INSERT INTO admin_settings (key, value_int) VALUES
                ('booking_base_fee_cents', :base_fee),
                ('booking_base_fee_priority', :base_priority),
                ('booking_base_fee_override_priority', :override_priority)
                """
            ),
            {
                "base_fee": int(row[0]),
                "base_priority": int(row[1]),
                "override_priority": int(row[3]),
            },
        )

        if row[2] is not None:
            bind.execute(
                sa.text(
                    "INSERT INTO admin_settings (key, value_int) VALUES ('booking_base_fee_override_cents', :v)"
                ),
                {"v": int(row[2])},
            )
        if row[4] is not None:
            bind.execute(
                sa.text(
                    "INSERT INTO admin_settings (key, value_int) VALUES ('booking_base_fee_active_until_epoch', :v)"
                ),
                {"v": int(row[4])},
            )

    op.drop_table("admin_policies")
