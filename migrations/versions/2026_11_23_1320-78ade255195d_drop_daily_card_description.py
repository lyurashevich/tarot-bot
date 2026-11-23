"""drop daily card description

Revision ID: 78ade255195d
Revises: 08251ee44f5a
Create Date: 2026-11-23 13:20:14.644321

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "78ade255195d"
down_revision: str | Sequence[str] | None = "08251ee44f5a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Descriptions are shared per card and position now: see card_descriptions.
    op.drop_column("daily_cards", "description")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("daily_cards", sa.Column("description", sa.Text(), nullable=True))
