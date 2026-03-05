import boto3
import json
import os

def lambda_handler(event, context):
    sqs = boto3.client('sqs')
    queue_url = os.environ['QUEUE_URL']

    for record in event['Records']:
        message_body = record['body']
        print(f"Processing message: {message_body}")

        try:
            # Process the message (custom logic here)
            print("Message processed successfully")
        except Exception as e:
            print(f"Error processing message: {e}")
            # Optionally send to a dead-letter queue or log the error

    return {
        'statusCode': 200,
        'body': json.dumps('Messages processed successfully')
    }