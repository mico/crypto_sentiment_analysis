"""change_sentiment_to_integer

Revision ID: 8921cb7f4f2e
Revises: 5688e2683766
Create Date: 2025-04-19 18:24:24.672311

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8921cb7f4f2e'
down_revision: Union[str, None] = '5688e2683766'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
