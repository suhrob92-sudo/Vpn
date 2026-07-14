"""user balance wallet

Revision ID: 7c1f2ab90d41
Revises: 35681ec69265
Create Date: 2026-07-10 12:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '7c1f2ab90d41'
down_revision = '35681ec69265'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('balance', sa.Numeric(12, 2), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    op.drop_column('users', 'balance')
