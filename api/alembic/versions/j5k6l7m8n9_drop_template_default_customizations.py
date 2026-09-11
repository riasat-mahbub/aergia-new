"""drop the unused template default_customizations column

Revision ID: j5k6l7m8n9
Revises: i4j5k6l7m8
Create Date: 2026-09-11 00:00:00.000000

The JSON conversion was completed before this schema migration. Refuse to
drop a populated column so an operator cannot lose an old template's defaults
by running Alembic against an unconverted database.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


revision: str = "j5k6l7m8n9"
down_revision: str | None = "i4j5k6l7m8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("templates")}
    if "default_customizations" not in columns:
        return

    remaining = bind.execute(
        sa.text("select count(*) from templates where default_customizations is not null")
    ).scalar_one()
    if remaining:
        raise RuntimeError(
            "templates.default_customizations still contains data; convert "
            "the legacy template defaults before upgrading"
        )

    with op.batch_alter_table("templates") as batch_op:
        batch_op.drop_column("default_customizations")


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("templates")}
    if "default_customizations" not in columns:
        with op.batch_alter_table("templates") as batch_op:
            batch_op.add_column(sa.Column("default_customizations", sa.JSON(), nullable=True))
