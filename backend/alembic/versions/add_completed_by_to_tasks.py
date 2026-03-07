"""Add completed_by field to tasks

Revision ID: add_completed_by_to_tasks
Revises: bf296fc8b9f3
Create Date: 2026-03-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'add_completed_by_to_tasks'
down_revision = 'bf296fc8b9f3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tasks', sa.Column('completed_by', sa.String(length=50), nullable=True))
    op.create_index('ix_tasks_completed_by', 'tasks', ['completed_by'])


def downgrade() -> None:
    op.drop_index('ix_tasks_completed_by', table_name='tasks')
    op.drop_column('tasks', 'completed_by')
