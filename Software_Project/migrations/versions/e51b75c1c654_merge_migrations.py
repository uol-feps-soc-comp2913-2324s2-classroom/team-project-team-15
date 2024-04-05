"""Merge migrations

Revision ID: e51b75c1c654
Revises: 51a9fa4ed3ac, 83b50f4d6ae5, f69c25d8db3f
Create Date: 2024-03-14 04:08:12.917670

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e51b75c1c654'
down_revision = ('51a9fa4ed3ac', '83b50f4d6ae5', 'f69c25d8db3f')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
