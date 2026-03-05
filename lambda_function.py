import json

def lambda_handler(event, context):
    # Log the event
    print("Received event:", json.dumps(event))
    
    # Return a response
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }