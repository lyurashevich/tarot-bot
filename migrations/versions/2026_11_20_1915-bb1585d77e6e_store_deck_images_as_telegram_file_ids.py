"""store deck images as telegram file ids

Revision ID: bb1585d77e6e
Revises: 9d555ca21cf8
Create Date: 2026-11-20 19:15:35.083473

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bb1585d77e6e"
down_revision: str | Sequence[str] | None = "9d555ca21cf8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "deck_card_images", "file_id_upright", existing_type=sa.VARCHAR(), nullable=False
    )
    op.alter_column(
        "deck_card_images", "file_id_reversed", existing_type=sa.VARCHAR(), nullable=False
    )
    op.drop_column("deck_card_images", "image_path")


def downgrade() -> None:
    """Downgrade schema."""
    # Existing rows get an empty path: the files are not kept on disk any more.
    op.add_column(
        "deck_card_images",
        sa.Column("image_path", sa.VARCHAR(), nullable=False, server_default=""),
    )
    op.alter_column("deck_card_images", "image_path", server_default=None)
    op.alter_column(
        "deck_card_images", "file_id_reversed", existing_type=sa.VARCHAR(), nullable=True
    )
    op.alter_column(
        "deck_card_images", "file_id_upright", existing_type=sa.VARCHAR(), nullable=True
    )
