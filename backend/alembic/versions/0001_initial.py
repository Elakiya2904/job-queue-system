"""Initial database schema for job queue system

Revision ID: 0001_initial
Revises: 
Create Date: 2026-02-28 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create workers table
    op.create_table('workers',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('capabilities', sa.JSON(), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=True),
        sa.Column('api_key_hash', sa.String(length=255), nullable=True),
        sa.Column('current_task_id', sa.String(length=50), nullable=True),
        sa.Column('last_heartbeat', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tasks_processed', sa.Integer(), nullable=False),
        sa.Column('tasks_failed', sa.Integer(), nullable=False),
        sa.Column('tasks_completed', sa.Integer(), nullable=False),
        sa.Column('total_processing_time_ms', sa.Integer(), nullable=False),
        sa.Column('uptime_seconds', sa.Integer(), nullable=False),
        sa.Column('memory_usage', sa.Float(), nullable=True),
        sa.Column('cpu_usage', sa.Float(), nullable=True),
        sa.Column('disk_usage', sa.Float(), nullable=True),
        sa.Column('hostname', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('port', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('max_concurrent_tasks', sa.Integer(), nullable=False),
        sa.Column('heartbeat_interval', sa.Integer(), nullable=False),
        sa.CheckConstraint("status IN ('active', 'idle', 'offline', 'error')", name='check_worker_status'),
        sa.CheckConstraint('tasks_processed >= 0', name='check_tasks_processed_non_negative'),
        sa.CheckConstraint('tasks_failed >= 0', name='check_tasks_failed_non_negative'),
        sa.CheckConstraint('tasks_completed >= 0', name='check_tasks_completed_non_negative'),
        sa.CheckConstraint('total_processing_time_ms >= 0', name='check_total_processing_time_non_negative'),
        sa.CheckConstraint('uptime_seconds >= 0', name='check_uptime_non_negative'),
        sa.CheckConstraint('memory_usage IS NULL OR (memory_usage >= 0 AND memory_usage <= 100)', name='check_memory_usage_percentage'),
        sa.CheckConstraint('cpu_usage IS NULL OR (cpu_usage >= 0 AND cpu_usage <= 100)', name='check_cpu_usage_percentage'),
        sa.CheckConstraint('disk_usage IS NULL OR (disk_usage >= 0 AND disk_usage <= 100)', name='check_disk_usage_percentage'),
        sa.CheckConstraint('max_concurrent_tasks > 0', name='check_max_concurrent_tasks_positive'),
        sa.CheckConstraint('heartbeat_interval > 0', name='check_heartbeat_interval_positive'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_worker_capabilities', 'workers', ['capabilities'])
    op.create_index('idx_worker_current_task', 'workers', ['current_task_id'])
    op.create_index('idx_worker_performance', 'workers', ['tasks_processed', 'tasks_failed'])
    op.create_index('idx_worker_resources', 'workers', ['memory_usage', 'cpu_usage'])
    op.create_index('idx_worker_status_heartbeat', 'workers', ['status', 'last_heartbeat'])
    op.create_index(op.f('ix_workers_api_key_hash'), 'workers', ['api_key_hash'])
    op.create_index(op.f('ix_workers_id'), 'workers', ['id'])
    op.create_index(op.f('ix_workers_last_heartbeat'), 'workers', ['last_heartbeat'])
    op.create_index(op.f('ix_workers_status'), 'workers', ['status'])
    
    # Create tasks table
    op.create_table('tasks',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('type', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('scheduled_for', sa.DateTime(timezone=True), nullable=True),
        sa.Column('timeout', sa.Integer(), nullable=False),
        sa.Column('max_retries', sa.Integer(), nullable=False),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('locked_by', sa.String(length=50), nullable=True),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('lock_timeout', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.String(length=50), nullable=False),
        sa.Column('correlation_id', sa.String(length=100), nullable=True),
        sa.Column('idempotency_key', sa.String(length=255), nullable=True),
        sa.CheckConstraint("status IN ('queued', 'processing', 'completed', 'failed', 'failed_permanent')", name='check_task_status'),
        sa.CheckConstraint('priority IN (1, 2, 3, 4)', name='check_task_priority'),
        sa.CheckConstraint('retry_count >= 0', name='check_retry_count_non_negative'),
        sa.CheckConstraint('max_retries >= 0', name='check_max_retries_non_negative'),
        sa.CheckConstraint('timeout > 0', name='check_timeout_positive'),
        sa.CheckConstraint('(locked_by IS NULL AND locked_at IS NULL AND lock_timeout IS NULL) OR (locked_by IS NOT NULL AND locked_at IS NOT NULL AND lock_timeout IS NOT NULL)', name='check_lock_fields_consistency'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key')
    )
    op.create_index('idx_task_correlation', 'tasks', ['correlation_id'])
    op.create_index('idx_task_created_by_status', 'tasks', ['created_by', 'status'])
    op.create_index('idx_task_lock_expiry', 'tasks', ['locked_at', 'lock_timeout'])
    op.create_index('idx_task_scheduled_status', 'tasks', ['scheduled_for', 'status'])
    op.create_index('idx_task_status_priority', 'tasks', ['status', 'priority'])
    op.create_index('idx_task_type_status', 'tasks', ['type', 'status'])
    op.create_index(op.f('ix_tasks_correlation_id'), 'tasks', ['correlation_id'])
    op.create_index(op.f('ix_tasks_created_by'), 'tasks', ['created_by'])
    op.create_index(op.f('ix_tasks_id'), 'tasks', ['id'])
    op.create_index(op.f('ix_tasks_locked_at'), 'tasks', ['locked_at'])
    op.create_index(op.f('ix_tasks_locked_by'), 'tasks', ['locked_by'])
    op.create_index(op.f('ix_tasks_priority'), 'tasks', ['priority'])
    op.create_index(op.f('ix_tasks_scheduled_for'), 'tasks', ['scheduled_for'])
    op.create_index(op.f('ix_tasks_status'), 'tasks', ['status'])
    op.create_index(op.f('ix_tasks_type'), 'tasks', ['type'])
    
    # Create task_attempts table
    op.create_table('task_attempts',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('task_id', sa.String(length=50), nullable=False),
        sa.Column('worker_id', sa.String(length=50), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('error_code', sa.String(length=100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.CheckConstraint('(completed_at IS NULL) != (failed_at IS NULL)', name='check_attempt_completion_xor_failure'),
        sa.CheckConstraint('processing_time_ms >= 0', name='check_processing_time_non_negative'),
        sa.CheckConstraint('(failed_at IS NULL) OR (error_code IS NOT NULL)', name='check_error_code_required_on_failure'),
        sa.CheckConstraint('completed_at IS NULL OR completed_at >= started_at', name='check_completed_after_started'),
        sa.CheckConstraint('failed_at IS NULL OR failed_at >= started_at', name='check_failed_after_started'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['worker_id'], ['workers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_task_attempt_duration', 'task_attempts', ['processing_time_ms'])
    op.create_index('idx_task_attempt_error', 'task_attempts', ['error_code'])
    op.create_index('idx_task_attempt_status', 'task_attempts', ['completed_at', 'failed_at'])
    op.create_index('idx_task_attempt_task_started', 'task_attempts', ['task_id', 'started_at'])
    op.create_index('idx_task_attempt_worker_started', 'task_attempts', ['worker_id', 'started_at'])
    op.create_index(op.f('ix_task_attempts_error_code'), 'task_attempts', ['error_code'])
    op.create_index(op.f('ix_task_attempts_id'), 'task_attempts', ['id'])
    op.create_index(op.f('ix_task_attempts_started_at'), 'task_attempts', ['started_at'])
    op.create_index(op.f('ix_task_attempts_task_id'), 'task_attempts', ['task_id'])
    op.create_index(op.f('ix_task_attempts_worker_id'), 'task_attempts', ['worker_id'])
    
    # Create dead_letter_queue table
    op.create_table('dead_letter_queue',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('type', sa.String(length=100), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('original_created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('original_created_by', sa.String(length=50), nullable=False),
        sa.Column('correlation_id', sa.String(length=100), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('failure_reason', sa.String(length=100), nullable=False),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('max_retries', sa.Integer(), nullable=False),
        sa.Column('last_error_code', sa.String(length=100), nullable=True),
        sa.Column('last_error_message', sa.Text(), nullable=True),
        sa.Column('last_worker_id', sa.String(length=50), nullable=True),
        sa.Column('attempts_summary', sa.JSON(), nullable=False),
        sa.Column('reviewed', sa.String(length=20), nullable=False),
        sa.Column('reviewed_by', sa.String(length=50), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('recovery_attempts', sa.Integer(), nullable=False),
        sa.Column('last_recovery_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_recovery_attempt_by', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("failure_reason IN ('MAX_RETRIES_EXCEEDED', 'PERMANENT_ERROR', 'STALE_LOCK_TIMEOUT', 'MANUAL_MOVE')", name='check_dlq_failure_reason'),
        sa.CheckConstraint("reviewed IN ('pending', 'reviewed', 'resolved')", name='check_dlq_reviewed_status'),
        sa.CheckConstraint('retry_count >= 0', name='check_dlq_retry_count_non_negative'),
        sa.CheckConstraint('max_retries >= 0', name='check_dlq_max_retries_non_negative'),
        sa.CheckConstraint('recovery_attempts >= 0', name='check_dlq_recovery_attempts_non_negative'),
        sa.CheckConstraint('priority IN (1, 2, 3, 4)', name='check_dlq_priority'),
        sa.CheckConstraint('(reviewed_by IS NULL) = (reviewed_at IS NULL)', name='check_dlq_reviewer_consistency'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_dlq_creator_failed_at', 'dead_letter_queue', ['original_created_by', 'failed_at'])
    op.create_index('idx_dlq_error_code', 'dead_letter_queue', ['last_error_code'])
    op.create_index('idx_dlq_failure_reason', 'dead_letter_queue', ['failure_reason', 'failed_at'])
    op.create_index('idx_dlq_priority_failed_at', 'dead_letter_queue', ['priority', 'failed_at'])
    op.create_index('idx_dlq_recovery_attempts', 'dead_letter_queue', ['recovery_attempts', 'last_recovery_attempt_at'])
    op.create_index('idx_dlq_reviewed_status', 'dead_letter_queue', ['reviewed', 'failed_at'])
    op.create_index('idx_dlq_type_failed_at', 'dead_letter_queue', ['type', 'failed_at'])
    op.create_index('idx_dlq_worker_failed_at', 'dead_letter_queue', ['last_worker_id', 'failed_at'])
    op.create_index(op.f('ix_dead_letter_queue_correlation_id'), 'dead_letter_queue', ['correlation_id'])
    op.create_index(op.f('ix_dead_letter_queue_failed_at'), 'dead_letter_queue', ['failed_at'])
    op.create_index(op.f('ix_dead_letter_queue_id'), 'dead_letter_queue', ['id'])
    op.create_index(op.f('ix_dead_letter_queue_last_worker_id'), 'dead_letter_queue', ['last_worker_id'])
    op.create_index(op.f('ix_dead_letter_queue_original_created_by'), 'dead_letter_queue', ['original_created_by'])
    op.create_index(op.f('ix_dead_letter_queue_original_created_at'), 'dead_letter_queue', ['original_created_at'])
    op.create_index(op.f('ix_dead_letter_queue_priority'), 'dead_letter_queue', ['priority'])
    op.create_index(op.f('ix_dead_letter_queue_reviewed'), 'dead_letter_queue', ['reviewed'])
    op.create_index(op.f('ix_dead_letter_queue_reviewed_by'), 'dead_letter_queue', ['reviewed_by'])
    op.create_index(op.f('ix_dead_letter_queue_type'), 'dead_letter_queue', ['type'])
    op.create_index(op.f('ix_dead_letter_queue_failure_reason'), 'dead_letter_queue', ['failure_reason'])
    op.create_index(op.f('ix_dead_letter_queue_last_error_code'), 'dead_letter_queue', ['last_error_code'])


def downgrade() -> None:
    # Drop all tables in reverse order
    op.drop_table('dead_letter_queue')
    op.drop_table('task_attempts')
    op.drop_table('tasks')
    op.drop_table('workers')