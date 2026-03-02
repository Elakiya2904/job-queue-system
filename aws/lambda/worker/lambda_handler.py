"""
AWS Lambda handler for processing SQS task messages.
"""

import json
import os
import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import application components
try:
    from app.services.worker_runner import WorkerRunner
    from app.core.config import settings
    from app.db.base import SessionLocal
    from app.models import Task, TaskAttempt
    from sqlalchemy.orm import Session
except ImportError as e:
    logger.error(f"Failed to import application components: {e}")
    raise


class LambdaWorkerHandler:
    """Handler for processing SQS messages in AWS Lambda."""
    
    def __init__(self):
        self.worker_runner = WorkerRunner()
        self.worker_id = f"lambda-worker-{os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'unknown')}"
    
    async def process_sqs_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single SQS record."""
        try:
            # Parse message body
            message_body = json.loads(record['body'])
            task_id = message_body.get('task_id')
            task_type = message_body.get('task_type')
            payload = message_body.get('payload', {})
            priority = message_body.get('priority', 0)
            
            logger.info(f"Processing task {task_id} of type {task_type}")
            
            if not task_id:
                logger.error("No task_id found in message")
                return {
                    'statusCode': 400,
                    'batchItemFailures': [{'itemIdentifier': record.get('messageId')}]
                }
            
            # Get database session
            session = SessionLocal()
            try:
                # Find and claim the task
                task = session.query(Task).filter(Task.id == task_id).first()
                
                if not task:
                    logger.error(f"Task {task_id} not found in database")
                    return {
                        'statusCode': 404,
                        'batchItemFailures': [{'itemIdentifier': record.get('messageId')}]
                    }
                
                # Check if task is still available for processing
                if task.status != 'queued':
                    logger.warning(f"Task {task_id} is already {task.status}")
                    # This is not an error - task was already processed
                    return {'statusCode': 200}
                
                # Create task attempt
                attempt = TaskAttempt(
                    task_id=task_id,
                    worker_id=self.worker_id,
                    attempt_number=task.retry_count + 1,
                    started_at=datetime.now(timezone.utc),
                    status='in_progress'
                )
                
                # Update task status
                task.status = 'in_progress'
                task.locked_by = self.worker_id
                task.locked_at = datetime.now(timezone.utc)
                task.updated_at = datetime.now(timezone.utc)
                
                session.add(attempt)
                session.commit()
                session.refresh(attempt)
                
                # Process the task
                result = await self.worker_runner.execute_task(
                    task_id=task_id,
                    task_type=task_type,
                    payload=payload,
                    timeout=task.timeout or 300
                )
                
                # Update task and attempt based on result
                if result.get('success'):
                    task.status = 'completed'
                    task.completed_at = datetime.now(timezone.utc)
                    task.result = result.get('result')
                    task.locked_by = None
                    task.locked_at = None
                    
                    attempt.status = 'completed'
                    attempt.completed_at = datetime.now(timezone.utc)
                    attempt.result = result.get('result')
                    
                    logger.info(f"Task {task_id} completed successfully")
                    
                else:
                    # Task failed
                    error_message = result.get('error', 'Unknown error')
                    task.retry_count += 1
                    
                    if task.retry_count >= task.max_retries:
                        task.status = 'failed'
                        task.error_message = error_message
                        task.failed_at = datetime.now(timezone.utc)
                        logger.error(f"Task {task_id} failed permanently after {task.retry_count} attempts")
                    else:
                        task.status = 'queued'  # Will be retried by SQS
                        logger.warning(f"Task {task_id} failed, will retry (attempt {task.retry_count}/{task.max_retries})")
                    
                    task.locked_by = None
                    task.locked_at = None
                    
                    attempt.status = 'failed'
                    attempt.completed_at = datetime.now(timezone.utc)
                    attempt.error = error_message
                
                task.updated_at = datetime.now(timezone.utc)
                session.commit()
                
                return {'statusCode': 200}
                
            finally:
                session.close()
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in message body: {e}")
            return {
                'statusCode': 400,
                'batchItemFailures': [{'itemIdentifier': record.get('messageId')}]
            }
            
        except Exception as e:
            logger.error(f"Error processing SQS record: {e}")
            return {
                'statusCode': 500,
                'batchItemFailures': [{'itemIdentifier': record.get('messageId')}]
            }
    
    async def handle_sqs_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle SQS Lambda event with multiple records."""
        logger.info(f"Processing {len(event.get('Records', []))} SQS records")
        
        results = []
        batch_item_failures = []
        
        for record in event.get('Records', []):
            try:
                result = await self.process_sqs_record(record)
                results.append(result)
                
                # Collect any batch item failures
                if 'batchItemFailures' in result:
                    batch_item_failures.extend(result['batchItemFailures'])
                    
            except Exception as e:
                logger.error(f"Unexpected error processing record {record.get('messageId')}: {e}")
                batch_item_failures.append({
                    'itemIdentifier': record.get('messageId')
                })
        
        # Return result with any failed items
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'processed': len(event.get('Records', [])),
                'failed': len(batch_item_failures),
                'message': f'Processed {len(event.get("Records", []))} records'
            })
        }
        
        if batch_item_failures:
            response['batchItemFailures'] = batch_item_failures
        
        return response


# Global handler instance
lambda_handler_instance = LambdaWorkerHandler()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda entry point for SQS-triggered task processing.
    
    Args:
        event: SQS Lambda event
        context: Lambda context
        
    Returns:
        Response dictionary with processing results
    """
    try:
        logger.info(f"Lambda handler invoked with {len(event.get('Records', []))} records")
        
        # Create and run event loop for async processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            return loop.run_until_complete(
                lambda_handler_instance.handle_sqs_event(event)
            )
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Lambda handler error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Lambda handler failed'
            })
        }