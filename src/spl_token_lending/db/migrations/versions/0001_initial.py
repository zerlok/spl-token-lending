"""initial

Revision ID: 0001
Revises: 
Create Date: 2023-02-01 14:19:31.041043

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""create extension if not exists "uuid-ossp";""")


def downgrade() -> None:
    op.execute("""drop extension if exists "uuid-ossp";""")
