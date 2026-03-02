"""
AWS SQS service for task queue management.
"""

import json
import boto3
import logging
from typing import Dict, Any, Optional, List
from botocore.exceptions import ClientError, BotoCoreError
from ..core.config import settings

logger = logging.getLogger(__name__)


class SQSService:
    """Service for managing AWS SQS task queues."""
    
    def __init__(self):
        """Initialize SQS service with AWS configuration."""
        self.sqs = None
        self.queue_url = settings.sqs_queue_url
        self.dlq_url = settings.sqs_dlq_url
        self.region = settings.aws_region or 'us-east-1'
        
        if settings.use_sqs:
            try:
                self.sqs = boto3.client('sqs', region_name=self.region)
                logger.info(f"SQS client initialized for region: {self.region}")
            except Exception as e:
                logger.error(f"Failed to initialize SQS client: {e}")
                raise
        else:
            logger.info("SQS not configured, using internal queue")
    
    def is_available(self) -> bool:
        """Check if SQS is properly configured and available."""
        return (
            self.sqs is not None and 
            self.queue_url is not None and 
            settings.use_sqs
        )
    
    async def send_task_message(
        self, 
        task_id: str, 
        task_type: str, 
        payload: Dict[str, Any],
        priority: int = 0,
        delay_seconds: int = 0
    ) -> Optional[str]:
        """
        Send a task message to SQS queue.
        
        Args:
            task_id: Unique task identifier
            task_type: Type of task to execute
            payload: Task payload data
            priority: Task priority (0-9, higher = more priority)
            delay_seconds: Delay before message becomes visible
            
        Returns:
            Message ID if successful, None otherwise
        """
        if not self.is_available():
            logger.warning("SQS not available, cannot send message")
            return None
        
        message_body = {
            "task_id": task_id,
            "task_type": task_type,
            "payload": payload,
            "priority": priority
        }
        
        try:
            # Higher priority gets lower delay for message visibility
            message_attributes = {
                'priority': {
                    'StringValue': str(priority),
                    'DataType': 'Number'
                },
                'task_type': {
                    'StringValue': task_type,
                    'DataType': 'String'
                }
            }
            
            response = self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message_body),
                DelaySeconds=delay_seconds,
                MessageAttributes=message_attributes
            )
            
            message_id = response.get('MessageId')
            logger.info(f"Task message sent to SQS: {task_id} (MessageId: {message_id})")
            return message_id
            
        except ClientError as e:
            logger.error(f"Failed to send message to SQS: {e}")
            error_code = e.response['Error']['Code']
            if error_code == 'QueueDoesNotExist':
                logger.error(f"Queue does not exist: {self.queue_url}")
            elif error_code == 'AccessDenied':
                logger.error("Access denied to SQS queue")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error sending message to SQS: {e}")
            return None
    
    async def receive_messages(
        self, 
        max_messages: int = 1,
        wait_time_seconds: int = 20,
        visibility_timeout: int = 900  # 15 minutes
    ) -> List[Dict[str, Any]]:
        """
        Receive messages from SQS queue.
        
        Args:
            max_messages: Maximum number of messages to receive
            wait_time_seconds: Long polling wait time
            visibility_timeout: Message visibility timeout in seconds
            
        Returns:
            List of message dictionaries
        """
        if not self.is_available():
            logger.warning("SQS not available, cannot receive messages")
            return []
        
        try:
            response = self.sqs.receive_message(
                QueueUrl=self.queue_url,
                AttributeNames=['All'],
                MessageAttributeNames=['All'],
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_time_seconds,
                VisibilityTimeout=visibility_timeout
            )
            
            messages = response.get('Messages', [])
            logger.info(f"Received {len(messages)} messages from SQS")
            
            parsed_messages = []
            for message in messages:
                try:
                    body = json.loads(message['Body'])
                    parsed_message = {
                        'receipt_handle': message['ReceiptHandle'],
                        'message_id': message['MessageId'],
                        'task_id': body.get('task_id'),
                        'task_type': body.get('task_type'),
                        'payload': body.get('payload'),
                        'priority': body.get('priority', 0),
                        'attributes': message.get('Attributes', {}),
                        'message_attributes': message.get('MessageAttributes', {})
                    }
                    parsed_messages.append(parsed_message)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message body: {e}")
                    continue
                    
            return parsed_messages
            
        except ClientError as e:
            logger.error(f"Failed to receive messages from SQS: {e}")
            return []
            
        except Exception as e:
            logger.error(f"Unexpected error receiving messages from SQS: {e}")
            return []
    
    async def delete_message(self, receipt_handle: str) -> bool:
        """
        Delete a message from the queue after successful processing.
        
        Args:
            receipt_handle: Message receipt handle
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.is_available():
            logger.warning("SQS not available, cannot delete message")
            return False
        
        try:
            self.sqs.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle
            )
            logger.info("Message deleted from SQS")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete message from SQS: {e}")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error deleting message from SQS: {e}")
            return False
    
    async def change_message_visibility(
        self, 
        receipt_handle: str, 
        visibility_timeout: int
    ) -> bool:
        """
        Change the visibility timeout of a message.
        
        Args:
            receipt_handle: Message receipt handle
            visibility_timeout: New visibility timeout in seconds
            
        Returns:
            True if changed successfully, False otherwise
        """
        if not self.is_available():
            logger.warning("SQS not available, cannot change message visibility")
            return False
        
        try:
            self.sqs.change_message_visibility(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=visibility_timeout
            )
            logger.info(f"Message visibility timeout changed to {visibility_timeout} seconds")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to change message visibility: {e}")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error changing message visibility: {e}")
            return False
    
    async def get_queue_attributes(self) -> Optional[Dict[str, Any]]:
        """
        Get queue attributes and statistics.
        
        Returns:
            Queue attributes dictionary or None if error
        """
        if not self.is_available():
            return None
        
        try:
            response = self.sqs.get_queue_attributes(
                QueueUrl=self.queue_url,
                AttributeNames=['All']
            )
            
            attributes = response.get('Attributes', {})
            
            return {
                'approximate_number_of_messages': int(attributes.get('ApproximateNumberOfMessages', 0)),
                'approximate_number_of_messages_not_visible': int(attributes.get('ApproximateNumberOfMessagesNotVisible', 0)),
                'approximate_number_of_messages_delayed': int(attributes.get('ApproximateNumberOfMessagesDelayed', 0)),
                'created_timestamp': attributes.get('CreatedTimestamp'),
                'last_modified_timestamp': attributes.get('LastModifiedTimestamp'),
                'queue_arn': attributes.get('QueueArn'),
                'visibility_timeout': int(attributes.get('VisibilityTimeout', 0)),
                'message_retention_period': int(attributes.get('MessageRetentionPeriod', 0)),
                'receive_message_wait_time_seconds': int(attributes.get('ReceiveMessageWaitTimeSeconds', 0))
            }
            
        except ClientError as e:
            logger.error(f"Failed to get queue attributes: {e}")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error getting queue attributes: {e}")
            return None


# Global SQS service instance
sqs_service = SQSService()