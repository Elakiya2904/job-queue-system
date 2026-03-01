"""Add new task statuses in_progress and dead_letter

Revision ID: 2609822d179d
Revises: 0001_initial
Create Date: 2026-03-01 13:48:45.705813

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2609822d179d'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite doesn't support dropping constraints directly
    # Since we're only adding values to an existing constraint, 
    # we can just run raw SQL to recreate the table with the new constraint
    
    # For SQLite, we need to use batch operations to modify constraints
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.drop_constraint('check_task_status', type_='check')
        batch_op.create_check_constraint(
            'check_task_status',
            "status IN ('queued', 'processing', 'completed', 'failed', 'failed_permanent', 'in_progress', 'dead_letter')"
        )


def downgrade() -> None:
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.drop_constraint('check_task_status', type_='check')
        batch_op.create_check_constraint(
            'check_task_status',
            "status IN ('queued', 'processing', 'completed', 'failed', 'failed_permanent')"
        )