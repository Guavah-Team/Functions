import json
import boto3

def get_user_reviews(user_id):
    dynamodb = boto3.resource('dynamodb')

    guavah_users = dynamodb.Table('GuavahUsers')
    user = guavah_users.get_item(
        Key={
            'UserID': user_id,
        }
    )
    
    #Check if user exists
    if ("Item" in user):
        user = user["Item"]
        #Check if user has any reviews
        if ("Reviews" in user):
            user_reviews = user["Reviews"]
            return user_reviews
        else:
            return None
    else: 
        return None

def lambda_handler(event, context):
    user_id = event['UserID']
    user_reviews = get_user_reviews(user_id)
    if (user_reviews is not None):
        return {
            'statusCode': 200,
            'body': user_reviews
        }
    else:
        return {
            'statusCode': 404
        }
