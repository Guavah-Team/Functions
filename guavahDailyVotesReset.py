import json
import boto3
from boto3.dynamodb.conditions import Attr

client = boto3.resource('dynamodb')
users_table = client.Table('GuavahUsers')

def reset_daily_votes():
    statusCode = 200
    errorMessage = "DailyVotes successfully reset."
    
    response = users_table.scan(FilterExpression = Attr('DailyVotes').gt(0))
    users = response["Items"]
    
    while 'LastEvaluatedKey' in response:
        response = users_table.scan(
            ExclusiveStartKey = response['LastEvaluatedKey']
        )
        users.extend(response['Items'])
    
    for user in users:
        try:    
            updated_user = users_table.update_item(
               Key={
                'UserID': user["UserID"]
            },
            UpdateExpression="SET DailyVotes = :dv",
            ExpressionAttributeValues={
                ':dv': 0
            },
            ReturnValues="UPDATED_NEW"
            )
        except ClientError as e:
            statusCode = 500
            errorMessage = "DailyVotes reset failed."
            return {
                'statusCode': statusCode,
                'errorMessage': errorMessage
            }
    
    return {
        'statusCode': statusCode,
        'errorMessage': errorMessage
    }

def lambda_handler(event, context):
    return reset_daily_votes()
