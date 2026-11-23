"""add card descriptions

Revision ID: 08251ee44f5a
Revises: bb1585d77e6e
Create Date: 2026-11-20 22:04:06.088888

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "08251ee44f5a"
down_revision: str | Sequence[str] | None = "bb1585d77e6e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "card_descriptions",
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("is_reversed", sa.Boolean(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["card_id"],
            ["cards.id"],
            name=op.f("fk_card_descriptions_card_id_cards"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("card_id", "is_reversed", name=op.f("pk_card_descriptions")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("card_descriptions")
