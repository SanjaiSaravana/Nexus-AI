"""phase3_memory

Revision ID: 003_phase3
Revises: 002_phase2
Create Date: 2026-10-14 01:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from app.core.database import GUID, VectorType
from app.core.config import settings

revision: str = '003_phase3'
down_revision: Union[str, None] = '002_phase2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'memories',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('user_id', GUID(), nullable=False),
        sa.Column('memory_type', sa.String(length=32), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('importance', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('source', sa.String(length=64), nullable=False, server_default='conversation'),
        sa.Column('source_id', sa.String(length=255), nullable=True),
        sa.Column('mem_metadata', sa.JSON(), nullable=False),
        sa.Column('embedding', VectorType(dim=settings.EMBEDDING_DIM), nullable=True),
        sa.Column('access_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_memories_id'), 'memories', ['id'], unique=False)
    op.create_index(op.f('ix_memories_user_id'), 'memories', ['user_id'], unique=False)
    op.create_index(op.f('ix_memories_memory_type'), 'memories', ['memory_type'], unique=False)
    op.create_index(op.f('ix_memories_importance'), 'memories', ['importance'], unique=False)
    op.create_index(op.f('ix_memories_created_at'), 'memories', ['created_at'], unique=False)

def downgrade() -> None:
    op.drop_table('memories')
