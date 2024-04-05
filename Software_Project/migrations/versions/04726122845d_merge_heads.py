"""Merge heads

Revision ID: 04726122845d
Revises: 13c80205b8a5, 21cfa4487d69, 281635ffe588, 3fb2b6169175, 85757e0fb985, 878c535409f3, 99021fe5160d, c00fc2a94091, d9800bfc6dc9, e51b75c1c654, eb458a4fc318, f048ab7f2f16
Create Date: 2024-03-29 16:14:42.540895

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '04726122845d'
down_revision = ('13c80205b8a5', '21cfa4487d69', '281635ffe588', '3fb2b6169175', '85757e0fb985', '878c535409f3', '99021fe5160d', 'c00fc2a94091', 'd9800bfc6dc9', 'e51b75c1c654', 'eb458a4fc318', 'f048ab7f2f16')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
