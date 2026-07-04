"""phase 6 content-only authoring: drop is_system and user_id from templates

Revision ID: b1_phase6_content_only_authoring
Revises: a0aa74606361
Create Date: 2026-08-08 18:30:00.000000

Phase 6 step 1 deletes the user-template authoring surface. After this
migration:

- ``templates.is_system`` is dropped. Every remaining row is a system
  template seeded by ``api/app/db/seed.py``. The boolean column carried no
  information (it was either True on existing rows or False on rows
  belonging to deleted user-templates).
- ``templates.user_id`` is dropped along with its index and FK constraint.
  ``User.templates`` was the only consumer of the back-reference, and is
  removed in ``app/models/user.py``. CVs whose ``template_id`` pointed at a
  deleted ``user_*`` row fall back to ``generic-modern`` on next open —
  the brief's wording is read as "delete the user-templates surface";
  preserving user templates is out of scope.

SQLite stores FKs as part of the column definition; ``ALTER TABLE DROP
COLUMN`` with an active FK requires the batch mode that copies the table
to a temp, recreates without the FK, and swaps back. We rely on the
default ``batch_alter_table`` (no ``recreate`` override) so indexes are
handled in the same transaction.

``downgrade()`` re-adds the columns with their original nullability and
re-creates the index. ``user_id`` is left NULL on downgrade (no user-template
data is preserved; documented in this docstring).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1_phase6_content_only_authoring"
down_revision: Union[str, None] = "a0aa74606361"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Best-effort cleanup of any orphan user_id references. The column is
    # nullable; rows that pointed at now-deleted users must not block the
    # table rebuild.
    op.execute("UPDATE templates SET user_id = NULL WHERE user_id IS NOT NULL")

    with op.batch_alter_table("templates") as batch_op:
        batch_op.drop_index("ix_templates_user_id")
        batch_op.drop_column("user_id")
        batch_op.drop_column("is_system")


def downgrade() -> None:
    with op.batch_alter_table("templates") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_system", sa.Boolean(), nullable=False, server_default=sa.true()
            )
        )
        batch_op.add_column(sa.Column("user_id", sa.String(length=36), nullable=True))
        batch_op.create_index("ix_templates_user_id", ["user_id"], unique=False)
