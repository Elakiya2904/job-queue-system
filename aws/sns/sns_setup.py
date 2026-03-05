import boto3

def setup_sns_topic():
    sns = boto3.client('sns', region_name='us-east-1')

    # Create SNS topic
    response = sns.create_topic(Name='FailedTaskNotifications')
    topic_arn = response['TopicArn']
    print(f"SNS Topic ARN: {topic_arn}")

    # Subscribe an email to the topic
    email = 'example@example.com'  # Replace with your email
    sns.subscribe(
        TopicArn=topic_arn,
        Protocol='email',
        Endpoint=email
    )
    print(f"Subscription request sent to {email}")

    # Publish a test message
    sns.publish(
        TopicArn=topic_arn,
        Message='This is a test message for the SNS topic.',
        Subject='Test SNS Notification'
    )
    print("Test message published.")

if __name__ == "__main__":
    setup_sns_topic()